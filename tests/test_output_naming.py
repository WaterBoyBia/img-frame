import pytest

from app.core.output_naming import unique_output_path


def test_adds_framed_suffix_and_default_jpg_extension(tmp_path):
    source = tmp_path / "DSC_0061.JPG"

    assert unique_output_path(source, tmp_path).name == "DSC_0061_framed.jpg"


def test_increments_when_default_jpg_output_exists(tmp_path):
    source = tmp_path / "DSC_0061.JPG"
    (tmp_path / "DSC_0061_framed.jpg").touch()
    (tmp_path / "DSC_0061_framed_1.jpg").touch()

    assert unique_output_path(source, tmp_path).name == "DSC_0061_framed_2.jpg"


def test_uses_selected_png_extension_and_its_own_collision_sequence(tmp_path):
    source = tmp_path / "DSC_0061.JPG"
    (tmp_path / "DSC_0061_framed.png").touch()

    assert unique_output_path(source, tmp_path, "png").name == "DSC_0061_framed_1.png"


def test_rejects_missing_output_directory(tmp_path):
    with pytest.raises(ValueError):
        unique_output_path(tmp_path / "photo.jpg", tmp_path / "missing")
