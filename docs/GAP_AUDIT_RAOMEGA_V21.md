# AstraCore OS (R.A. Omega) v2.1 — Spec vs Code Gap Audit

Date: 2026-05-25
Branch: `elias/p0-api-spine`
Head: `ea125fd`

## 1) What was audited
- Master spec provided by R.A. (v2.1 production-locked)
- Backend modules: `app/core/*`, `app/media_processing/*`, `app/server/*`, `app/billing/*`
- Frontend cockpit: `web/gemini-code-1779662675087.html`
- Runtime and ops hardening work already shipped in P0/P1

---

## 2) Spec vs Code Matrix

### Implemented
1. File-based ledger architecture (no DB)  
   - `app/core/ledger.py`
2. Async org mutex locking by org_id  
   - `_org_ledger_locks`, `_get_org_lock`, async write/register/consume in `ledger.py`
3. Atomic write pattern (`.tmp` + `os.replace`) for critical ledger writes  
   - `write_ledger`, `_write_org_ledger_raw` in `ledger.py`
4. 15-minute chunk recording client behavior  
   - `mediaRecorder.start(900_000)` in web file
5. Codec negotiation + bitrate ceiling in frontend  
   - vp9→h264 fallback + `videoBitsPerSecond: 1_200_000`
6. Capture leak prevention with active track registry  
   - `window.activeCaptureTracks` tracking + stop/drain logic
7. Frame extraction + high-change filtering (hash-based)  
   - `process_session` in `splitter.py` (MD5 dedupe of consecutive frames)
8. Audio extraction profile (mono 16k MP3 @ 32k)  
   - `extract_audio` in `splitter.py`
9. Lossless concat on stop-commit  
   - `finalize_session_output` uses `ffmpeg -f concat -c copy`
10. Timeline binding + drift ceiling enforcement function  
   - `bind_frame_to_transcript`, `verify_timeline_alignment` in `checksum.py`
11. Ops baseline hardening  
   - preflight, observability, metrics, rotating logs, ops auth/rate limit
12. Plan/seat/session enforcement baseline in API  
   - `app/billing/*`, `routes_sessions.py`

### Partial
1. Disk lifecycle isolation and fault containment  
   - Present in some paths (`try/except` in stop-commit, fault logs in interceptor), but not consistently applied across all write/mutation routines.
2. Atomic writes are inconsistent  
   - Ledger writes are atomic, but seat logs/fault logs use direct `write_text` append style in several places.
3. Timeline integrity wiring is not end-to-end  
   - `verify_timeline_alignment()` exists, but stop-commit path does not currently call it on assembled event rows before final persistence.
4. Multi-seat async upload orchestration  
   - `BatchUploadInterceptor` exists in `upload_handler.py`, but not wired into FastAPI upload route (`/api/upload/part`).
5. Frontend failure lockdown behavior  
   - LED fail glow and warnings exist; strict locking of Pine/MT5/Jarvis controls on backend fault states is not fully enforced end-to-end.
6. Org-scoped async commit serialization in session routes  
   - Some enforcement exists in billing and ledgers, but stop-commit processing path itself is not wrapped in explicit org-level lock guard.

### Missing
1. True non-buffered upload streaming path in API ingest  
   - Current `/api/upload/part` does `data = await file.read()` then `write_bytes`, which can spike RAM for large chunks.
2. Explicit org/user context sync hooks for Hermes routing layer  
   - No implemented `--sync_ledger_context` equivalent control path in app runtime.
3. Deterministic agentic multi-loop orchestration layer (Brain L1/L2/L3 runtime scheduler)  
   - Components exist (transcription/OCR/tags/summary), but no explicit orchestrator state machine for multi-loop execution and retries.
4. Test coverage suite (unit/integration)  
   - No test files detected.
5. Production dependency depth for AI pipelines  
   - `requirements.txt` currently minimal (FastAPI/Uvicorn/multipart only), while intel/media pathways imply broader runtime requirements.
6. Commercial tier copy and enforcement cohesion  
   - Pricing/tier model appears in spec/UI narrative, but API-side billing rules are still placeholder caps rather than locked business-config policy.

---

## 3) Top Risks

### Critical
1. Upload RAM pressure risk  
   `/api/upload/part` reads full file in memory before write.
2. Integrity guard not enforced in final commit path  
   Timeline drift checker exists but not gate-kept in stop-commit flow.
3. Missing tests for core ingestion/commit/integrity path  
   High regression risk as more agents edit concurrently.

### High
1. Inconsistent atomic writes outside primary ledgers (seat/fault logs).  
2. Async upload interceptor not integrated into real API route.  
3. Placeholder billing limits could drift from final tier economics.

### Medium
1. Docs/spec wording ahead of implementation for some Hermes orchestration claims.  
2. Dependency manifest too thin for portable deployment reliability.

---

## 4) 14-Day Lean Execution Plan

### Days 1–3 (Stability First)
- Replace memory-heavy upload write with streamed chunk-to-disk writer.
- Wire `verify_timeline_alignment()` into stop-commit gate before summary persistence.
- Convert seat/fault log writes to atomic tmp+replace helpers.

### Days 4–6 (Pipeline Control)
- Integrate `BatchUploadInterceptor` in ingest/session orchestration path.
- Add org-scoped lock wrapper around stop-commit critical section.
- Add structured retry policy for recoverable ffmpeg/transcription failures.

### Days 7–10 (Verification Layer)
- Add tests:
  - ingestion part upload
  - stop-commit happy path
  - drift violation path
  - plan/seat/rate-limit guardrails
- Add smoke script for local pre-deploy validation.

### Days 11–14 (Commercial & Ops Fit)
- Lock final tier policy constants + env-backed config map.
- Expand runbook (`README` + ops troubleshooting + failure playbook).
- Produce release checklist for Phase-1 alpha cohort.

---

## 5) Agent Wiring Plan (execution discipline)

- Elias (orchestrator): owns sequencing, merge gates, release criteria.
- Diego (implementation systems): upload streaming, atomic write consistency, lock boundaries.
- Nolan (reliability): tests, smoke scripts, failure-path assertions.
- Mateo (research/policy): pricing/tier constants finalization + economics alignment.
- Mira/Sofía (external language/copy): UI+docs wording sync once engineering truth is locked.

Hard guardrails:
- No agent edits outside assigned lane.
- Every lane must include validation command + evidence.
- Merge only if compile + smoke + targeted tests pass.

---

## 6) First Implementation Slice (P0 next concrete tasks)

1. `app/server/routes_ingest.py`
   - Replace full-buffer read with streamed write loop to disk.
2. `app/server/routes_sessions.py`
   - Add timeline alignment verification gate before `save_summary()`.
3. `app/core/ledger.py` + `app/core/upload_handler.py`
   - Normalize seat/fault log writes to atomic helper.
4. Add tests in `tests/`:
   - `test_upload_part_streaming.py`
   - `test_timeline_drift_guard.py`
   - `test_stop_commit_integrity_gate.py`

Validation command baseline:
- `python -m compileall app`
- `pytest -q`

Checkpoint commits:
- `P1-2a streamed upload writer`
- `P1-2b timeline integrity gate`
- `P1-2c atomic seat/fault log writes`
- `P1-2d ingestion+integrity tests`
