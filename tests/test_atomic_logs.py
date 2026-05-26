import json
from pathlib import Path

from app.core import ledger
from app.core.upload_handler import _log_processing_error


def test_seat_and_fault_logs_write_without_tmp_leaks(tmp_path, monkeypatch):
    seats_dir = tmp_path / "seats"
    seats_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(ledger, "SEATS_DIR", seats_dir)
    monkeypatch.setattr("app.core.upload_handler.SEATS_DIR", seats_dir)

    ledger.append_seat_session_row("OP1", {"session_by": "OP1", "status": "ready"})
    ledger.append_seat_session_row("OP1", {"session_by": "OP1", "status": "ready-2"})

    _log_processing_error({"session_by": "OP1", "asset": "a.webm", "error": "boom"}, "trace")

    seat_log = json.loads((seats_dir / "OP1_log.json").read_text())
    assert len(seat_log["session_rows"]) == 2

    fault_log = json.loads((seats_dir / "usr_floor_OP1_log.json").read_text())
    assert len(fault_log["fault_rows"]) == 1

    tmp_files = list(seats_dir.glob("*.tmp"))
    assert tmp_files == []
