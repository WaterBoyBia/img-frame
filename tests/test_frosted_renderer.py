import numpy as np

from app.core.frame_layout import calculate_layout
from app.core.frame_renderer import FrameRenderer
from app.models.frame_config import FrameConfig


def test_frosted_frame_changes_outer_pixels_but_not_original_area():
    source = np.zeros((8, 8, 3), dtype=np.uint8)
    source[:, :, 1] = 200
    layout = calculate_layout((8, 8), ["CAMERA"], border_ratio=0.2)

    result = FrameRenderer().render(
        source,
        layout,
        FrameConfig(material="frosted", border_ratio=0.2, blur_ratio=0.05),
        ["CAMERA"],
    )

    x, y, width, height = layout.image_rect
    assert np.array_equal(result[y : y + height, x : x + width, :3], source)
    assert not np.array_equal(result[0, 0, :3], source[0, 0])
