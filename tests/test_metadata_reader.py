from pathlib import Path

from app.core.metadata_reader import MetadataReader


def test_reads_metadata_from_existing_jpeg():
    path = Path(__file__).parents[1] / "img-test" / "DSC_0061.JPG"

    values = MetadataReader().read(path)

    assert values.camera_model or values.focal_length_mm or values.iso


def test_missing_fields_return_none(tmp_path):
    from PIL import Image

    path = tmp_path / "without-exif.jpg"
    Image.new("RGB", (8, 8), "white").save(path)

    values = MetadataReader().read(path)

    assert values.camera_model is None
    assert values.focal_length_mm is None
    assert values.iso is None
