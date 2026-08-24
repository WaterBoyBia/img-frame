import numpy as np

from app.core.frame_layout import calculate_layout
from app.core.frame_renderer import FrameRenderer
from app.models.frame_config import FrameConfig


def test_16bit_source_keeps_dtype_and_source_values():
    source = np.zeros((4, 6, 3), dtype=np.uint16)
    source[:, :, 0] = 65535
    layout = calculate_layout((6, 4), ["CAMERA"], border_ratio=0.1)

    result = FrameRenderer().render(source, layout, FrameConfig(border_ratio=0.1), ["CAMERA"])

    assert result.dtype == np.uint16
    x, y, width, height = layout.image_rect
    assert int(result[y, x, 0]) == 65535


def test_16bit_frosted_frame_keeps_dtype():
    source = np.zeros((8, 8, 3), dtype=np.uint16)
    source[:, :, 1] = 40000
    layout = calculate_layout((8, 8), ["CAMERA"], border_ratio=0.2)

    result = FrameRenderer().render(
        source,
        layout,
        FrameConfig(material="frosted", border_ratio=0.2),
        ["CAMERA"],
    )

    assert result.dtype == np.uint16
