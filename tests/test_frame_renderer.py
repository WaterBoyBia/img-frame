import numpy as np
from unittest.mock import patch

from app.core.frame_layout import calculate_layout
from app.core.frame_renderer import FrameRenderer
from app.models.frame_config import FrameConfig


def test_solid_renderer_copies_original_pixels_to_image_rect():
    source = np.zeros((4, 6, 3), dtype=np.uint8)
    source[:, :, 0] = 123
    lines = ["CAMERA", "50mm    100"]
    layout = calculate_layout((6, 4), lines, border_ratio=0.1)

    result = FrameRenderer().render(source, layout, FrameConfig(border_ratio=0.1), lines)

    x, y, width, height = layout.image_rect
    assert result[y : y + height, x : x + width, :3].tolist() == source.tolist()
    assert result.dtype == np.uint8
    assert result.shape[2] == 4


def test_white_frame_uses_alpha_from_opacity():
    source = np.zeros((4, 6, 3), dtype=np.uint8)
    layout = calculate_layout((6, 4), ["CAMERA"], border_ratio=0.1)

    result = FrameRenderer().render(
        source,
        layout,
        FrameConfig(opacity=0.5, border_ratio=0.1),
        ["CAMERA"],
    )

    assert result.shape[2] == 4
    assert tuple(result[0, 0]) == (255, 255, 255, 127)


def test_renderer_uses_bold_font_only_for_camera_model():
    source = np.zeros((80, 120, 3), dtype=np.uint8)
    lines = ["CAMERA", "50mm    100"]
    layout = calculate_layout((120, 80), lines, border_ratio=0.1)
    from app.core.frame_layout import load_microsoft_yahei

    calls = []

    def record_font(size, bold=False):
        calls.append(bold)
        return load_microsoft_yahei(size, bold=bold)

    with patch("app.core.frame_renderer.load_microsoft_yahei", side_effect=record_font):
        FrameRenderer().render(source, layout, FrameConfig(border_ratio=0.1), lines)

    assert calls == [True, False]
