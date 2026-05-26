# Enzo Security + QA Control Matrix v1

## Evidence Root
`/root/AstraCore/logs/enzo_security/`

## Controls

### C-01 Prompt Injection QA Loop
- Owner: Enzo
- Scope: consult/operator-facing generation paths
- Test: targeted adversarial prompt set + output policy assertions
- Cadence: daily + before release
- Evidence:
  - `enzo_prompt_eval_<timestamp>.json`
  - `enzo_prompt_eval_summary_<date>.md`
- Pass rule: 0 critical policy leaks, 0 role exposure leaks

### C-02 File Ledger Integrity
- Owner: Enzo + Diego
- Scope: JSON state/ledger writes
- Test: static scan for mutex usage + atomic replace usage
- Cadence: per release
- Evidence:
  - `enzo_ledger_scan_<timestamp>.json`
- Pass rule: no high-risk write paths without atomic pattern

### C-03 Compiler Sandbox Wall
- Owner: Enzo + Diego
- Scope: `app/core/compiler_sandbox.py`
- Test: guardrail smoke checks + hostile input checks
- Cadence: per release
- Evidence:
  - `enzo_sandbox_scan_<timestamp>.json`
- Pass rule: all configured safety checks pass
- Current runtime thresholds: `MAX_SCRIPT_CHARS=200000`, `MAX_SCRIPT_LINES=5000`

### C-04 Regression Verification Gate
- Owner: Enzo
- Scope: backend
- Test: `pytest -q` + `python -m compileall app`
- Cadence: each phase commit
- Evidence:
  - `enzo_regression_<timestamp>.log`
- Pass rule: all tests pass, compile passes

## Severity Scale
- Critical: immediate freeze, no release
- High: block release until fixed
- Medium: fix in next phase
- Low: backlog allowed with owner/date
