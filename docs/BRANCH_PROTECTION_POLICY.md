# Branch Protection Policy (main)

## Current enforced controls
- Required status check: `security-release-gate`
- Strict status checks: enabled (branch must be up to date before merge)
- Enforce for admins: enabled
- Force pushes: disabled
- Branch deletion: disabled

## Owner/Admin exception policy
- Default policy: **no bypass exceptions** on `main`.
- Repo owners/admins follow the same required checks as all contributors.
- Emergency override is allowed only for production recovery and must be logged in project notes with:
  - reason
  - timestamp (UTC)
  - actor
  - rollback/follow-up action

## Operator rule (AstraCore)
- Always run `bash scripts/release_gate_security.sh` before any push.
- Prefer PR flow; direct pushes to `main` should be rare and justified.
