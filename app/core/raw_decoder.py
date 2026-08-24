from __future__ import annotations

from pathlib import Path

import numpy as np
import rawpy
from PIL import ImageCms

from app.core.errors import RawDecodeError
from app.core.image_loader import LoadedImage


class RawDecoder:
    """Decode camera RAW files to an oriented-independent 16-bit RGB image."""

    def decode(self, path: Path) -> LoadedImage:
        path = Path(path)
        raw = None
        try:
            raw = rawpy.imread(path)
            pixels = raw.postprocess(
                use_camera_wb=True,
                no_auto_bright=True,
                output_bps=16,
                output_color=rawpy.ColorSpace.sRGB,
            )
            pixels = np.asarray(pixels)
            if pixels.ndim != 3 or pixels.shape[2] != 3:
                raise ValueError("RAW decoder returned a non-RGB image")
            if pixels.dtype != np.uint16:
                pixels = np.clip(pixels, 0, 65535).astype(np.uint16)
            pixels = pixels.copy()
        except RawDecodeError:
            raise
        except Exception as exc:
            raise RawDecodeError(f"unable to decode RAW image: {path}") from exc
        finally:
            close = getattr(raw, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass

        return LoadedImage(
            pixels=pixels,
            icc_profile=_srgb_icc_profile(),
            bit_depth=16,
            mode="RGB",
            orientation_applied=False,
            source_path=path,
        )


def _srgb_icc_profile() -> bytes:
    """Return an embedded sRGB profile for PNG export."""
    profile = ImageCms.createProfile("sRGB")
    return ImageCms.ImageCmsProfile(profile).tobytes()
