from pathlib import Path


def transcribe_audio(audio_path: str) -> list[dict]:
    """
    P0 scaffold: return timestamped transcript segments.
    Replace with real STT provider integration in P1.
    """
    p = Path(audio_path)
    if not p.exists():
        return []

    # Placeholder deterministic segment.
    return [
        {
            "start_ms": 0,
            "end_ms": 5000,
            "text": "[P0 placeholder] transcription pending provider integration",
            "source": p.name,
        }
    ]
