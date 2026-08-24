from __future__ import annotations

from pathlib import Path
from typing import Any

import exifread

from app.models.metadata import MetadataValues


def _ratio_to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        numerator = getattr(value, "num", None)
        denominator = getattr(value, "den", None)
        if numerator is not None and denominator not in (None, 0):
            return float(numerator) / float(denominator)
        text = str(value).strip()
        if "/" in text:
            left, right = text.split("/", 1)
            return float(left) / float(right)
        return float(text)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _format_number(value: float | None) -> str | None:
    if value is None:
        return None
    if value.is_integer():
        return str(int(value))
    return f"{value:g}"


def _format_shutter(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if "/" in text:
        left, right = text.split("/", 1)
        try:
            return f"{int(left)}/{int(right)}s"
        except ValueError:
            pass
    number = _ratio_to_float(value)
    return None if number is None else f"{_format_number(number)}s"


def _format_aperture(value: Any) -> str | None:
    number = _ratio_to_float(value)
    return None if number is None else f"f/{_format_number(number)}"


class MetadataReader:
    def read(self, path: Path) -> MetadataValues:
        with path.open("rb") as stream:
            tags = exifread.process_file(stream, details=False)

        model = tags.get("Image Model")
        focal = _ratio_to_float(tags.get("EXIF FocalLength"))
        shutter = _format_shutter(tags.get("EXIF ExposureTime"))
        aperture = _format_aperture(tags.get("EXIF FNumber"))
        iso = self._read_iso(tags.get("EXIF ISOSpeedRatings"))
        return MetadataValues(
            camera_model=str(model).strip() if model else None,
            focal_length_mm=focal,
            shutter_speed=shutter,
            aperture=aperture,
            iso=iso,
        )

    @staticmethod
    def _read_iso(value: Any) -> int | None:
        number = _ratio_to_float(value)
        if number is None:
            return None
        return int(number)
