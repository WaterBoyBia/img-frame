from __future__ import annotations

from PySide6.QtCore import Signal, Qt, QSignalBlocker
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QButtonGroup,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from app.models.frame_config import FrameConfig
from app.models.metadata import MetadataValues


class SettingsPanel(QWidget):
    metadata_changed = Signal(object)
    frame_config_changed = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedWidth(258)
        self._color = (255, 255, 255, 255)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("相框设置")
        title.setStyleSheet("font-size: 16px; font-weight: 600;")
        layout.addWidget(title)

        metadata_form = QFormLayout()
        metadata_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.camera_model_edit = QLineEdit()
        self.focal_length_edit = QLineEdit()
        self.shutter_speed_edit = QLineEdit()
        self.aperture_edit = QLineEdit()
        self.iso_edit = QLineEdit()
        self.iso_edit.setPlaceholderText("例如 100")
        fields = (
            ("相机型号", self.camera_model_edit),
            ("焦距", self.focal_length_edit),
            ("快门", self.shutter_speed_edit),
            ("光圈", self.aperture_edit),
            ("ISO", self.iso_edit),
        )
        for label, editor in fields:
            metadata_form.addRow(label, editor)
            editor.editingFinished.connect(self._emit_metadata)
        layout.addLayout(metadata_form)

        layout.addWidget(QLabel("材质"))
        material_row = QHBoxLayout()
        self.solid_button = QPushButton("纯色")
        self.frosted_button = QPushButton("磨砂")
        self.material_group = QButtonGroup(self)
        self.material_group.setExclusive(True)
        for button in (self.solid_button, self.frosted_button):
            button.setCheckable(True)
            self.material_group.addButton(button)
            material_row.addWidget(button)
            button.clicked.connect(self._emit_frame_config)
        self.solid_button.setChecked(True)
        layout.addLayout(material_row)

        self.color_button = QPushButton("颜色")
        self.color_button.clicked.connect(self._choose_color)
        layout.addWidget(self.color_button)

        self.opacity_slider = self._add_slider(layout, "透明度", 0, 100, 100)
        self.border_slider = self._add_slider(layout, "边框厚度", 1, 20, 5)
        self.font_slider = self._add_slider(layout, "字号", 1, 100, 24)
        self.blur_slider = self._add_slider(layout, "磨砂半径", 1, 20, 3)

        layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def set_metadata(self, values: MetadataValues) -> None:
        editors = (
            (self.camera_model_edit, values.camera_model or ""),
            (self.focal_length_edit, _format_focal(values.focal_length_mm)),
            (self.shutter_speed_edit, values.shutter_speed or ""),
            (self.aperture_edit, values.aperture or ""),
            (self.iso_edit, "" if values.iso is None else str(values.iso)),
        )
        blockers = [QSignalBlocker(editor) for editor, _ in editors]
        try:
            for editor, text in editors:
                editor.setText(text)
        finally:
            del blockers

    def set_frame_config(self, config: FrameConfig) -> None:
        self._color = config.color
        self._set_color_button()
        blockers = [
            QSignalBlocker(self.opacity_slider),
            QSignalBlocker(self.border_slider),
            QSignalBlocker(self.font_slider),
            QSignalBlocker(self.blur_slider),
            QSignalBlocker(self.solid_button),
            QSignalBlocker(self.frosted_button),
        ]
        try:
            self.opacity_slider.setValue(round(config.opacity * 100))
            self.border_slider.setValue(round(config.border_ratio * 100))
            self.font_slider.setValue(round(config.font_ratio * 1000))
            self.blur_slider.setValue(round(config.blur_ratio * 100))
            self.solid_button.setChecked(config.material == "solid")
            self.frosted_button.setChecked(config.material == "frosted")
        finally:
            del blockers

    def metadata(self) -> MetadataValues:
        return MetadataValues(
            camera_model=_optional_text(self.camera_model_edit.text()),
            focal_length_mm=_parse_focal(self.focal_length_edit.text()),
            shutter_speed=_optional_text(self.shutter_speed_edit.text()),
            aperture=_optional_text(self.aperture_edit.text()),
            iso=_parse_iso(self.iso_edit.text()),
        )

    def frame_config(self) -> FrameConfig:
        material = "frosted" if self.frosted_button.isChecked() else "solid"
        return FrameConfig(
            material=material,
            color=self._color,
            opacity=self.opacity_slider.value() / 100.0,
            border_ratio=self.border_slider.value() / 100.0,
            font_ratio=self.font_slider.value() / 1000.0,
            blur_ratio=self.blur_slider.value() / 100.0,
        )

    def _add_slider(self, layout, label: str, minimum: int, maximum: int, value: int) -> QSlider:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        slider.valueChanged.connect(self._emit_frame_config)
        row.addWidget(slider)
        layout.addLayout(row)
        return slider

    def _emit_metadata(self) -> None:
        self.metadata_changed.emit(self.metadata())

    def _emit_frame_config(self) -> None:
        self.frame_config_changed.emit(self.frame_config())

    def _choose_color(self) -> None:
        color = QColorDialog.getColor(QColor(*self._color[:3]), self, "选择相框颜色")
        if color.isValid():
            self._color = (color.red(), color.green(), color.blue(), 255)
            self._set_color_button()
            self._emit_frame_config()

    def _set_color_button(self) -> None:
        r, g, b, _ = self._color
        self.color_button.setStyleSheet(
            f"QPushButton {{ background-color: rgb({r}, {g}, {b}); color: {'black' if sum((r, g, b)) > 380 else 'white'}; }}"
        )


def _optional_text(value: str) -> str | None:
    value = value.strip()
    return value or None


def _parse_focal(value: str) -> float | None:
    value = value.strip().lower().replace("mm", "").strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _parse_iso(value: str) -> int | None:
    value = value.strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _format_focal(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:g}mm"
