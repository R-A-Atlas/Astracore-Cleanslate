# Agent Readiness Pack v1 (Post-Audit)

## Objective
Enable safe parallel execution after gap audit without cross-lane corruption.

## Lanes
1. Lane A — Ingest Reliability (Diego)
2. Lane B — Integrity Guards & Atomicity (Diego + Nolan)
3. Lane C — Test Harness & Smoke Validation (Nolan)
4. Lane D — Tier/Policy Finalization (Mateo)
5. Lane E — UX/Comms Sync after truth-lock (Mira/Sofía)

## File Ownership
- Lane A: `app/server/routes_ingest.py`, `app/core/upload_handler.py`
- Lane B: `app/server/routes_sessions.py`, `app/core/ledger.py`, `app/core/checksum.py`
- Lane C: `tests/*`, `scripts/smoke/*`
- Lane D: `app/billing/*`, `.env.example`, `README.md` pricing/config notes
- Lane E: `web/*` and docs text only after backend locks are merged

## No-Go Rules
- No direct edits to another lane’s files without explicit reassignment.
- No merge without compile + lane-specific verification evidence.
- No placeholder claims in docs that are not code-true.

## Done Criteria (per PR/commit)
- Must include:
  - changed files list
  - validation command output
  - risk note (what could break)
- Mandatory baseline:
  - `python -m compileall app`
  - targeted test(s) for touched behavior

## Merge Sequence
1. Lane A
2. Lane B
3. Lane C
4. Lane D
5. Lane E

## Immediate Task Queue (from audit)
- A1: streamed upload write path
- B1: timeline drift gate in stop-commit
- B2: atomic seat/fault log writes
- C1: tests for A1/B1/B2
- D1: lock final policy constants to approved business values
