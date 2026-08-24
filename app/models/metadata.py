from dataclasses import dataclass


@dataclass
class MetadataValues:
    camera_model: str | None = None
    focal_length_mm: float | None = None
    shutter_speed: str | None = None
    aperture: str | None = None
    iso: int | None = None
