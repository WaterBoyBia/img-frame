from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, QThreadPool, QTimer, QUrl, Signal, QRunnable, QObject
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.errors import ImgFrameError
from app.core.session_controller import SessionController
from app.ui.preview_widget import PreviewWidget
from app.ui.settings_panel import SettingsPanel


class MainWindow(QMainWindow):
    def __init__(self, parent=None, controller: SessionController | None = None) -> None:
        super().__init__(parent)
        self.controller = controller or SessionController()
        self.settings = QSettings("img-frame", "img-frame")
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(2)
        self._workers: set[QRunnable] = set()
        self._session_generation = 0
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(150)
        self._preview_timer.timeout.connect(self._render_scheduled_preview)
        self._build_ui()
        self._restore_output_directory()
        self._restore_output_format()
        self._set_application_font()

    def _build_ui(self) -> None:
        self.setWindowTitle("img-frame")
        self.resize(1280, 800)
        self.setMinimumSize(960, 640)

        self.open_button = QPushButton("打开图片")
        self.open_button.clicked.connect(self._open_dialog)
        self.export_button = QPushButton("导出 JPG")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self._start_export)

        format_label = QLabel("输出格式")
        self.output_format_combo = QComboBox()
        self.output_format_combo.addItem("JPG", "jpg")
        self.output_format_combo.addItem("PNG", "png")
        self.output_format_combo.currentIndexChanged.connect(self._output_format_changed)

        shortcut = QVBoxLayout()
        shortcut.setContentsMargins(12, 12, 8, 12)
        shortcut.setSpacing(8)
        shortcut.addWidget(self.open_button)
        shortcut.addWidget(format_label)
        shortcut.addWidget(self.output_format_combo)
        shortcut.addWidget(self.export_button)
        shortcut.addStretch(1)
        shortcut_widget = QWidget()
        shortcut_widget.setLayout(shortcut)
        shortcut_widget.setFixedWidth(124)

        self.preview_widget = PreviewWidget()
        self.settings_panel = SettingsPanel()
        self.settings_panel.setEnabled(False)
        self.settings_panel.metadata_changed.connect(self._metadata_changed)
        self.settings_panel.frame_config_changed.connect(self._frame_config_changed)
        self.camera_model_edit = self.settings_panel.camera_model_edit

        center = QHBoxLayout()
        center.setContentsMargins(0, 0, 0, 0)
        center.addWidget(shortcut_widget)
        center.addWidget(self.preview_widget, 1)
        center.addWidget(self.settings_panel)

        self.output_directory_button = QPushButton("选择输出目录")
        self.output_directory_button.clicked.connect(self._choose_output_directory)
        self.output_directory_label = QLabel("输出目录：未选择")
        self.status_label = QLabel("准备就绪")
        bottom = QHBoxLayout()
        bottom.setContentsMargins(12, 8, 12, 10)
        bottom.addWidget(self.output_directory_button)
        bottom.addWidget(self.output_directory_label, 1)
        bottom.addWidget(self.status_label)

        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.addLayout(center, 1)
        root.addLayout(bottom)
        container = QWidget()
        container.setLayout(root)
        self.setCentralWidget(container)

    def open_path(self, path: Path) -> None:
        self._session_generation += 1
        try:
            session = self.controller.open_image(Path(path), self.preview_widget.available_size())
            self._apply_opened_session(session, self.controller.preview)
        except ImgFrameError as exc:
            self._show_error(exc.code, exc.detail)

    def _open_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "打开图片",
            "",
            "图片 (*.jpg *.jpeg *.png)",
        )
        if path:
            self._start_open(Path(path))

    def _start_open(self, path: Path) -> None:
        self._session_generation += 1
        generation = self._session_generation
        self.open_button.setEnabled(False)
        self.status_label.setText("正在读取图片…")
        worker = _OpenWorker(
            self.controller,
            path,
            self.preview_widget.available_size(),
            generation,
        )
        worker.signals.succeeded.connect(self._open_succeeded)
        worker.signals.failed.connect(self._open_failed)
        self._start_worker(worker)

    def _open_succeeded(self, session, preview, generation: int) -> None:
        if generation != self._session_generation:
            return
        self.open_button.setEnabled(True)
        self.controller.session = session
        self.controller.output_directory = session.source_path.parent
        self.controller.preview = preview
        self._apply_opened_session(session, preview)

    def _open_failed(self, code: str, detail: str, generation: int) -> None:
        if generation != self._session_generation:
            return
        self.open_button.setEnabled(True)
        self.status_label.setText("读取失败")
        self._show_error(code, detail)

    def _apply_opened_session(self, session, preview) -> None:
        saved = self.settings.value("output_directory", "")
        if saved and Path(saved).is_dir():
            self.controller.set_output_directory(Path(saved))
        self.settings_panel.set_metadata(session.edited_metadata)
        self.settings_panel.set_frame_config(session.frame_config)
        self.settings_panel.setEnabled(True)
        self.preview_widget.set_image(preview)
        self.export_button.setEnabled(True)
        self._update_output_directory_label()
        self.status_label.setText(f"已打开：{session.source_path.name}")

    def _metadata_changed(self, metadata) -> None:
        try:
            self.controller.set_metadata(metadata)
            self._queue_preview()
        except ImgFrameError as exc:
            self._show_error(exc.code, exc.detail)
        except (TypeError, ValueError) as exc:
            self._show_error("invalid_metadata", str(exc))

    def _frame_config_changed(self, config) -> None:
        try:
            self.controller.set_frame_config(config)
            self._queue_preview()
        except ImgFrameError as exc:
            self._show_error(exc.code, exc.detail)

    def _queue_preview(self) -> None:
        self._preview_timer.start()

    def _render_scheduled_preview(self) -> None:
        if self.controller.session is None:
            return
        worker = _PreviewWorker(
            self.controller.image_service,
            self.controller.session,
            self.preview_widget.available_size(),
            self._session_generation,
        )
        worker.signals.succeeded.connect(self._preview_succeeded)
        worker.signals.failed.connect(self._preview_failed)
        self._start_worker(worker)

    def _preview_succeeded(self, preview, generation: int) -> None:
        if generation == self._session_generation:
            self.controller.preview = preview
            self.preview_widget.set_image(preview)

    def _preview_failed(self, code: str, detail: str, generation: int) -> None:
        if generation == self._session_generation:
            self._show_error(code, detail)

    def _choose_output_directory(self) -> None:
        current = str(self.controller.output_directory or "")
        directory = QFileDialog.getExistingDirectory(self, "选择输出目录", current)
        if not directory:
            return
        try:
            self.controller.set_output_directory(Path(directory))
            self.settings.setValue("output_directory", directory)
            self._update_output_directory_label()
        except ImgFrameError as exc:
            self._show_error(exc.code, exc.detail)

    def _output_format_changed(self, _index: int) -> None:
        output_format = self.output_format_combo.currentData()
        if not output_format:
            return
        try:
            self.controller.set_output_format(str(output_format))
            self.settings.setValue("output_format", str(output_format))
            self.export_button.setText(f"导出 {str(output_format).upper()}")
        except (ImgFrameError, TypeError, ValueError) as exc:
            detail = getattr(exc, "detail", str(exc))
            code = getattr(exc, "code", "export_failed")
            self._show_error(code, detail)

    def _start_export(self) -> None:
        if self.controller.session is None:
            return
        self.export_button.setEnabled(False)
        self.status_label.setText("正在导出…")
        worker = _ExportWorker(self.controller, self._session_generation)
        worker.signals.succeeded.connect(self._export_succeeded)
        worker.signals.failed.connect(self._export_failed)
        self._start_worker(worker)

    def _start_worker(self, worker: QRunnable) -> None:
        self._workers.add(worker)
        worker.signals.succeeded.connect(
            lambda *args, active_worker=worker: self._workers.discard(active_worker)
        )
        worker.signals.failed.connect(
            lambda *args, active_worker=worker: self._workers.discard(active_worker)
        )
        self._pool.start(worker)

    def closeEvent(self, event) -> None:
        self._preview_timer.stop()
        self._pool.waitForDone()
        self._workers.clear()
        super().closeEvent(event)

    def _export_succeeded(self, destination: str, generation: int) -> None:
        if generation != self._session_generation:
            return
        self.export_button.setEnabled(True)
        self.status_label.setText(f"已导出：{destination}")
        output_dir = str(Path(destination).parent)
        QDesktopServices.openUrl(QUrl.fromLocalFile(output_dir))

    def _export_failed(self, code: str, detail: str, generation: int) -> None:
        if generation != self._session_generation:
            return
        self.export_button.setEnabled(True)
        self.status_label.setText("导出失败")
        self._show_error(code, detail)

    def _restore_output_directory(self) -> None:
        directory = self.settings.value("output_directory", "")
        if directory and Path(directory).is_dir():
            self.controller.output_directory = Path(directory)
            self._update_output_directory_label()

    def _restore_output_format(self) -> None:
        saved = str(self.settings.value("output_format", "jpg")).lower().lstrip(".")
        index = self.output_format_combo.findData(saved)
        if index < 0:
            index = self.output_format_combo.findData("jpg")
        self.output_format_combo.setCurrentIndex(index)
        self._output_format_changed(index)

    def _update_output_directory_label(self) -> None:
        directory = self.controller.output_directory
        self.output_directory_label.setText(
            f"输出目录：{directory}" if directory else "输出目录：未选择"
        )

    def _show_error(self, code: str, detail: str) -> None:
        from app.ui.error_messages import message_for_error

        QMessageBox.warning(self, "处理失败", message_for_error(code, detail))

    @staticmethod
    def _set_application_font() -> None:
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None:
            app.setFont(QFont("Microsoft YaHei UI", 10))


class _ExportSignals(QObject):
    succeeded = Signal(str, int)
    failed = Signal(str, str, int)


class _OpenSignals(QObject):
    succeeded = Signal(object, object, int)
    failed = Signal(str, str, int)


class _PreviewSignals(QObject):
    succeeded = Signal(object, int)
    failed = Signal(str, str, int)


class _OpenWorker(QRunnable):
    def __init__(self, controller: SessionController, path: Path, preview_size, generation: int) -> None:
        super().__init__()
        self.controller = controller
        self.path = path
        self.preview_size = preview_size
        self.generation = generation
        self.signals = _OpenSignals()

    def run(self) -> None:
        try:
            session = self.controller.image_service.open(self.path)
            preview = self.controller.image_service.render_preview(session, self.preview_size)
            self.signals.succeeded.emit(session, preview, self.generation)
        except ImgFrameError as exc:
            self.signals.failed.emit(exc.code, exc.detail, self.generation)
        except MemoryError as exc:
            self.signals.failed.emit("memory_error", str(exc), self.generation)
        except Exception as exc:
            self.signals.failed.emit("image_load_failed", str(exc), self.generation)


class _PreviewWorker(QRunnable):
    def __init__(self, image_service, session, preview_size, generation: int) -> None:
        super().__init__()
        self.image_service = image_service
        self.session = session
        self.preview_size = preview_size
        self.generation = generation
        self.signals = _PreviewSignals()

    def run(self) -> None:
        try:
            preview = self.image_service.render_preview(self.session, self.preview_size)
            self.signals.succeeded.emit(preview, self.generation)
        except ImgFrameError as exc:
            self.signals.failed.emit(exc.code, exc.detail, self.generation)
        except MemoryError as exc:
            self.signals.failed.emit("memory_error", str(exc), self.generation)
        except Exception as exc:
            self.signals.failed.emit("image_load_failed", str(exc), self.generation)


class _ExportWorker(QRunnable):
    def __init__(self, controller: SessionController, generation: int) -> None:
        super().__init__()
        self.controller = controller
        self.generation = generation
        self.signals = _ExportSignals()

    def run(self) -> None:
        try:
            destination = self.controller.export()
            self.signals.succeeded.emit(str(destination), self.generation)
        except ImgFrameError as exc:
            self.signals.failed.emit(exc.code, exc.detail, self.generation)
        except MemoryError as exc:
            self.signals.failed.emit("memory_error", str(exc), self.generation)
        except Exception as exc:
            self.signals.failed.emit("export_failed", str(exc), self.generation)
