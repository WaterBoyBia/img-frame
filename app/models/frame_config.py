from dataclasses import dataclass


@dataclass
class FrameConfig:
    material: str = "solid"
    color: tuple[int, int, int, int] = (255, 255, 255, 255)
    opacity: float = 1.0
    border_ratio: float = 0.05
    font_ratio: float = 0.024
    blur_ratio: float = 0.03

    def __post_init__(self) -> None:
        if self.material not in {"solid", "frosted"}:
            raise ValueError("unsupported frame material")
        if not 0.0 <= self.opacity <= 1.0:
            raise ValueError("opacity must be between 0 and 1")
        if not 0.0 < self.border_ratio <= 0.2:
            raise ValueError("border_ratio must be in (0, 0.2]")
        if not 0.0 < self.font_ratio <= 0.1:
            raise ValueError("font_ratio must be in (0, 0.1]")
        if not 0.0 < self.blur_ratio <= 0.2:
            raise ValueError("blur_ratio must be in (0, 0.2]")
