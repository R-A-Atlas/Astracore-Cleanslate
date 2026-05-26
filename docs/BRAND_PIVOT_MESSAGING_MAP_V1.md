# BRAND_PIVOT_MESSAGING_MAP_V1

Date: 2026-05-25  
Owner: Mira (Brand + Messaging)  
Execution alignment: Elias  
Final approval: R.A.

## 1) Pivot-safe positioning statement (current-state only)
AstraCore is building a reliability-first operating layer for trading session capture and review workflows, with current delivery focused on stable ingest/commit foundations (atomic ledger writes, org-scoped lock patterns, chunked recording behavior, and timeline integrity components) before broader automation claims.

Short variant:
Reliability-first session infrastructure before growth claims.

## 2) Homepage hero variants (3)

### Hero Variant A — Reliability-first
Headline:
Build on session reliability, not guesswork.

Subheadline:
AstraCore is shipping the core ingest and commit foundation first: atomic ledger writes, safer capture handling, and timeline integrity controls.

Support line:
Current phase focuses on backend truth and operational stability.

### Hero Variant B — Practical execution
Headline:
From fragile workflows to controlled session infrastructure.

Subheadline:
We are moving from audit-only work into product execution, prioritizing memory-safe ingest paths, commit integrity gates, and org-level control patterns.

Support line:
No inflated claims — only what is implemented and verified.

### Hero Variant C — Trust + cadence
Headline:
Shipping reliability in phases.

Subheadline:
AstraCore’s current milestones center on ingestion resilience, atomic mutation discipline, and measurable commit-path safeguards.

Support line:
Each release message maps to code-level implementation status.

## 3) Trust-proof bullets (implemented functionality only)
1. Atomic ledger write pattern is implemented using temp-file + replace flow in core ledger paths.
2. Org-based async lock primitives exist for ledger mutation control.
3. Frontend records in 15-minute chunks (mediaRecorder start at 900,000 ms).
4. Frontend includes codec negotiation fallback and bitrate ceiling configuration.
5. Media pipeline already includes frame extraction + consecutive-frame hash dedupe, plus stop-commit lossless concat workflow.

## 4) CTA variants — Retail traders (3)
1. Track the reliability roadmap
   - See what is shipped now and what is next.
2. Review current implementation status
   - Check phase-by-phase progress before joining alpha.
3. Join the waitlist for verified releases
   - Get updates only when functionality is implemented.

## 5) CTA variants — Prop / team managers (3)
1. Evaluate current reliability controls
   - Review implemented ingest and commit safeguards.
2. Request phase-status brief
   - Get the current shipped-vs-planned breakdown for team review.
3. Join alpha updates for ops leads
   - Receive milestone notes tied to verified implementation.

## 6) Website messaging optimization notes (immediate)
1. Replace any broad “AI orchestration is fully deployed” language with “core reliability layers are being shipped in phases.”
2. Add a visible status block on homepage:
   - Implemented
   - Partial
   - In progress
   - Not shipped yet
3. Keep technical trust language plain:
   - “atomic writes,” “org lock discipline,” “timeline alignment checks,” “streaming ingest work in progress.”
4. Separate audience pathways:
   - Retail: clarity + discipline + replay reliability
   - Team/prop: control, consistency, and multi-seat commit safeguards

## 7) Claim verification
Source files reviewed:
- /root/AstraCore/Astracore-Cleanslate/docs/GAP_AUDIT_RAOMEGA_V21.md
- /root/AstraCore/Astracore-Cleanslate/docs/HERMES_AGENT_UPGRADE_PLAN_RAOMEGA_V21.md

Claim mapping:
- Atomic ledger writes: GAP_AUDIT section “Implemented” items 1 and 3.
- Org lock primitives: GAP_AUDIT “Implemented” item 2.
- 15-minute chunk recording: GAP_AUDIT “Implemented” item 4.
- Codec fallback + bitrate ceiling: GAP_AUDIT “Implemented” item 5.
- Frame extraction/hash dedupe + lossless concat: GAP_AUDIT “Implemented” items 7 and 9.

Guardrail:
Any missing/partial items (streamed upload path, end-to-end timeline gate enforcement, full interceptor wiring, complete test coverage) are intentionally not presented as shipped benefits in public messaging.
