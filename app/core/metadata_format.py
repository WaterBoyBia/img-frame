from __future__ import annotations

from app.models.metadata import MetadataValues


def _format_focal_length(value: float | None) -> str:
    if value is None:
        return ""
    if float(value).is_integer():
        return f"{int(value)}mm"
    return f"{value:g}mm"


def _format_iso(value: int | None) -> str:
    return "" if value is None else str(int(value))


def format_display_lines(values: MetadataValues) -> list[str]:
    first_line = (values.camera_model or "").strip()
    second_values = [
        _format_focal_length(values.focal_length_mm),
        (values.shutter_speed or "").strip(),
        (values.aperture or "").strip(),
        _format_iso(values.iso),
    ]
    second_line = "    ".join(value for value in second_values if value)
    return [line for line in (first_line, second_line) if line]
