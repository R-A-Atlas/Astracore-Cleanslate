from __future__ import annotations

import shutil
from pathlib import Path

REQUIRED_DIRS = [
    Path("workspace/uploads"),
    Path("workspace/captures"),
    Path("workspace/memory/sessions"),
    Path("workspace/memory/intel"),
    Path("workspace/outputs/reports/daily"),
    Path("workspace/ops"),
    Path("workspace/logs"),
]


def ensure_runtime_ready() -> dict:
    created = []
    for directory in REQUIRED_DIRS:
        if not directory.exists():
            created.append(str(directory))
        directory.mkdir(parents=True, exist_ok=True)

    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    if not ffmpeg_path or not ffprobe_path:
        raise RuntimeError(
            "Missing runtime dependency: ffmpeg/ffprobe not found in PATH. "
            "Install ffmpeg before starting the API."
        )

    return {
        "created_dirs": created,
        "ffmpeg": ffmpeg_path,
        "ffprobe": ffprobe_path,
    }
