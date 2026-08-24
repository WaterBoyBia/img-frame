import numpy as np
from PIL import Image

from app.core.frame_layout import calculate_layout
from app.core.frame_renderer import FrameRenderer
from app.core.image_exporter import ImageExporter
from app.core.image_loader import ImageLoader
from app.core.metadata_format import format_display_lines
from app.core.metadata_reader import MetadataReader
from app.models.frame_config import FrameConfig
from tests.conftest import JPEG_IMAGE_PATH


def test_existing_jpeg_can_be_framed_without_metadata(tmp_path):
    loaded = ImageLoader().load(JPEG_IMAGE_PATH)
    values = MetadataReader().read(JPEG_IMAGE_PATH)
    lines = format_display_lines(values)
    layout = calculate_layout(
        (loaded.pixels.shape[1], loaded.pixels.shape[0]),
        lines,
    )
    rendered = FrameRenderer().render(
        loaded.pixels,
        layout,
        FrameConfig(),
        lines,
    )
    destination = tmp_path / "framed.png"

    ImageExporter().write(rendered, destination, loaded.icc_profile)

    with Image.open(destination) as output:
        output_pixels = np.asarray(output).copy()
        assert output.format == "PNG"
        assert output.info.get("icc_profile") == loaded.icc_profile
        assert output.size == layout.canvas_size
        assert set(output.info).issubset({"icc_profile"})

    x, y, width, height = layout.image_rect
    output_source_area = output_pixels[y : y + height, x : x + width, :3]
    assert np.array_equal(output_source_area, loaded.pixels[:, :, :3])
