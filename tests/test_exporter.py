import numpy as np
import pytest
from PIL import Image, ImageCms

from app.core.errors import ExportError
from app.core.image_exporter import ImageExporter


def test_exports_png_with_icc_but_without_text_metadata(tmp_path):
    source = Image.new("RGB", (4, 4), "red")
    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    destination = tmp_path / "result.png"

    ImageExporter().write(source, destination, icc_profile=icc)

    output = Image.open(destination)
    assert output.format == "PNG"
    assert output.info.get("icc_profile") == icc
    assert not any(key in output.info for key in ("exif", "xmp", "XML:com.adobe.xmp", "parameters"))


def test_export_atomically_writes_uint16_array_and_records_config(tmp_path):
    source = np.zeros((3, 5, 4), dtype=np.uint16)
    source[:, :, 0] = 65535
    destination = tmp_path / "result.png"
    config = object()

    exporter = ImageExporter()
    result = exporter.export(source, destination, config=config)

    assert result == destination
    output = Image.open(destination)
    assert output.mode == "RGBA"
    assert _png_bit_depth(destination) == 16
    assert exporter.last_config is config


def test_rejects_non_png_destination(tmp_path):
    with pytest.raises(ExportError):
        ImageExporter().write(Image.new("RGB", (1, 1)), tmp_path / "result.jpg")


def _png_bit_depth(path):
    return path.read_bytes()[24]
