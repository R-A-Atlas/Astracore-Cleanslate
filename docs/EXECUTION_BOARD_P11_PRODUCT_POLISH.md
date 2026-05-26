# EXECUTION BOARD — P11 PRODUCT POLISH

## Status
- P11-1 subscription naming/pricing polish — completed
- P11-2 support policy alignment (copy + backend support contract flags) — completed
- P11-3 plan key alignment (UI names ↔ backend plan IDs) — completed
- P11-4 billing page trust + policy clarity — completed
- P11-5 branch protection hardening — completed
- P11-6 cleanup slice (runtime artifact hygiene + post-merge parity) — completed
- P11-7 checkout provider fail-fast validation coverage — completed
- P11-8 pricing trust strip near CTA — completed
- P11-9 ops billing visibility (`/ops/billing`) — completed

## Next slices

### P11-3 plan key alignment (UI names ↔ backend plan IDs)
Goal:
- Ensure Starter/Pro/Desk labels map clearly to backend plan keys used in billing APIs.

DoD:
- Add explicit mapping contract in backend (no ambiguous defaults).
- Add tests for mapping and invalid plan fallback behavior.
- Keep frontend copy independent from backend enforcement names.

### P11-4 billing page trust + policy clarity
Goal:
- Add one short support policy note near pricing CTA and avoid overpromises.

DoD:
- Note confirms: AI support on all tiers, live support bugs/account only, 24-48h SLA.
- Copy reviewed for consistency across pricing cards and checkout entry points.

### P11-5 branch protection hardening
Goal:
- Remove bypass ambiguity on main and enforce required checks.

DoD:
- GitHub branch rules updated so the live required check `gate` is enforced.
- Document owner/admin exception policy.

## P11-9 contract note — `/ops/billing`
- Endpoint: `GET /ops/billing`
- Auth: required ops token header (`x-ops-token` unless overridden by env)
- Purpose: visibility into plan normalization and invalid plan pressure
- Response keys:
  - `plan_validation.total_requests`
  - `plan_validation.backend_direct_hits`
  - `plan_validation.alias_hits`
  - `plan_validation.defaulted_blank`
  - `plan_validation.invalid_attempts`
  - `plan_validation.allowed_backend_plans`
  - `plan_validation.allowed_aliases`

## Rules (always)
- Run `bash scripts/release_gate_security.sh` before every push.
- Keep commits slice-atomic.
- Verify `HEAD == origin/main` after every push.
