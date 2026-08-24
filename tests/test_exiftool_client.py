from unittest.mock import patch

from app.core.exiftool_client import ExifToolClient


def test_reads_json_output_from_exiftool(tmp_path):
    image_path = tmp_path / "image.jpg"
    image_path.write_bytes(b"data")
    payload = b'[{"Model":"NIKON D750","FocalLength":"50 mm"}]'

    with patch("subprocess.run") as run:
        run.return_value.returncode = 0
        run.return_value.stdout = payload
        run.return_value.stderr = b""

        result = ExifToolClient("exiftool.exe").read_json(image_path)

    assert result[0]["Model"] == "NIKON D750"
    run.assert_called_once()


def test_unavailable_exiftool_returns_none(tmp_path):
    with patch("subprocess.run", side_effect=FileNotFoundError):
        assert ExifToolClient("missing.exe").read_json(tmp_path / "x.jpg") is None
