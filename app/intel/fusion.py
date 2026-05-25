from datetime import datetime, timezone


def build_query_timeline(*, user_id: str, session_id: str, transcript_segments: list[dict], frame_events: list[dict], event_rows: list[dict]) -> dict:
    """Build query-ready fused timeline artifact for consult/read APIs."""
    transcript_chunks = []
    for i, seg in enumerate(transcript_segments):
        if isinstance(seg, dict):
            start_ms = int(seg.get("start_ms") or 0)
            end_ms = int(seg.get("end_ms") or start_ms)
            text = seg.get("text") or ""
        else:
            start_ms = 0
            end_ms = 0
            text = str(seg)
        transcript_chunks.append(
            {
                "id": f"tc_{i}",
                "start_ms": start_ms,
                "end_ms": end_ms,
                "text": text,
            }
        )

    frame_chunks = []
    for i, evt in enumerate(frame_events):
        if isinstance(evt, dict):
            index = int(evt.get("index") or i)
            frame = evt.get("frame")
            event = evt.get("event") or "visual-change-detected"
            epoch_ms = int(evt.get("epoch_ms") or 0)
        else:
            index = i
            frame = None
            event = str(evt)
            epoch_ms = 0
        frame_chunks.append(
            {
                "id": f"fc_{i}",
                "index": index,
                "frame": frame,
                "event": event,
                "epoch_ms": epoch_ms,
            }
        )

    timeline = sorted(event_rows, key=lambda r: int(r.get("epoch_ms") or 0))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "session_id": session_id,
        "counts": {
            "transcript_segments": len(transcript_chunks),
            "frame_events": len(frame_chunks),
            "timeline_rows": len(timeline),
        },
        "transcript_chunks": transcript_chunks,
        "frame_chunks": frame_chunks,
        "timeline_rows": timeline,
    }
