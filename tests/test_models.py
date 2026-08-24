from app.models.frame_config import FrameConfig
from app.models.metadata import MetadataValues


def test_metadata_defaults_are_empty():
    values = MetadataValues()

    assert values.camera_model is None
    assert values.focal_length_mm is None
    assert values.shutter_speed is None
    assert values.aperture is None
    assert values.iso is None


def test_frame_config_defaults_match_approved_design():
    config = FrameConfig()

    assert config.material == "solid"
    assert config.color == (255, 255, 255, 255)
    assert config.opacity == 1.0
    assert config.border_ratio == 0.05
    assert config.font_ratio == 0.024


def test_frame_config_rejects_invalid_ranges():
    try:
        FrameConfig(opacity=1.5)
    except ValueError:
        pass
    else:
        raise AssertionError("opacity outside [0, 1] must fail")
