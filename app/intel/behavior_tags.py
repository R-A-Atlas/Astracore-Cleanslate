def infer_behavior_tags(transcript_segments: list[dict], frame_events: list[dict]) -> list[dict]:
    """
    P0 scaffold behavior tags.
    Very simple heuristic to keep downstream interfaces stable.
    """
    tags: list[dict] = []

    if len(frame_events) > 50:
        tags.append({"tag": "high-activity-session", "severity": "medium"})

    joined = " ".join((s.get("text") or "").lower() for s in transcript_segments)
    if any(k in joined for k in ["chase", "revenge", "force", "fomo"]):
        tags.append({"tag": "discipline-risk-language", "severity": "high"})

    if not tags:
        tags.append({"tag": "insufficient-signal", "severity": "low"})

    return tags
