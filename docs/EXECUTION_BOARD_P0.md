# AstraCore Cleanslate — Execution Board P0

Owner: Elias
Approval: R.A.
Status: Active

## Goal
Turn the existing framework into a functioning product loop:
Capture -> Process -> Analyze -> Report -> Enforce Plan -> Operate

---

## P0-1 API Spine (Critical)
### Tasks
- [ ] Create `app/server/main.py`
- [ ] Add route modules:
  - [ ] `app/server/routes_ingest.py`
  - [ ] `app/server/routes_sessions.py`
  - [ ] `app/server/routes_ops.py`
  - [ ] `app/server/schemas.py`
- [ ] Implement endpoints:
  - [ ] `GET /health`
  - [ ] `POST /api/session/start`
  - [ ] `POST /api/upload/part`
  - [ ] `POST /api/session/stop-commit`
  - [ ] `GET /api/session/{session_id}/status`

### Acceptance
- Frontend upload path receives real API responses.
- Session status can be polled from UI.

---

## P0-2 Session Finalization Wiring (Critical)
### Tasks
- [ ] Wire stop/commit endpoint to `finalize_session_output()`
- [ ] Run `process_session()` after successful concat
- [ ] Save artifacts path references in session metadata

### Acceptance
- One full session creates merged video + audio + filtered frame outputs.

---

## P0-3 Intelligence Pipeline v1 (Critical)
### Tasks
- [ ] Add `app/intel/transcription.py`
- [ ] Add `app/intel/frame_ocr.py`
- [ ] Add `app/intel/event_extractor.py`
- [ ] Add `app/intel/behavior_tags.py`
- [ ] Add `app/intel/session_summary.py`

### Acceptance
- Completed session yields structured summary JSON with behavior tags.

---

## P0-4 Product Output v1 (Critical)
### Tasks
- [ ] Add `app/reports/daily_review.py`
- [ ] Add `app/reports/weekly_rollup.py`
- [ ] Add report templates under `app/reports/templates/`

### Acceptance
- User can open plain-language Daily Review after session completion.

---

## P0-5 Plan/Tier Enforcement (Critical)
### Tasks
- [ ] Add `app/billing/plan_policy.py`
- [ ] Add `app/billing/usage_enforcement.py`
- [ ] Enforce seat/session limits in session-start and stop-commit flows

### Acceptance
- Quota exhaustion is enforced by API with clear user-safe message.

---

## P0-6 Runtime Baseline (Critical)
### Tasks
- [ ] Add dependency manifest (`requirements.txt` or `pyproject.toml`)
- [ ] Add startup checks (workspace dirs + ffmpeg availability)
- [ ] Add minimal README run instructions

### Acceptance
- New environment can run app with documented steps.

---

## P0-7 Basic Validation Harness (Critical)
### Tasks
- [ ] Add tests:
  - [ ] timeline alignment
  - [ ] ledger atomic write behavior
  - [ ] upload/session finalize happy path
  - [ ] plan enforcement

### Acceptance
- Core safety paths pass test run before any release.

---

## Owners by Track
- API spine/finalization: Elias + Diego
- Intelligence pipeline: Elias (architecture), future analysis specialists later
- Output/report clarity: Sofía + Mira
- Plan logic: Nolan
- Research feedback loop: Mateo

---

## Freeze Rules
- No second-layer chat-agent expansion until P0-1 through P0-5 are complete.
- No live-trading activation paths during P0.
- No uncontrolled model output directly written to critical ledgers.

---

## Next Milestone Trigger
When P0-1 through P0-3 pass acceptance, we start naming + design for the trader-facing assistant layer (currently called Jarvis, rename pending).
