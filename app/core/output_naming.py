from __future__ import annotations

from pathlib import Path


def unique_output_path(source_path: Path, output_dir: Path) -> Path:
    source_path = Path(source_path)
    output_dir = Path(output_dir)
    if not output_dir.is_dir():
        raise ValueError(f"output directory does not exist: {output_dir}")

    base_name = f"{source_path.stem}_framed"
    candidate = output_dir / f"{base_name}.png"
    suffix = 1
    while candidate.exists():
        candidate = output_dir / f"{base_name}_{suffix}.png"
        suffix += 1
    return candidate
