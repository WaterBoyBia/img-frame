from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.models.frame_config import FrameConfig
from app.models.metadata import MetadataValues


@dataclass
class ImageSession:
    source_path: Path
    pixels: np.ndarray
    icc_profile: bytes | None
    bit_depth: int
    metadata: MetadataValues
    edited_metadata: MetadataValues
    frame_config: FrameConfig
    orientation_applied: bool
