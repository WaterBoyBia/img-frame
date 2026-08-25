from pathlib import Path

import numpy as np
import pytest

from app.core.session_controller import SessionController
from app.core.errors import InvalidMetadataError, NoSessionError
from app.models.frame_config import FrameConfig
from app.models.image_session import ImageSession
from app.models.metadata import MetadataValues


def make_test_session(path: Path) -> ImageSession:
    values = MetadataValues(camera_model="TEST")
    return ImageSession(
        source_path=path,
        pixels=np.zeros((4, 4, 3), dtype=np.uint8),
        icc_profile=None,
        bit_depth=8,
        metadata=values,
        edited_metadata=MetadataValues(camera_model="TEST"),
        frame_config=FrameConfig(),
        orientation_applied=True,
    )


class FakeImageService:
    def open(self, path):
        return make_test_session(path)

    def render_preview(self, session, max_size):
        return session.pixels.copy()

    def render_export(self, session):
        return session.pixels.copy()


class FakeExporter:
    def __init__(self):
        self.last_config = None

    def export(self, image, destination, icc_profile, config):
        self.last_config = config
        destination.touch()
        return destination


def make_controller_with_fakes():
    exporter = FakeExporter()
    controller = SessionController(image_service=FakeImageService(), exporter=exporter)
    return controller, exporter


def test_open_image_creates_session_and_preview(tmp_path):
    controller, _ = make_controller_with_fakes()
    source_path = tmp_path / "photo.jpg"

    session = controller.open_image(source_path)

    assert session.source_path == source_path
    assert controller.preview is not None
    assert controller.output_directory == tmp_path


def test_export_uses_unique_path_and_current_frame_config(tmp_path):
    controller, exporter = make_controller_with_fakes()
    source_path = tmp_path / "photo.jpg"
    controller.open_image(source_path)
    controller.set_output_directory(tmp_path)

    output_path = controller.export()

    assert output_path.name == "photo_framed.jpg"
    assert exporter.last_config == controller.session.frame_config


def test_export_uses_selected_png_format(tmp_path):
    controller, _ = make_controller_with_fakes()
    controller.open_image(tmp_path / "photo.jpg")
    controller.set_output_format("png")

    output_path = controller.export()

    assert output_path.name == "photo_framed.png"


def test_output_format_defaults_to_jpg_and_rejects_unknown_values():
    controller, _ = make_controller_with_fakes()

    assert controller.output_format == "jpg"
    with pytest.raises(ValueError):
        controller.set_output_format("tiff")


def test_preview_updates_are_coalesced_until_rendered(tmp_path):
    controller, _ = make_controller_with_fakes()
    controller.open_image(tmp_path / "photo.jpg")

    assert controller.schedule_preview_update() is True
    assert controller.schedule_preview_update() is False
    controller.render_preview()
    assert controller.schedule_preview_update() is True


def test_invalid_metadata_and_missing_session_use_structured_errors(tmp_path):
    controller, _ = make_controller_with_fakes()

    with pytest.raises(NoSessionError):
        controller.export()

    controller.open_image(tmp_path / "photo.jpg")
    with pytest.raises(InvalidMetadataError):
        controller.update_metadata(iso=0)
