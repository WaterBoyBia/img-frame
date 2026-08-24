from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy


class PreviewWidget(QLabel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background: #202124; color: #aeb4bd;")
        self.setText("打开图片以开始")
        self._pixmap: QPixmap | None = None
        self._zoom = 0.0

    def set_image(self, image: np.ndarray | QImage | QPixmap | None) -> None:
        if image is None:
            self._pixmap = None
            self.setPixmap(QPixmap())
            self.setText("打开图片以开始")
            return
        if isinstance(image, QPixmap):
            pixmap = image
        elif isinstance(image, QImage):
            pixmap = QPixmap.fromImage(image)
        else:
            pixmap = QPixmap.fromImage(_array_to_qimage(image))
        self._pixmap = pixmap
        self.setText("")
        self.fit_to_window()

    def set_zoom(self, zoom: float) -> None:
        self._zoom = max(0.1, min(8.0, float(zoom)))
        self._apply_pixmap()

    def fit_to_window(self) -> None:
        self._zoom = 0.0
        self._apply_pixmap()

    def available_size(self) -> tuple[int, int]:
        return max(1, self.width() - 16), max(1, self.height() - 16)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_pixmap()

    def _apply_pixmap(self) -> None:
        if self._pixmap is None or self._pixmap.isNull():
            return
        if self._zoom:
            size = self._pixmap.size()
            size.setWidth(max(1, round(size.width() * self._zoom)))
            size.setHeight(max(1, round(size.height() * self._zoom)))
            scaled = self._pixmap.scaled(
                size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            scaled = self._pixmap.scaled(
                self.available_size()[0],
                self.available_size()[1],
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        self.setPixmap(scaled)


def _array_to_qimage(array: np.ndarray) -> QImage:
    if not isinstance(array, np.ndarray) or array.ndim != 3:
        raise ValueError("preview image must be an RGB or RGBA array")
    if array.dtype == np.uint16:
        array = (array / 257).astype(np.uint8)
    elif array.dtype != np.uint8:
        raise ValueError("preview image must use uint8 or uint16 pixels")
    if array.shape[2] == 3:
        alpha = np.full((*array.shape[:2], 1), 255, dtype=np.uint8)
        array = np.concatenate((array, alpha), axis=2)
    if array.shape[2] != 4:
        raise ValueError("preview image must have RGB or RGBA channels")
    array = np.ascontiguousarray(array)
    image = QImage(
        array.data,
        array.shape[1],
        array.shape[0],
        array.strides[0],
        QImage.Format.Format_RGBA8888,
    )
    return image.copy()
