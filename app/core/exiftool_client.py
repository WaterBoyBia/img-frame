from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


class ExifToolClient:
    def __init__(self, executable: str | Path = "exiftool.exe") -> None:
        self.executable = str(executable)

    @property
    def available(self) -> bool:
        path = Path(self.executable)
        return path.exists() if path.parent != Path(".") else shutil.which(self.executable) is not None

    def read_json(self, path: Path) -> list[dict[str, Any]] | None:
        try:
            result = subprocess.run(
                [self.executable, "-j", "-n", "-q", str(path)],
                check=False,
                capture_output=True,
                timeout=10,
                shell=False,
            )
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
            return None
        if result.returncode != 0:
            return None
        try:
            payload = result.stdout.decode("utf-8") if isinstance(result.stdout, bytes) else result.stdout
            data = json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
            return None
        return data if isinstance(data, list) else None
