import asyncio
import hashlib
import re
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path


SCREENSHOT_INTERVAL = 5    # seconds between chart captures
FLUSH_INTERVAL      = 60   # seconds between batch disk-copy passes
_BATCH_SIZE         = 50   # max frames moved to disk per single flush pass

UPLOADS_DIR = Path("workspace/uploads")   # server-side landing zone for webm parts
FINALS_DIR  = Path("workspace/captures")  # merged session output destination

_SAFE_ID_RE = re.compile(r"[^A-Za-z0-9_\-]")


class FrameSpoolBuffer:
    """
    Memory-bounded frame spool that tracks on-disk temp-dir paths rather than
    buffering raw PNG bytes in heap memory.

    Frames produced by ffmpeg inside a TemporaryDirectory live entirely on disk;
    only their Path references are queued here.  During each flush pass, files
    are copied to the target captures directory in groups of _BATCH_SIZE,
    capping per-flush I/O bursts when multiple sessions run concurrently.

    Contract: flush() MUST be called before the originating TemporaryDirectory
    context closes.  Once the temp-dir is deleted, queued paths become invalid.
    """

    def __init__(self, captures_dir: Path, flush_interval: int = FLUSH_INTERVAL):
        self._captures_dir  = captures_dir
        self._flush_interval = flush_interval
        self._pending: list[Path] = []
        self._lock       = threading.Lock()
        self._last_flush = time.monotonic()

    def enqueue(self, src_path: Path) -> None:
        """Register a temp-dir frame path; auto-flush if the interval has elapsed."""
        with self._lock:
            self._pending.append(src_path)
            if time.monotonic() - self._last_flush >= self._flush_interval:
                self._flush_locked()

    def flush(self) -> None:
        """Force-flush all remaining pending paths to the captures directory."""
        with self._lock:
            self._flush_locked()

    def _flush_locked(self) -> None:
        """
        Copy all pending frames to captures_dir in batches of _BATCH_SIZE.
        Caller must hold self._lock.
        """
        if not self._pending:
            return
        self._captures_dir.mkdir(parents=True, exist_ok=True)
        for i in range(0, len(self._pending), _BATCH_SIZE):
            for src in self._pending[i : i + _BATCH_SIZE]:
                shutil.copy2(src, self._captures_dir / src.name)
        self._pending.clear()
        self._last_flush = time.monotonic()


def _safe_id(value: str) -> str:
    """Strip path-traversal sequences; keep only alphanumeric, hyphens, underscores."""
    return _SAFE_ID_RE.sub("", value).strip("-_") or "unnamed"


def _frame_hash(path: Path) -> str:
    """MD5 digest of raw PNG bytes — cheap static-frame identity check."""
    return hashlib.md5(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Internal async ffmpeg runner
# ---------------------------------------------------------------------------

async def _run_ffmpeg(*args: str, context: str = "ffmpeg") -> None:
    """
    Execute an ffmpeg command via asyncio.create_subprocess_exec.

    stdout and stderr are both routed to asyncio.subprocess.PIPE so the
    event loop is never blocked waiting on process I/O.  stderr content is
    captured and surfaced inside the RuntimeError message on failure.
    """
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr_bytes = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(
            f"{context} failed (exit {proc.returncode}):\n"
            f"{stderr_bytes.decode(errors='replace')}"
        )


# ---------------------------------------------------------------------------
# Public async pipeline functions
# ---------------------------------------------------------------------------

async def extract_audio(video_path: str, output_dir: str) -> Path:
    """
    Extract compressed mono 16 kHz MP3 from a video file using ffmpeg (async).

    CBR 32 kbps yields ~14 MB/hr — suitable for 5–12 hr sessions without
    saturating local storage.  The video stream is stripped immediately so
    only the audio payload reaches disk.
    """
    video = Path(video_path)
    out   = Path(output_dir) / f"{video.stem}_audio.mp3"
    await _run_ffmpeg(
        "-y", "-i", str(video),
        "-vn",                  # strip video stream
        "-ac", "1",             # mono
        "-ar", "16000",         # 16 kHz
        "-c:a", "libmp3lame",   # MP3 encoder
        "-b:a", "32k",          # 32 kbps CBR
        str(out),
        context="ffmpeg audio extraction",
    )
    return out


async def capture_screenshots(video_path: str, output_dir: str) -> list[Path]:
    """Save one PNG frame every SCREENSHOT_INTERVAL seconds (direct disk write, async)."""
    video   = Path(video_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pattern = str(out_dir / f"{video.stem}_frame_%04d.png")
    await _run_ffmpeg(
        "-y", "-i", str(video),
        "-vf", f"fps=1/{SCREENSHOT_INTERVAL}",
        pattern,
        context="ffmpeg screenshot capture",
    )
    return sorted(out_dir.glob(f"{video.stem}_frame_*.png"))


async def process_session(video_path: str, captures_dir: str) -> dict:
    """
    Run the full split pipeline for a single trading session video.

    Memory model
    ────────────
    ffmpeg writes all frame PNGs into a private TemporaryDirectory on disk —
    no per-frame heap allocation.  A FrameSpoolBuffer holds only Path
    references and batch-copies them to workspace/captures/ in groups of
    _BATCH_SIZE every FLUSH_INTERVAL seconds, capping concurrent-session
    I/O bursts without exhausting host RAM.

    Lifecycle guarantee
    ───────────────────
    spool.flush() is called while the TemporaryDirectory context is still
    open, ensuring all source paths are accessible during the copy pass.
    The temp directory — and all ffmpeg output inside it — is deleted
    automatically when the 'with' block exits after the flush completes.
    """
    out_dir = Path(captures_dir)
    audio   = await extract_audio(video_path, captures_dir)
    spool   = FrameSpoolBuffer(out_dir)
    video   = Path(video_path)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        pattern  = str(tmp_path / f"{video.stem}_frame_%04d.png")

        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y",
            "-i", str(video),
            "-vf", f"fps=1/{SCREENSHOT_INTERVAL}",
            pattern,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr_bytes = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(
                f"ffmpeg screenshot capture failed (exit {proc.returncode}):\n"
                f"{stderr_bytes.decode(errors='replace')}"
            )

        frame_names: list[str] = []
        prev_hash = None
        for frame_path in sorted(tmp_path.glob(f"{video.stem}_frame_*.png")):
            h = _frame_hash(frame_path)
            if h == prev_hash:
                continue            # static frame — chart idle, no new data
            prev_hash = h
            spool.enqueue(frame_path)
            frame_names.append(frame_path.name)

        # Flush inside the context — temp sources must still exist for copy.
        spool.flush()

    # TemporaryDirectory deleted here; all unique frames are in captures_dir.

    # Purge source video now that audio and screenshots are committed.
    # Keeps the captures directory lean across long multi-part sessions.
    Path(video_path).unlink(missing_ok=True)

    return {
        "audio":  str(audio),
        "frames": [str(out_dir / name) for name in frame_names],
    }


async def finalize_session_output(user_id: str, session_id: str) -> Path:
    """
    Losslessly concatenate all 15-minute webm parts for a completed session
    into one continuous output file using ffmpeg -c copy (no re-encoding).

    Lifecycle
    ─────────
    1. Glob workspace/uploads/{user_id}/{session_id}/ for part_*.webm files,
       sorted lexicographically — part_01… < part_02… preserves recording order.
    2. Write a temporary ffmpeg concat list using absolute paths (-safe 0).
    3. Run: ffmpeg -f concat -safe 0 -i list.txt -c copy output.webm
       Copy-mux only: zero re-encoding, no thread blocking, instant join.
    4. Delete the concat list; source parts are left intact for audit.

    Returns the Path to the merged file written to workspace/captures/.
    Raises FileNotFoundError if no parts exist for the session.
    Raises RuntimeError (from _run_ffmpeg) on any ffmpeg failure.
    """
    safe_user    = _safe_id(user_id)
    safe_session = _safe_id(session_id)

    parts_dir = UPLOADS_DIR / safe_user / safe_session
    parts     = sorted(parts_dir.glob("part_*.webm"))
    if not parts:
        raise FileNotFoundError(
            f"No webm parts found for session '{session_id}' under '{parts_dir}'."
        )

    FINALS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = FINALS_DIR / f"{safe_user}_{safe_session}_final.webm"

    # Concat list lives beside the parts so all paths share the same filesystem.
    concat_list = parts_dir / f"{safe_session}_concat.txt"
    concat_list.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in parts) + "\n"
    )

    try:
        await _run_ffmpeg(
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy",
            str(output_path),
            context=f"ffmpeg concat [{len(parts)} parts → {output_path.name}]",
        )
    finally:
        concat_list.unlink(missing_ok=True)

    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: splitter.py <video_path> <captures_dir>")
        sys.exit(1)
    result = asyncio.run(process_session(sys.argv[1], sys.argv[2]))
    print(result)
