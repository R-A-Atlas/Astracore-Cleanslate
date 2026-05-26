from pathlib import Path


def build_daily_review(summary: dict) -> dict:
    user_id = summary.get("user_id", "unknown")
    session_id = summary.get("session_id", "unknown")
    operator_key = summary.get("operator_key", "unknown")
    generated_at = summary.get("generated_at", "")

    tags = [t.get("tag", "unknown") for t in summary.get("behavior", {}).get("tags", [])]
    tag_text = ", ".join(tags) if tags else "none"

    frame_count = summary.get("artifacts", {}).get("frame_count", 0)
    transcript_count = summary.get("transcript", {}).get("segment_count", 0)

    what_happened = (
        f"Captured {frame_count} high-change frames and {transcript_count} transcript segments."
    )
    why_it_matters = (
        "This session log creates a replayable record of execution behavior so mistakes can be corrected faster."
    )

    # P0 placeholders to keep output structure stable.
    fixes = [
        "Define one clear entry condition before session start.",
        "Set a hard stop rule and verbalize it before each trade.",
        "Log one behavioral trigger to avoid in next session.",
    ]

    markdown = (
        "# AstraCore Daily Review\n\n"
        f"- User: {user_id}\n"
        f"- Session: {session_id}\n"
        f"- Operator: {operator_key}\n"
        f"- Generated: {generated_at}\n\n"
        "## What happened\n"
        f"{what_happened}\n\n"
        "## Why it matters\n"
        f"{why_it_matters}\n\n"
        "## Top 3 fixes for next session\n"
        f"1. {fixes[0]}\n"
        f"2. {fixes[1]}\n"
        f"3. {fixes[2]}\n\n"
        "## Behavior tags\n"
        f"{tag_text}\n"
    )

    return {
        "user_id": user_id,
        "session_id": session_id,
        "operator_key": operator_key,
        "generated_at": generated_at,
        "behavior_tags": tags,
        "markdown": markdown,
    }


def save_daily_review(review: dict) -> str:
    out_dir = Path("workspace/outputs/reports/daily")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{review['user_id']}__{review['session_id']}__daily_review.md"
    path.write_text(review["markdown"])
    return str(path)
