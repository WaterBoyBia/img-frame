from __future__ import annotations

from pathlib import Path

import numpy as np

from app.core.frame_layout import calculate_layout
from app.core.frame_renderer import FrameRenderer
from app.core.image_loader import ImageLoader
from app.core.metadata_format import format_display_lines
from app.core.metadata_reader import MetadataReader
from app.models.frame_config import FrameConfig
from app.models.image_session import ImageSession
from app.models.metadata import MetadataValues


class ImageService:
    def __init__(
        self,
        loader: ImageLoader | None = None,
        metadata_reader: MetadataReader | None = None,
        renderer: FrameRenderer | None = None,
    ) -> None:
        self.loader = loader or ImageLoader()
        self.metadata_reader = metadata_reader or MetadataReader()
        self.renderer = renderer or FrameRenderer()

    def open(self, path: Path) -> ImageSession:
        path = Path(path)
        loaded = self.loader.load(path)
        metadata = self.metadata_reader.read(path)
        return ImageSession(
            source_path=loaded.source_path,
            pixels=loaded.pixels,
            icc_profile=loaded.icc_profile,
            bit_depth=loaded.bit_depth,
            metadata=metadata,
            edited_metadata=_copy_metadata(metadata),
            frame_config=FrameConfig(),
            orientation_applied=loaded.orientation_applied,
        )

    def render_preview(self, session: ImageSession, max_size: tuple[int, int] | int) -> np.ndarray:
        preview_pixels = _fit_pixels(session.pixels, max_size)
        preview_session = ImageSession(
            source_path=session.source_path,
            pixels=preview_pixels,
            icc_profile=session.icc_profile,
            bit_depth=session.bit_depth,
            metadata=session.metadata,
            edited_metadata=session.edited_metadata,
            frame_config=session.frame_config,
            orientation_applied=session.orientation_applied,
        )
        return self._render(preview_session)

    def render_export(self, session: ImageSession) -> np.ndarray:
        return self._render(session)

    def _render(self, session: ImageSession) -> np.ndarray:
        lines = format_display_lines(session.edited_metadata)
        height, width = session.pixels.shape[:2]
        layout = calculate_layout(
            (width, height),
            lines,
            border_ratio=session.frame_config.border_ratio,
            font_ratio=session.frame_config.font_ratio,
            bold_first_line=bool(session.edited_metadata.camera_model),
        )
        return self.renderer.render(session.pixels, layout, session.frame_config, lines)


def _copy_metadata(values: MetadataValues) -> MetadataValues:
    return MetadataValues(
        camera_model=values.camera_model,
        focal_length_mm=values.focal_length_mm,
        shutter_speed=values.shutter_speed,
        aperture=values.aperture,
        iso=values.iso,
    )


def _fit_pixels(pixels: np.ndarray, max_size: tuple[int, int] | int) -> np.ndarray:
    if isinstance(max_size, int):
        max_width = max_height = max_size
    else:
        max_width, max_height = max_size
    if max_width <= 0 or max_height <= 0:
        raise ValueError("preview size must be positive")
    height, width = pixels.shape[:2]
    scale = min(1.0, max_width / width, max_height / height)
    if scale == 1.0:
        return pixels.copy()
    target_size = (max(1, round(width * scale)), max(1, round(height * scale)))
    from PIL import Image

    if pixels.dtype == np.uint8:
        image = Image.fromarray(pixels)
        resized = image.resize(target_size, Image.Resampling.LANCZOS)
        return np.asarray(resized).copy()
    if pixels.dtype == np.uint16:
        channels = pixels.shape[2]
        resized_channels = []
        for index in range(channels):
            channel = Image.fromarray((pixels[:, :, index] >> 8).astype(np.uint8))
            resized = channel.resize(target_size, Image.Resampling.LANCZOS)
            resized_channels.append(np.asarray(resized, dtype=np.uint16) * 257)
        return np.stack(resized_channels, axis=2)
    raise ValueError("pixels must use uint8 or uint16 dtype")
