"""Project smoke tests for the first-stage runtime and error contract."""

import importlib


def test_runtime_dependencies_are_importable_and_versioned():
    for module_name in ("numpy", "PIL", "PySide6", "exifread", "rawpy", "pytestqt"):
        module = importlib.import_module(module_name)
        assert module.__name__ == module_name
        if module_name != "pytestqt":
            assert getattr(module, "__version__", "")


def test_error_types_expose_codes_and_detail():
    from app.core.errors import (
        ExportError,
        ImageLoadError,
        ImgFrameError,
        RawDecodeError,
    )

    cases = (
        (ImgFrameError, "unknown"),
        (ImageLoadError, "image_load_failed"),
        (RawDecodeError, "raw_decode_failed"),
        (ExportError, "export_failed"),
    )
    for error_type, code in cases:
        error = error_type("detail")
        assert error.code == code
        assert error.detail == "detail"
        assert str(error) == "detail"
