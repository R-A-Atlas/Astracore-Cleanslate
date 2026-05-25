from datetime import datetime, timezone


def build_session_summary(
    *,
    user_id: str,
    session_id: str,
    operator_key: str,
    audio_path: str | None,
    frame_paths: list[str],
    transcript_segments: list[dict],
    event_rows: list[dict],
    behavior_tags: list[dict],
) -> dict:
    """P0 scaffold: canonical session summary payload."""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "session_id": session_id,
        "operator_key": operator_key,
        "artifacts": {
            "audio": audio_path,
            "frames": frame_paths,
            "frame_count": len(frame_paths),
        },
        "transcript": {
            "segments": transcript_segments,
            "segment_count": len(transcript_segments),
        },
        "events": {
            "rows": event_rows,
            "count": len(event_rows),
        },
        "behavior": {
            "tags": behavior_tags,
            "count": len(behavior_tags),
        },
    }
