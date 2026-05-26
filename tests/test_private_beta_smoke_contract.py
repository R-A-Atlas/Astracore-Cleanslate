import os
import subprocess


def test_private_beta_smoke_success_contract():
    result = subprocess.run(
        ["bash", "scripts/private_beta_smoke.sh"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    stdout = result.stdout
    assert "[PASS] signup" in stdout
    assert "[PASS] login" in stdout
    assert "[PASS] google_start" in stdout
    assert "[PASS] google_callback" in stdout
    assert "[PASS] dashboard_summary" in stdout
    assert "[PASS] settings_save" in stdout
    assert "[PASS] settings_load" in stdout
    assert "[PASS] billing_enforcement" in stdout
    assert "SMOKE_OK private beta gate" in stdout


def test_private_beta_smoke_fail_exit_contract():
    env = os.environ.copy()
    env["PRIVATE_BETA_SMOKE_FORCE_FAIL_STEP"] = "login"
    result = subprocess.run(
        ["bash", "scripts/private_beta_smoke.sh"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "[FAIL] login :: forced failure" in result.stdout
    assert "SMOKE_OK private beta gate" not in result.stdout
