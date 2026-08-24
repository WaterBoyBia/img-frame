import pytest

from app.core.frame_layout import calculate_layout, load_microsoft_yahei


def test_classic_layout_expands_outside_original_image():
    lines = ["NIKON D750", "50mm    1/250s"]

    layout = calculate_layout((6000, 4000), lines)

    assert layout.border_px == 200
    assert layout.image_rect == (200, 200, 6000, 4000)
    assert layout.canvas_size[0] == 6400
    assert layout.canvas_size[1] > 4400
    assert layout.text_rect is not None
    assert layout.text_rect[0] == 200
    assert layout.text_rect[2] == 6000
    assert len(layout.text_positions) == 2


def test_empty_text_does_not_create_text_area():
    layout = calculate_layout((100, 80), [])

    assert layout.canvas_size == (108, 88)
    assert layout.text_rect is None
    assert layout.text_positions == ()


def test_long_text_gets_smaller_font_scale_but_stays_inside():
    layout = calculate_layout((1200, 800), ["A" * 300, "B" * 300])

    assert 0.6 <= layout.font_scale < 1.0
    assert layout.text_rect is not None
    assert layout.text_rect[2] <= layout.canvas_size[0]


def test_text_positions_center_each_line_in_text_rect():
    lines = ["CAMERA", "50mm"]

    layout = calculate_layout((1200, 800), lines)

    assert layout.text_rect is not None
    text_center = layout.text_rect[0] + layout.text_rect[2] / 2
    for position, text_size in zip(layout.text_positions, layout.text_sizes, strict=True):
        assert position[0] + text_size[0] / 2 == pytest.approx(text_center, abs=1)


def test_camera_model_uses_bold_font_metrics():
    layout = calculate_layout((1200, 800), ["CAMERA", "50mm"])
    bold_font = load_microsoft_yahei(layout.font_px, bold=True)
    regular_font = load_microsoft_yahei(layout.font_px)

    bold_bbox = bold_font.getbbox("CAMERA")
    regular_bbox = regular_font.getbbox("50mm")
    assert layout.bold_first_line is True
    assert layout.text_sizes[0][0] == bold_bbox[2] - bold_bbox[0]
    assert layout.text_sizes[1][0] == regular_bbox[2] - regular_bbox[0]


def test_parameter_only_line_can_remain_regular():
    layout = calculate_layout((1200, 800), ["50mm    100"], bold_first_line=False)

    assert layout.bold_first_line is False


@pytest.mark.parametrize("image_size", [(0, 100), (100, 0), (-1, 100)])
def test_rejects_invalid_image_sizes(image_size):
    with pytest.raises(ValueError):
        calculate_layout(image_size, ["CAMERA"])
