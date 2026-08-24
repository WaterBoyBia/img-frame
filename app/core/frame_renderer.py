from __future__ import annotations

from typing import Sequence

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from app.core.errors import FontUnavailableError
from app.core.frame_layout import FrameLayout, load_microsoft_yahei
from app.models.frame_config import FrameConfig


class FrameRenderer:
    def render(
        self,
        source: np.ndarray,
        layout: FrameLayout,
        config: FrameConfig,
        lines: Sequence[str],
    ) -> np.ndarray:
        self._validate_source(source, layout)
        max_value = _max_value(source.dtype)
        if config.material == "frosted":
            result = self._render_frosted(source, layout, config, max_value)
        else:
            result = self._render_solid(source, layout, config, max_value)
        self._draw_text(result, layout, config, lines, max_value)
        return result

    @staticmethod
    def _render_solid(
        source: np.ndarray,
        layout: FrameLayout,
        config: FrameConfig,
        max_value: int,
    ) -> np.ndarray:
        canvas = np.empty(
            (layout.canvas_size[1], layout.canvas_size[0], 4),
            dtype=source.dtype,
        )
        frame_color = _scaled_color(config.color[:3], max_value)
        frame_alpha = _scaled_alpha(config.opacity, max_value)
        canvas[:, :, :3] = frame_color
        canvas[:, :, 3] = frame_alpha
        _copy_source(canvas, source, layout, max_value)
        return canvas

    @staticmethod
    def _render_frosted(
        source: np.ndarray,
        layout: FrameLayout,
        config: FrameConfig,
        max_value: int,
    ) -> np.ndarray:
        source_rgb = source[:, :, :3]
        left, top, width, height = layout.image_rect
        bottom_padding = layout.canvas_size[1] - (top + height)
        extended = np.pad(
            source_rgb,
            ((top, bottom_padding), (left, left), (0, 0)),
            mode="edge",
        )
        radius = max(1, round(min(source.shape[:2]) * config.blur_ratio))
        blurred = _gaussian_blur(extended, radius)
        color = np.asarray(_scaled_color(config.color[:3], max_value), dtype=np.float64)
        base = blurred.astype(np.float64)
        overlay_weight = float(config.opacity)
        background = np.rint(base * (1.0 - overlay_weight) + color * overlay_weight)
        canvas = np.empty((*background.shape[:2], 4), dtype=source.dtype)
        canvas[:, :, :3] = np.clip(background, 0, max_value).astype(source.dtype)
        canvas[:, :, 3] = _scaled_alpha(config.opacity, max_value)
        _copy_source(canvas, source, layout, max_value)
        return canvas

    @staticmethod
    def _draw_text(
        canvas: np.ndarray,
        layout: FrameLayout,
        config: FrameConfig,
        lines: Sequence[str],
        max_value: int,
    ) -> None:
        visible_lines = [str(line) for line in lines if str(line).strip()]
        if not visible_lines or layout.text_rect is None:
            return
        try:
            font = load_microsoft_yahei(layout.font_px)
        except FontUnavailableError:
            raise
        except OSError as exc:
            raise FontUnavailableError("Microsoft YaHei font is unavailable") from exc

        mask = Image.new("L", layout.canvas_size, 0)
        draw = ImageDraw.Draw(mask)
        for line, position in zip(visible_lines, layout.text_positions):
            draw.text(position, line, font=font, fill=255)
        mask_array = np.asarray(mask, dtype=np.float64) / 255.0
        luminance = (
            0.299 * config.color[0]
            + 0.587 * config.color[1]
            + 0.114 * config.color[2]
        )
        text_value = 0 if luminance >= 128 else max_value
        blend = mask_array[:, :, None]
        canvas[:, :, :3] = np.rint(
            canvas[:, :, :3].astype(np.float64) * (1.0 - blend)
            + text_value * blend
        ).astype(canvas.dtype)

    @staticmethod
    def _validate_source(source: np.ndarray, layout: FrameLayout) -> None:
        if not isinstance(source, np.ndarray) or source.ndim != 3:
            raise ValueError("source must be a three-dimensional image array")
        if source.shape[2] not in (3, 4):
            raise ValueError("source must have RGB or RGBA channels")
        if source.dtype not in (np.uint8, np.uint16):
            raise ValueError("source must use uint8 or uint16 pixels")
        _, _, width, height = layout.image_rect
        if source.shape[1] != width or source.shape[0] != height:
            raise ValueError("source dimensions do not match layout")


def _copy_source(
    canvas: np.ndarray,
    source: np.ndarray,
    layout: FrameLayout,
    max_value: int,
) -> None:
    x, y, width, height = layout.image_rect
    if source.shape[2] == 4:
        canvas[y : y + height, x : x + width] = source
        return
    canvas[y : y + height, x : x + width, :3] = source
    canvas[y : y + height, x : x + width, 3] = max_value


def _max_value(dtype: np.dtype) -> int:
    if dtype == np.uint8:
        return 255
    if dtype == np.uint16:
        return 65535
    raise ValueError("source must use uint8 or uint16 pixels")


def _scaled_color(color: tuple[int, int, int], max_value: int) -> tuple[int, int, int]:
    scale = max_value / 255.0
    return tuple(int(round(max(0, min(255, value)) * scale)) for value in color)


def _scaled_alpha(opacity: float, max_value: int) -> int:
    return int(opacity * max_value)


def _gaussian_blur(array: np.ndarray, radius: int) -> np.ndarray:
    if array.dtype == np.uint8:
        return np.asarray(Image.fromarray(array).filter(ImageFilter.GaussianBlur(radius)))
    channels = []
    for index in range(3):
        channel = array[:, :, index]
        high = np.asarray(
            Image.fromarray((channel >> 8).astype(np.uint8)).filter(
                ImageFilter.GaussianBlur(radius)
            ),
            dtype=np.uint16,
        )
        low = np.asarray(
            Image.fromarray((channel & 0xFF).astype(np.uint8)).filter(
                ImageFilter.GaussianBlur(radius)
            ),
            dtype=np.uint16,
        )
        channels.append((high << 8) | low)
    return np.stack(channels, axis=2)
