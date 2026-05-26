#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[release-gate] compile check"
python -m compileall app

echo "[release-gate] targeted security suite"
python -m pytest -q \
  tests/test_p8_ops_auth_enforcement.py \
  tests/test_p8_rate_limit_sensitive_paths.py \
  tests/test_p8_tenant_binding.py \
  tests/test_p9_abuse_resilience_edges.py

echo "[release-gate] PASS"
