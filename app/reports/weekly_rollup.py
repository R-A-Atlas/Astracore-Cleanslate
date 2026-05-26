from collections import Counter


def build_weekly_rollup(summaries: list[dict]) -> dict:
    tag_counter = Counter()
    for s in summaries:
        for t in s.get("behavior", {}).get("tags", []):
            tag_counter[t.get("tag", "unknown")] += 1

    return {
        "sessions": len(summaries),
        "top_behavior_tags": tag_counter.most_common(5),
    }
