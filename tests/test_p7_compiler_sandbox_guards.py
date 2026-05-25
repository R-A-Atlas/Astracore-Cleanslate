from pathlib import Path

import pytest

import app.core.compiler_sandbox as sandbox


def test_pine_rejects_oversized_script(monkeypatch, tmp_path):
    monkeypatch.setattr(sandbox, "ERROR_LOG", tmp_path / "error.log")
    oversized = "a" * (sandbox.MAX_SCRIPT_CHARS + 1)

    with pytest.raises(SystemExit):
        sandbox.validate_pine_v6(oversized, output_path="/tmp/x.pine")

    log_text = (tmp_path / "error.log").read_text()
    assert "PINE_SCRIPT_TOO_LARGE" in log_text


def test_mql5_rejects_too_many_lines(monkeypatch, tmp_path):
    monkeypatch.setattr(sandbox, "ERROR_LOG", tmp_path / "error.log")
    too_many_lines = "\n".join(["line"] * (sandbox.MAX_SCRIPT_LINES + 1))

    with pytest.raises(SystemExit):
        sandbox.validate_mql5(too_many_lines, output_path="/tmp/x.mq5")

    log_text = (tmp_path / "error.log").read_text()
    assert "MQL5_SCRIPT_TOO_MANY_LINES" in log_text


def test_pine_allows_small_valid_script(monkeypatch, tmp_path):
    monkeypatch.setattr(sandbox, "ERROR_LOG", tmp_path / "error.log")
    valid = """//@version=6
indicator(\"x\")
plot(close)
"""

    sandbox.validate_pine_v6(valid, output_path="/tmp/ok.pine")
    assert not Path(tmp_path / "error.log").exists()
