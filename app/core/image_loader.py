from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.errors import ImageLoadError, UnsupportedFormatError

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


@dataclass
class LoadedImage:
    pixels: np.ndarray
    icc_profile: bytes | None
    bit_depth: int
    mode: str
    orientation_applied: bool
    source_path: Path


class ImageLoader:
    def load(self, path: Path) -> LoadedImage:
        path = Path(path)
        if not path.is_file():
            raise ImageLoadError(f"file not found: {path}")
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise UnsupportedFormatError(f"unsupported format: {path.suffix}")
        try:
            with Image.open(path) as original:
                icc_profile = original.info.get("icc_profile")
                orientation = original.getexif().get(274, 1)
                image = ImageOps.exif_transpose(original)
                image = self._normalize_raster(image, path.suffix.lower())
                pixels = np.asarray(image).copy()
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise ImageLoadError(f"unable to read image: {path}") from exc

        if pixels.dtype == np.int32:
            pixels = np.clip(pixels, 0, 65535).astype(np.uint16)
        bit_depth = 16 if pixels.dtype == np.uint16 else 8
        return LoadedImage(
            pixels=pixels,
            icc_profile=icc_profile,
            bit_depth=bit_depth,
            mode=image.mode,
            orientation_applied=orientation != 1,
            source_path=path,
        )

    @staticmethod
    def _normalize_raster(image: Image.Image, suffix: str) -> Image.Image:
        if suffix in {".jpg", ".jpeg"}:
            return image.convert("RGB")
        if image.mode in {"RGB", "RGBA", "I;16", "I"}:
            return image
        if "transparency" in image.info:
            return image.convert("RGBA")
        return image.convert("RGB")
