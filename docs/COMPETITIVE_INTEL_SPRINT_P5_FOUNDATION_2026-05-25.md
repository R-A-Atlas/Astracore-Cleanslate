# AstraCore Competitive Intelligence Sprint (P5 Foundation)

## Scope
- Category: AI meeting assistants + conversation intelligence + multimodal work intelligence
- Goal: Identify crowded zones, whitespace, and a concrete P5-1 execution wedge.

## Competitor landscape (sample set)
- Fireflies.ai — https://fireflies.ai
- Otter.ai — https://otter.ai
- Fathom — https://fathom.video
- Gong — https://www.gong.io
- ZoomInfo Chorus — https://www.zoominfo.com/products/chorus
- Grain — https://grain.com
- tl;dv — https://tldv.io
- Read AI — https://www.read.ai
- Sembly AI — https://www.sembly.ai
- Avoma — https://www.avoma.com
- Supernormal — https://supernormal.com
- Krisp AI — https://krisp.ai
- Notion AI — https://www.notion.com/product/ai
- Fellow — https://fellow.app
- MeetGeek — https://meetgeek.ai
- Jamie — https://www.meetjamie.ai
- Granola — https://www.granola.so
- Bubbles — https://www.usebubbles.com
- Salesloft (Conversation Intelligence) — https://www.salesloft.com
- Jiminny — https://jiminny.com

## High-confidence market read
1. Recording + transcription is commoditized.
2. CRM/task integrations are common.
3. Enterprise players are strong in sales coaching and reporting.
4. Most products are weak on true causal timeline intelligence.
5. Most products are weak on closed-loop execution verification.

## Strategic whitespace (top 5)
1. Causal timeline intelligence across meetings + actions + outcomes.
2. Persistent org memory with role-based retrieval and provenance.
3. Multimodal work graph (screen events + voice + docs + tasks).
4. Privacy-first private deployment for regulated teams.
5. Deterministic action layer (approve, execute, verify, rollback).

## AstraCore wedges (prioritized)
1. Causal Deal/Project Navigator
2. Private Memory OS (regulated verticals)
3. Autopilot with Human Guardrails

## Recommended immediate execution choice
Choose wedge #1 first (Causal Deal/Project Navigator) because:
- Matches already-built consult timeline foundation.
- Clear measurable KPI (slipped commitments, follow-up completion, forecast confidence).
- Can ship as incremental backend slices without big infra jump.

---

## P5-1 Spec (approved-for-build draft)
### Name
P5-1 — Causal Follow-through Signals (read-only)

### Objective
Add deterministic follow-through signals to consult responses so operators can see whether decisions turned into actions and outcomes.

### API additions (read-only)
- Add optional `include_follow_through=true|false` to `GET /api/session/{session_id}/consult`
- Add response block per match when enabled:
  - `follow_through.signals[]` with:
    - `signal_type` (task_created|task_completed|status_change|owner_ack)
    - `epoch_ms`
    - `source`
    - `confidence` (0-1)
    - `evidence_snippet`
  - `follow_through.score` (0-100)

### Determinism rules
- Stable sorting by `epoch_ms asc` inside signals
- Strict bounded score computation with explicit weights in constants
- No mutation of source artifacts

### Validation contract
- New tests:
  - positive signal extraction path
  - no-signal path
  - deterministic ordering path
- Full validation:
  - `pytest -q`
  - `python -m compileall app`

### Done definition
- Endpoint returns valid follow-through block when requested.
- Existing consult behavior unchanged when param omitted.
- Tests pass and docs updated.

## Next slices after P5-1
- P5-2: Follow-through aggregation in top-level stats.
- P5-3: `min_follow_through_score` filter.
- P5-4: debug counters for follow-through gating.
