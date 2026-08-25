from pathlib import Path


def test_main_window_starts_with_disabled_export(qtbot):
    from app.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    assert not window.export_button.isEnabled()
    assert window.open_button.isEnabled()
    assert window.output_format_combo.currentData() == "jpg"


def test_opening_existing_jpeg_enables_export(qtbot):
    from app.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.open_path(Path(__file__).parents[1] / "img-test" / "DSC_0061.JPG")

    assert window.export_button.isEnabled()
    assert window.camera_model_edit.text()


def test_selecting_png_updates_controller_and_export_button(qtbot):
    from app.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.output_format_combo.setCurrentIndex(window.output_format_combo.findData("png"))

    assert window.controller.output_format == "png"
    assert window.export_button.text() == "导出 PNG"


def test_editing_camera_model_updates_controller(qtbot):
    from app.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.open_path(Path(__file__).parents[1] / "img-test" / "DSC_0061.JPG")
    window.camera_model_edit.setText("TEST CAMERA")
    window.camera_model_edit.editingFinished.emit()

    assert window.controller.session.edited_metadata.camera_model == "TEST CAMERA"
