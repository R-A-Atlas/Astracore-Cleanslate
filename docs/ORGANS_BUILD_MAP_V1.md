# AstraCore Cleanslate — Organs Build Map v1

Owner: R.A. (Boss)
Operator: Elias Vega
Status: Approved to execute

## 1) Objective
Turn the current body (UI shell + ingest pipeline + ledgers) into a working product that delivers real trader value:
- session intelligence
- behavior coaching outputs
- usable daily/weekly reports
- tiered product controls
- operator visibility and control

---

## 2) What Exists (Body)
- File-based ledgers + atomic writes
- Async media processing pipeline (chunking, frame extraction, audio extraction, concat)
- Timeline drift verification primitives
- Frontend shell and cockpit UX baseline

## 3) Missing Organs (Now Required)

### Organ A — API Spine (P0)
Create executable backend service wiring frontend to pipeline.

**Add files**
- `app/server/main.py`
- `app/server/routes_ingest.py`
- `app/server/routes_sessions.py`
- `app/server/routes_ops.py`
- `app/server/schemas.py`

**Core endpoints**
- `GET /health`
- `POST /api/upload/part`
- `POST /api/session/start`
- `POST /api/session/stop-commit`
- `GET /api/session/{session_id}/status`
- `GET /ops/status`
- `GET /ops/recent-errors`

**Definition of done**
- Frontend upload call returns real status payload.
- Session stop triggers concat + processing pipeline.

---

### Organ B — Intelligence Pipeline v1 (P0)
Convert media into actionable structured artifacts.

**Add files**
- `app/intel/transcription.py`
- `app/intel/frame_ocr.py`
- `app/intel/event_extractor.py`
- `app/intel/behavior_tags.py`
- `app/intel/session_summary.py`

**Outputs**
- transcript segments with timestamps
- frame event rows (high-change moments)
- behavior tags (rule break, hesitation, revenge risk, overtrade risk)
- session summary JSON

**Definition of done**
- One completed session generates machine-readable summary artifacts.

---

### Organ C — Product Output Layer (P0)
Generate sellable user-facing outputs.

**Add files**
- `app/reports/daily_review.py`
- `app/reports/weekly_rollup.py`
- `app/reports/templates/*.md`

**Outputs**
- Daily Review Card:
  - what happened
  - what cost performance
  - top 3 behavior fixes next session
- Weekly Performance Brief:
  - pattern frequency
  - consistency score trend
  - coaching focus

**Definition of done**
- End user can open plain-language report after each session.

---

### Organ D — Plan/Tier Enforcement (P0)
Wire business model into runtime behavior.

**Add files**
- `app/billing/plan_policy.py`
- `app/billing/usage_enforcement.py`

**Rules (initial)**
- Tier 1 retail limits
- Tier 2 org seat + session allocation logic
- graceful reject when quota exhausted

**Definition of done**
- Limits are actually enforced by API, not just documented.

---

### Organ E — Security & Multi-Tenant Boundaries (P1)
Prevent cross-tenant leakage and unsafe execution.

**Add files**
- `app/security/auth.py`
- `app/security/tokens.py`
- `app/security/tenant_guard.py`

**Controls**
- internal API token auth
- org/operator binding checks on every route
- input size/type validation

**Definition of done**
- Requests cannot read/write outside their org/operator scope.

---

### Organ F — Ops/Telemetry Layer (P1)
Operator visibility for Telegram updates and recovery.

**Add files**
- `app/ops/metrics.py`
- `app/ops/error_registry.py`
- `app/ops/alerts.py`

**Metrics**
- queue depth
- process time
- failure counts by stage
- ffmpeg failure rate

**Definition of done**
- Elias can send clear status reports from real telemetry.

---

### Organ G — QA & Reliability Harness (P1)
Stop regressions while velocity increases.

**Add files**
- `tests/test_ledger_atomicity.py`
- `tests/test_timeline_alignment.py`
- `tests/test_upload_flow.py`
- `tests/test_plan_enforcement.py`
- `requirements.txt` or `pyproject.toml`

**Definition of done**
- CI/local test run validates core safety paths before release.

---

## 4) Execution Sequence (14-Day)

### Week 1 (P0 focus)
1. API Spine
2. Intelligence Pipeline v1
3. Product Output Layer
4. Plan/Tier Enforcement

### Week 2 (P1 hardening)
5. Security boundaries
6. Ops telemetry + alerts
7. QA harness + docs + release checks

---

## 5) Agent Team Ownership Map

- **Elias**: architecture control, priorities, risk gates, delivery updates to R.A.
- **Mateo**: market/user pain intelligence feeding summary language and feature priority
- **Sofía**: report/UI readability, dashboard clarity, conversion-facing copy structure
- **Nolan**: packaging logic, seat economics, limit behavior by tier
- **Mira**: brand voice + website messaging + social marketing strategy + engagement hooks
- **Diego**: implementation systems owner (runbooks, launch QA, integration specs, reliability operations)

---

## 6) Diego Role Update (Recommended)
Current role can be expanded.

### New Diego definition
**Implementation Systems & Reliability Lead**

Owns:
- integration contracts (API + data flow handoff docs)
- environment bootstrap and runbooks
- release checklists and rollback procedures
- incident response playbooks
- launch QA orchestration
- production-readiness verification

This keeps him highly valuable even after handoff documents are done.

---

## 7) Release Gates (must pass)
- API endpoints functional end-to-end
- one full session produces report artifacts
- plan enforcement active
- org isolation checks pass
- test suite green for P0 paths
- operator status endpoint readable for Telegram update flow

---

## 8) Immediate Next Build Items (start now)
1. Stand up `app/server/main.py` with `/health`
2. Implement `POST /api/upload/part`
3. Implement `POST /api/session/stop-commit`
4. Wire to `splitter.finalize_session_output()` and `process_session()`
5. Persist session status rows for frontend polling
