import pytest

from app.core.output_naming import unique_output_path


def test_adds_framed_suffix_and_png_extension(tmp_path):
    source = tmp_path / "DSC_0061.JPG"

    assert unique_output_path(source, tmp_path).name == "DSC_0061_framed.png"


def test_increments_when_output_exists(tmp_path):
    source = tmp_path / "DSC_0061.JPG"
    (tmp_path / "DSC_0061_framed.png").touch()
    (tmp_path / "DSC_0061_framed_1.png").touch()

    assert unique_output_path(source, tmp_path).name == "DSC_0061_framed_2.png"


def test_rejects_missing_output_directory(tmp_path):
    with pytest.raises(ValueError):
        unique_output_path(tmp_path / "photo.jpg", tmp_path / "missing")
