from pathlib import Path


def extract_frame_events(frame_paths: list[str]) -> list[dict]:
    """
    P0 scaffold: derive frame event rows from saved high-change frames.
    Replace with OCR/pattern interpretation in P1.
    """
    rows: list[dict] = []
    for i, fp in enumerate(frame_paths):
        name = Path(fp).name
        rows.append(
            {
                "index": i,
                "frame": name,
                "event": "visual-change-detected",
            }
        )
    return rows
