from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from app.core.errors import (
    ExportError,
    ImgFrameError,
    InvalidMetadataError,
    NoSessionError,
    OutputNotWritableError,
)
from app.core.image_exporter import ImageExporter
from app.core.image_service import ImageService
from app.core.output_naming import normalize_output_format, unique_output_path
from app.models.frame_config import FrameConfig
from app.models.image_session import ImageSession
from app.models.metadata import MetadataValues


class SessionController:
    def __init__(
        self,
        image_service: ImageService | Any | None = None,
        exporter: ImageExporter | Any | None = None,
    ) -> None:
        self.image_service = image_service or ImageService()
        self.exporter = exporter or ImageExporter()
        self.session: ImageSession | None = None
        self.output_directory: Path | None = None
        self.output_format = "jpg"
        self.preview: np.ndarray | None = None
        self._preview_pending = False

    def open_image(self, path: Path, preview_size: tuple[int, int] | int = (1200, 900)) -> ImageSession:
        session = self.image_service.open(Path(path))
        self.session = session
        self.output_directory = session.source_path.parent
        self.preview = self.image_service.render_preview(session, preview_size)
        self._preview_pending = False
        return session

    def set_metadata(self, metadata: MetadataValues) -> None:
        session = self._require_session()
        if not isinstance(metadata, MetadataValues):
            raise InvalidMetadataError("metadata must be a MetadataValues instance")
        _validate_metadata(metadata)
        session.edited_metadata = metadata
        self.schedule_preview_update()

    def update_metadata(self, **changes: Any) -> None:
        session = self._require_session()
        current = session.edited_metadata
        unknown = set(changes) - {
            "camera_model",
            "focal_length_mm",
            "shutter_speed",
            "aperture",
            "iso",
        }
        if unknown:
            raise InvalidMetadataError(f"unknown metadata fields: {sorted(unknown)}")
        updated = MetadataValues(
            camera_model=changes.get("camera_model", current.camera_model),
            focal_length_mm=changes.get("focal_length_mm", current.focal_length_mm),
            shutter_speed=changes.get("shutter_speed", current.shutter_speed),
            aperture=changes.get("aperture", current.aperture),
            iso=changes.get("iso", current.iso),
        )
        _validate_metadata(updated)
        session.edited_metadata = updated
        self.schedule_preview_update()

    def set_frame_config(self, config: FrameConfig) -> None:
        session = self._require_session()
        if not isinstance(config, FrameConfig):
            raise ValueError("config must be a FrameConfig instance")
        session.frame_config = config
        self.schedule_preview_update()

    def set_output_directory(self, directory: Path) -> Path:
        directory = Path(directory)
        if not directory.is_dir():
            raise OutputNotWritableError(f"output directory does not exist: {directory}")
        self.output_directory = directory
        return directory

    def set_output_format(self, output_format: str) -> str:
        try:
            normalized = normalize_output_format(output_format)
        except (TypeError, ValueError) as exc:
            raise ValueError(str(exc)) from exc
        self.output_format = normalized
        return normalized

    def render_preview(self, max_size: tuple[int, int] | int = (1200, 900)) -> np.ndarray:
        session = self._require_session()
        self.preview = self.image_service.render_preview(session, max_size)
        self._preview_pending = False
        return self.preview

    def schedule_preview_update(self) -> bool:
        if self.session is None:
            return False
        if self._preview_pending:
            return False
        self._preview_pending = True
        return True

    def export(self) -> Path:
        session = self._require_session()
        _validate_metadata(session.edited_metadata)
        _validate_frame_config(session.frame_config)
        output_directory = self.output_directory or session.source_path.parent
        if not output_directory.is_dir():
            raise OutputNotWritableError(f"output directory does not exist: {output_directory}")
        if not _directory_is_writable(output_directory):
            raise OutputNotWritableError(f"output directory is not writable: {output_directory}")
        rendered = self.image_service.render_export(session)
        destination = unique_output_path(
            session.source_path,
            output_directory,
            self.output_format,
        )
        try:
            return self.exporter.export(
                rendered,
                destination,
                session.icc_profile,
                session.frame_config,
            )
        except ImgFrameError:
            raise
        except Exception as exc:
            raise ExportError(f"unable to export image: {destination}") from exc

    def _require_session(self) -> ImageSession:
        if self.session is None:
            raise NoSessionError("no image session is open")
        return self.session


def _directory_is_writable(directory: Path) -> bool:
    probe: Path | None = None
    try:
        descriptor, probe_name = tempfile.mkstemp(
            prefix=".img-frame-write-test-",
            dir=directory,
        )
        probe = Path(probe_name)
        import os

        os.close(descriptor)
        return True
    except (OSError, PermissionError):
        return False
    finally:
        if probe is not None:
            try:
                probe.unlink(missing_ok=True)
            except OSError:
                pass


def _validate_frame_config(config: FrameConfig) -> None:
    try:
        FrameConfig(
            material=config.material,
            color=config.color,
            opacity=config.opacity,
            border_ratio=config.border_ratio,
            font_ratio=config.font_ratio,
            blur_ratio=config.blur_ratio,
        )
    except (AttributeError, TypeError, ValueError) as exc:
        raise InvalidMetadataError(f"invalid frame configuration: {exc}") from exc


def _validate_metadata(metadata: MetadataValues) -> None:
    if metadata.focal_length_mm is not None:
        try:
            if metadata.focal_length_mm <= 0:
                raise ValueError("focal length must be positive")
        except TypeError as exc:
            raise InvalidMetadataError("focal length must be numeric") from exc
    if metadata.iso is not None:
        if isinstance(metadata.iso, bool) or not isinstance(metadata.iso, int) or metadata.iso <= 0:
            raise InvalidMetadataError("ISO must be a positive integer")
    for field_name in ("camera_model", "shutter_speed", "aperture"):
        value = getattr(metadata, field_name)
        if value is not None and not isinstance(value, str):
            raise InvalidMetadataError(f"{field_name} must be text")
