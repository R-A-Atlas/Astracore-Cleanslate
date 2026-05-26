# EXECUTION BOARD — P11 PRODUCT POLISH

## Status
- P11-1 subscription naming/pricing polish — completed
- P11-2 support policy alignment (copy + backend support contract flags) — completed
- P11-3 plan key alignment (UI names ↔ backend plan IDs) — completed
- P11-4 billing page trust + policy clarity — completed
- P11-5 branch protection hardening — completed

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
- GitHub branch rules updated so `security-release-gate` is truly required.
- Document owner/admin exception policy.

## Rules (always)
- Run `bash scripts/release_gate_security.sh` before every push.
- Keep commits slice-atomic.
- Verify `HEAD == origin/main` after every push.
