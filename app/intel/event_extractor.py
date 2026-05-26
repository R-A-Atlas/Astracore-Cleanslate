def _to_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def build_event_rows(transcript_segments: list[dict], frame_events: list[dict]) -> list[dict]:
    """Build normalized, monotonic timeline rows for transcript + frame events."""
    rows: list[dict] = []

    for i, s in enumerate(transcript_segments):
        start_ms = _to_int(s.get("start_ms"), 0)
        end_ms = _to_int(s.get("end_ms"), start_ms)
        if end_ms < start_ms:
            end_ms = start_ms
        rows.append(
            {
                "id": f"t_{i}",
                "type": "transcript",
                "epoch_ms": start_ms,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "text": s.get("text") or "",
                "source": s.get("source") or "transcript",
            }
        )

    max_transcript_end = max([r["end_ms"] for r in rows if r["type"] == "transcript"], default=0)
    frame_base = max_transcript_end + 1

    for i, e in enumerate(frame_events):
        idx = _to_int(e.get("index"), i)
        epoch_ms = _to_int(e.get("epoch_ms"), frame_base + (idx * 1000))
        rows.append(
            {
                "id": f"f_{i}",
                "type": "frame",
                "epoch_ms": epoch_ms,
                "index": idx,
                "frame": e.get("frame"),
                "event": e.get("event") or "visual-change-detected",
                "source": e.get("source") or "frame_ocr",
            }
        )

    rows.sort(key=lambda r: (r.get("epoch_ms", 0), 0 if r.get("type") == "transcript" else 1))
    return rows
