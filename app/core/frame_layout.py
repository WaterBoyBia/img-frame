from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Sequence

from PIL import ImageFont
from PIL.ImageFont import FreeTypeFont

from app.core.errors import FontUnavailableError

FONT_CANDIDATES = (
    "msyh.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/msyh.ttf",
)


@dataclass(frozen=True)
class FrameLayout:
    canvas_size: tuple[int, int]
    image_rect: tuple[int, int, int, int]
    text_rect: tuple[int, int, int, int] | None
    border_px: int
    font_px: int
    font_scale: float
    text_positions: tuple[tuple[int, int], ...] = ()
    text_sizes: tuple[tuple[int, int], ...] = ()


def calculate_layout(
    image_size: tuple[int, int],
    lines: Sequence[str],
    border_ratio: float = 0.05,
    font_ratio: float = 0.024,
) -> FrameLayout:
    width, height = image_size
    _validate_inputs(width, height, border_ratio, font_ratio)

    short_edge = min(width, height)
    border_px = max(1, round(short_edge * border_ratio))
    initial_font_px = max(1, round(short_edge * font_ratio))
    visible_lines = tuple(str(line) for line in lines if str(line).strip())
    image_rect = (border_px, border_px, width, height)

    if not visible_lines:
        return FrameLayout(
            canvas_size=(width + 2 * border_px, height + 2 * border_px),
            image_rect=image_rect,
            text_rect=None,
            border_px=border_px,
            font_px=initial_font_px,
            font_scale=1.0,
        )

    font_px, font_scale, font = _fit_font(
        visible_lines,
        initial_font_px,
        width,
    )
    text_metrics = tuple(_text_metrics(font, line) for line in visible_lines)
    line_height = max(_font_line_height(font), *(height for _, height, _, _ in text_metrics))
    line_spacing = max(1, round(font_px * 0.35))
    vertical_padding = max(1, round(font_px * 0.75))
    line_slots = max(2, len(visible_lines))
    text_area_height = (
        2 * vertical_padding
        + line_slots * line_height
        + (line_slots - 1) * line_spacing
    )
    text_rect = (border_px, border_px + height, width, text_area_height)
    text_positions, text_sizes = _position_lines(
        text_rect,
        text_metrics,
        line_height,
        line_spacing,
    )

    return FrameLayout(
        canvas_size=(
            width + 2 * border_px,
            height + 2 * border_px + text_area_height,
        ),
        image_rect=image_rect,
        text_rect=text_rect,
        border_px=border_px,
        font_px=font_px,
        font_scale=font_scale,
        text_positions=text_positions,
        text_sizes=text_sizes,
    )


def load_microsoft_yahei(size: int) -> FreeTypeFont:
    """Load the project font from Windows using stable fallback paths."""
    last_error: OSError | None = None
    for candidate in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError as exc:
            last_error = exc
    raise FontUnavailableError("Microsoft YaHei font is unavailable") from last_error


def _fit_font(
    lines: Sequence[str],
    initial_size: int,
    available_width: int,
) -> tuple[int, float, FreeTypeFont]:
    minimum_size = max(1, ceil(initial_size * 0.6))
    for size in range(initial_size, minimum_size - 1, -1):
        font = load_microsoft_yahei(size)
        if all(_text_metrics(font, line)[0] <= available_width for line in lines):
            return size, size / initial_size, font
    font = load_microsoft_yahei(minimum_size)
    return minimum_size, minimum_size / initial_size, font


def _text_metrics(font: FreeTypeFont, text: str) -> tuple[int, int, int, int]:
    left, top, right, bottom = font.getbbox(text)
    return right - left, bottom - top, left, top


def _font_line_height(font: FreeTypeFont) -> int:
    ascent, descent = font.getmetrics()
    return max(1, ascent + descent)


def _position_lines(
    text_rect: tuple[int, int, int, int],
    metrics: Sequence[tuple[int, int, int, int]],
    line_height: int,
    line_spacing: int,
) -> tuple[tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]]:
    rect_x, rect_y, rect_width, rect_height = text_rect
    content_height = len(metrics) * line_height + max(0, len(metrics) - 1) * line_spacing
    line_top = rect_y + (rect_height - content_height) // 2
    positions: list[tuple[int, int]] = []
    sizes: list[tuple[int, int]] = []
    for index, (text_width, text_height, bbox_left, bbox_top) in enumerate(metrics):
        visible_x = rect_x + (rect_width - text_width) // 2
        visible_y = line_top + index * (line_height + line_spacing)
        positions.append((visible_x - bbox_left, visible_y - bbox_top))
        sizes.append((text_width, text_height))
    return tuple(positions), tuple(sizes)


def _validate_inputs(
    width: int,
    height: int,
    border_ratio: float,
    font_ratio: float,
) -> None:
    if width <= 0 or height <= 0:
        raise ValueError("image dimensions must be positive")
    if not 0.0 < border_ratio <= 0.2:
        raise ValueError("border_ratio must be in (0, 0.2]")
    if not 0.0 < font_ratio <= 0.1:
        raise ValueError("font_ratio must be in (0, 0.1]")
