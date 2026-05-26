## Private Beta Runbook

### Purpose
Use `scripts/private_beta_smoke.sh` to verify core private-beta gates before release:
- Auth signup/login
- Google OAuth start/callback (local deterministic code path)
- Dashboard summary load
- Settings save/load roundtrip
- Billing hard-lock enforcement

### Standard execution
1. From repo root:
   - `bash scripts/private_beta_smoke.sh`
2. Expected result:
   - Exit code `0`
   - Final line: `SMOKE_OK private beta gate`

### Failure handling and triage
When the script exits non-zero, inspect the first `[FAIL] <step> :: <detail>` line.

#### Step-by-step triage
- `signup` / `login`
  - Check auth env wiring and auth stores (`ASTRACORE_AUTH_*` files).
  - Verify no schema/validation regressions in `/api/auth/signup` and `/api/auth/login`.
- `google_start` / `google_callback`
  - Confirm local OAuth vars are set:
    - `ASTRACORE_GOOGLE_OAUTH_CLIENT_ID`
    - `ASTRACORE_GOOGLE_OAUTH_REDIRECT_URI`
  - Ensure callback accepts `local-google:<sub>:<email>` codes in local mode.
- `dashboard_summary`
  - Verify bearer token parsing in `/api/auth/me` path dependencies.
  - Check dashboard route auth dependency and response schema.
- `settings_save` / `settings_load`
  - Check `UserSettingsV1` schema compatibility.
  - Verify user settings store path and read/write permissions.
- `billing_enforcement`
  - Verify usage bucket key format: `<org>:<YYYY-MM>:<plan>`.
  - Confirm `retail` plan limits and hard-lock behavior in `usage_enforcement`.

### Incident response checklist
- Capture:
  - failing step name
  - full script output
  - commit SHA under test
- Reproduce locally with the same command.
- If needed, force fail-fast in CI/debug:
  - `PRIVATE_BETA_SMOKE_FORCE_FAIL_STEP=login bash scripts/private_beta_smoke.sh`
- Open incident with:
  - impact scope (auth/oauth/dashboard/settings/billing)
  - first bad commit (if known)
  - owner and ETA

### Recovery / rollback guidance
- If smoke fails on `main`, block release push.
- Revert only offending commit(s) or hotfix and rerun smoke.
- Require passing smoke output (`SMOKE_OK private beta gate`) before unblocking release.
