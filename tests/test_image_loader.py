from pathlib import Path

import numpy as np

from app.core.image_loader import ImageLoader


def test_loads_existing_jpeg_with_expected_shape_and_bit_depth():
    path = Path(__file__).parents[1] / "img-test" / "DSC_0061.JPG"

    image = ImageLoader().load(path)

    assert image.pixels.ndim == 3
    assert image.pixels.shape[2] == 3
    assert image.pixels.dtype == np.uint8
    assert image.bit_depth == 8


def test_loads_png_without_text_metadata(tmp_path):
    from PIL import Image

    path = tmp_path / "simple.png"
    Image.new("RGBA", (10, 6), (1, 2, 3, 255)).save(path)

    image = ImageLoader().load(path)

    assert image.pixels.shape == (6, 10, 4)
    assert image.bit_depth == 8
