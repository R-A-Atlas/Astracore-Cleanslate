# SOCIAL_CAMPAIGN_2WEEK_PIVOT_PLAN_V1

Date: 2026-05-25  
Owner: Mira (Social strategy + messaging)  
Execution alignment: Elias  
Final approval: R.A.

## 1) Objective
Run a 2-week pivot campaign that reframes AstraCore from “audit-only” to “reliability-first product execution,” without claiming unshipped capabilities.

## 2) Core pillar themes
1. Discipline
   - Build foundations first; no hype releases.
2. Replay clarity
   - Clear session reconstruction needs reliable ingest + timeline handling.
3. Risk behavior
   - Product and operator risk both decrease when commit paths are controlled and verifiable.

## 3) 2-week cadence
Frequency:
- 5 primary posts/week (Mon-Fri)
- 2 lighter reinforcement posts/weekend (status snippet or short clip)
- 1 weekly recap thread/post

Platform mix:
- LinkedIn/X-style text narrative: trust + roadmap clarity
- Instagram carousel/Reel: simplified milestone education
- Optional short video: “what shipped vs what is still in progress”

## 4) Phase-linked content map (P1-2, P1-3, P1-4 framing)
Note: P1-2/P1-3/P1-4 are campaign phase labels mapped to engineering milestones. Posts must state “implemented,” “in progress,” or “queued.”

### Week 1 — P1-2 (stability foundations)
Focus:
- What reliability foundation means in practice.
- What is already implemented vs partial.

Post angles:
1. “Why atomic writes matter before any AI claims.”
2. “Org lock discipline: preventing multi-seat mutation collisions.”
3. “15-minute capture chunks and why that choice matters for stability.”
4. “Timeline integrity: component exists, full gate wiring status explained honestly.”
5. “Implemented vs partial board snapshot (plain-language).”

Weekend reinforcement:
- Mini status card: “This week: shipped baseline truth, no inflated promises.”

### Week 2 — P1-3 (control + verification)
Focus:
- Verification culture, risk reduction, and commit-path trust.
- Explain queued items without presenting them as done.

Post angles:
1. “Streaming ingest path: why RAM-spike prevention is a release gate.”
2. “Why tests are a trust feature, not just engineering overhead.”
3. “Stop-commit integrity checks: what exists now, what is being wired next.”
4. “How phase-based shipping protects users from fragile feature drops.”
5. “Who this is for: retail discipline users vs prop/team reliability leads.”

Weekend reinforcement:
- Short founder/operator note format: “What we will not claim until verified.”

### Optional carryover (P1-4 preview if approved)
Focus:
- Commercial and ops-fit messaging once policy constants and runbooks are locked.

Post angles (preview language only):
1. “From reliability baseline to release-readiness criteria.”
2. “How pricing/tier communication will stay tied to enforced policy, not marketing language.”

## 5) Post structure template (all posts)
1. Hook: one concrete reliability point
2. Truth line: implemented / partial / in progress
3. Why it matters: user impact in plain language
4. Boundary line: what is not shipped yet
5. CTA: follow roadmap / join waitlist / request status brief

## 6) CTA bank by segment
Retail-focused:
- Follow the build log for verified reliability releases.
- Join waitlist updates when milestones move from partial to implemented.
- Get the simple “what’s live now” status summary.

Prop/team manager-focused:
- Request the current reliability control snapshot for your team review.
- Track phase gates before adoption decisions.
- Join operator updates tied to verification evidence.

## 7) Execution safeguards
1. Never use “fully built,” “production-complete,” or equivalent unless verified in code/status review.
2. Every post draft must carry a status tag:
   - Implemented
   - Partial
   - In progress
   - Planned
3. No numeric performance promises or revenue claims.
4. No outbound publishing without R.A. approval.

## 8) Claim verification
Source files reviewed:
- /root/AstraCore/Astracore-Cleanslate/docs/GAP_AUDIT_RAOMEGA_V21.md
- /root/AstraCore/Astracore-Cleanslate/docs/HERMES_AGENT_UPGRADE_PLAN_RAOMEGA_V21.md

Campaign claims restricted to documented implemented items:
- Atomic ledger write discipline (implemented core paths)
- Org lock primitives
- 15-minute capture chunk behavior
- Codec fallback + bitrate ceiling
- Frame extraction/hash filtering + lossless concat in stop-commit output flow

Explicitly treated as non-shipped/in-progress in campaign language:
- Streamed (non-buffered) upload ingest path
- End-to-end timeline gate enforcement in stop-commit
- Full async upload interceptor route integration
- Complete test coverage suite
