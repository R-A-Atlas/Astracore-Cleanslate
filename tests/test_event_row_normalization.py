from app.intel.event_extractor import build_event_rows


def test_build_event_rows_normalizes_and_sorts_monotonic():
    transcript = [
        {"start_ms": 1500, "end_ms": 2200, "text": "second"},
        {"start_ms": 500, "end_ms": 1200, "text": "first"},
    ]
    frames = [
        {"index": 0, "frame": "f0.png", "event": "visual-change-detected"},
        {"index": 1, "frame": "f1.png", "event": "visual-change-detected"},
    ]

    rows = build_event_rows(transcript, frames)

    assert len(rows) == 4
    assert all("epoch_ms" in r for r in rows)
    assert all("source" in r for r in rows)

    epochs = [r["epoch_ms"] for r in rows]
    assert epochs == sorted(epochs)

    transcript_rows = [r for r in rows if r["type"] == "transcript"]
    assert transcript_rows[0]["text"] == "first"
    assert transcript_rows[1]["text"] == "second"


def test_build_event_rows_frame_epoch_fallback_after_transcript_window():
    transcript = [{"start_ms": 0, "end_ms": 1000, "text": "alpha"}]
    frames = [{"index": 0, "frame": "f0.png"}]

    rows = build_event_rows(transcript, frames)
    frame_row = [r for r in rows if r["type"] == "frame"][0]

    assert frame_row["epoch_ms"] >= 1001
