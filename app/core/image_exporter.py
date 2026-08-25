from __future__ import annotations

import os
import struct
import tempfile
import zlib
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from app.core.errors import ExportError, ImgFrameError


class ImageExporter:
    def __init__(self) -> None:
        self.last_config: Any = None

    def write(
        self,
        image: Image.Image | np.ndarray,
        destination: Path,
        icc_profile: bytes | None = None,
    ) -> Path:
        destination = Path(destination)
        self._validate_destination(destination)
        try:
            array = _image_array(image)
            if destination.suffix.lower() == ".png":
                if _is_uint16_color(array):
                    _write_uint16_png(array, destination, icc_profile)
                else:
                    clean_image = _array_to_clean_image(array)
                    save_kwargs: dict[str, Any] = {
                        "format": "PNG",
                        "pnginfo": PngInfo(),
                        "compress_level": 1,
                    }
                    if icc_profile:
                        save_kwargs["icc_profile"] = icc_profile
                    clean_image.save(destination, **save_kwargs)
            else:
                clean_image = _array_to_jpeg_image(array)
                save_kwargs: dict[str, Any] = {
                    "format": "JPEG",
                    "quality": 95,
                    "subsampling": 0,
                    "optimize": True,
                }
                if icc_profile:
                    save_kwargs["icc_profile"] = icc_profile
                clean_image.save(destination, **save_kwargs)
        except ImgFrameError:
            raise
        except Exception as exc:
            raise ExportError(f"unable to write image: {destination}") from exc
        return destination

    def export(
        self,
        image: Image.Image | np.ndarray,
        destination: Path,
        icc_profile: bytes | None = None,
        config: Any = None,
    ) -> Path:
        destination = Path(destination)
        self._validate_destination(destination)
        self.last_config = config
        temporary_path: Path | None = None
        try:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{destination.stem}.",
                suffix=f".tmp{destination.suffix.lower()}",
                dir=destination.parent,
            )
            os.close(descriptor)
            temporary_path = Path(temporary_name)
            self.write(image, temporary_path, icc_profile)
            temporary_path.replace(destination)
            return destination
        except ImgFrameError:
            raise
        except Exception as exc:
            raise ExportError(f"unable to export image: {destination}") from exc
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass

    @staticmethod
    def _validate_destination(destination: Path) -> None:
        if destination.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            raise ExportError(f"PNG or JPG destination required: {destination}")
        if not destination.parent.is_dir():
            raise ExportError(f"output directory does not exist: {destination.parent}")


def _to_clean_image(image: Image.Image | np.ndarray) -> Image.Image:
    return _array_to_clean_image(_image_array(image))


def _array_to_clean_image(array: np.ndarray) -> Image.Image:

    if array.dtype not in (np.uint8, np.uint16):
        raise ExportError("image must use uint8 or uint16 pixels")
    if array.ndim == 2:
        if array.dtype == np.uint8:
            return Image.fromarray(array)
        return Image.fromarray(array, mode="I;16")
    if array.ndim != 3 or array.shape[2] not in (3, 4):
        raise ExportError("image must be grayscale, RGB, or RGBA")
    if array.dtype == np.uint8:
        return Image.fromarray(array)

    mode = "RGB" if array.shape[2] == 3 else "RGBA"
    raw = array.astype(">u2", copy=False).tobytes()
    return Image.frombytes(mode, (array.shape[1], array.shape[0]), raw, "raw", f"{mode};16B")


def _array_to_jpeg_image(array: np.ndarray) -> Image.Image:
    """Convert an 8/16-bit image to opaque 8-bit RGB for JPEG output."""
    if array.dtype not in (np.uint8, np.uint16):
        raise ExportError("image must use uint8 or uint16 pixels")
    if array.ndim == 2:
        rgb = np.repeat(array[:, :, None], 3, axis=2)
    elif array.ndim == 3 and array.shape[2] in (3, 4):
        rgb = array[:, :, :3]
        if array.shape[2] == 4:
            max_value = 255 if array.dtype == np.uint8 else 65535
            alpha = array[:, :, 3:4].astype(np.float64) / max_value
            background = np.full_like(rgb, max_value, dtype=np.float64)
            rgb = np.rint(rgb.astype(np.float64) * alpha + background * (1.0 - alpha))
    else:
        raise ExportError("image must be grayscale, RGB, or RGBA")

    if array.dtype == np.uint16:
        rgb = np.rint(np.asarray(rgb, dtype=np.float64) / 257.0)
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)
    return Image.fromarray(rgb)


def _image_array(image: Image.Image | np.ndarray) -> np.ndarray:
    if isinstance(image, Image.Image):
        return np.asarray(image).copy()
    if isinstance(image, np.ndarray):
        return np.asarray(image)
    raise ExportError("image must be a Pillow image or NumPy array")


def _is_uint16_color(array: np.ndarray) -> bool:
    return array.dtype == np.uint16 and array.ndim == 3 and array.shape[2] in (3, 4)


def _write_uint16_png(
    array: np.ndarray,
    destination: Path,
    icc_profile: bytes | None,
) -> None:
    height, width, channels = array.shape
    color_type = 2 if channels == 3 else 6
    rows = bytearray()
    for row in array:
        rows.append(0)
        rows.extend(row.astype(">u2", copy=False).tobytes())
    chunks = [
        _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 16, color_type, 0, 0, 0)),
    ]
    if icc_profile:
        chunks.append(_png_chunk(b"iCCP", b"icc\x00\x00" + zlib.compress(icc_profile)))
    chunks.append(_png_chunk(b"IDAT", zlib.compress(bytes(rows), level=1)))
    chunks.append(_png_chunk(b"IEND", b""))
    with destination.open("wb") as stream:
        stream.write(b"\x89PNG\r\n\x1a\n")
        for chunk in chunks:
            stream.write(chunk)


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    )
