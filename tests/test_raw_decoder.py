from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import rawpy

from app.core.errors import RawDecodeError, UnsupportedFormatError
from app.core.image_loader import ImageLoader
from app.core.raw_decoder import RawDecoder


def test_decodes_with_camera_white_balance_without_auto_brightening(tmp_path):
    raw_path = tmp_path / "sample.nef"
    raw_path.write_bytes(b"raw")

    with patch("rawpy.imread") as imread:
        raw = imread.return_value
        raw.postprocess.return_value = np.zeros((4, 6, 3), dtype=np.uint16)

        result = RawDecoder().decode(raw_path)

    imread.assert_called_once_with(raw_path)
    raw.postprocess.assert_called_once_with(
        use_camera_wb=True,
        no_auto_bright=True,
        output_bps=16,
        output_color=rawpy.ColorSpace.sRGB,
    )
    raw.close.assert_called_once()
    assert result.pixels.dtype == np.uint16
    assert result.pixels.shape == (4, 6, 3)
    assert result.mode == "RGB"
    assert result.icc_profile


def test_raw_decode_errors_are_wrapped(tmp_path):
    raw_path = tmp_path / "sample.arw"
    raw_path.write_bytes(b"not-raw")

    with patch("rawpy.imread", side_effect=RuntimeError("bad raw")):
        with pytest.raises(RawDecodeError):
            RawDecoder().decode(raw_path)


def test_image_loader_rejects_raw_extensions(tmp_path):
    raw_path = tmp_path / "sample.cr3"
    raw_path.write_bytes(b"raw")

    with patch("app.core.raw_decoder.RawDecoder.decode", return_value=object()) as decode:
        with pytest.raises(UnsupportedFormatError):
            ImageLoader().load(raw_path)

    decode.assert_not_called()
