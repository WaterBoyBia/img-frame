from __future__ import annotations

from pathlib import Path


SUPPORTED_OUTPUT_FORMATS = {"jpg", "png"}


def normalize_output_format(output_format: str | None) -> str:
    """Return the canonical output format used for file naming and encoding."""
    value = "jpg" if output_format is None else str(output_format).strip().lower()
    value = value.removeprefix(".")
    if value == "jpeg":
        value = "jpg"
    if value not in SUPPORTED_OUTPUT_FORMATS:
        raise ValueError(f"unsupported output format: {output_format}")
    return value


def unique_output_path(
    source_path: Path,
    output_dir: Path,
    output_format: str = "jpg",
) -> Path:
    source_path = Path(source_path)
    output_dir = Path(output_dir)
    if not output_dir.is_dir():
        raise ValueError(f"output directory does not exist: {output_dir}")

    extension = normalize_output_format(output_format)
    base_name = f"{source_path.stem}_framed"
    candidate = output_dir / f"{base_name}.{extension}"
    suffix = 1
    while candidate.exists():
        candidate = output_dir / f"{base_name}_{suffix}.{extension}"
        suffix += 1
    return candidate
