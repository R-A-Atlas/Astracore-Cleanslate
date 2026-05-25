def build_event_rows(transcript_segments: list[dict], frame_events: list[dict]) -> list[dict]:
    """
    P0 scaffold: merge transcript and frame events into a simple timeline.
    """
    rows: list[dict] = []

    for s in transcript_segments:
        rows.append(
            {
                "type": "transcript",
                "start_ms": s.get("start_ms"),
                "end_ms": s.get("end_ms"),
                "text": s.get("text"),
            }
        )

    for e in frame_events:
        rows.append(
            {
                "type": "frame",
                "index": e.get("index"),
                "frame": e.get("frame"),
                "event": e.get("event"),
            }
        )

    return rows
