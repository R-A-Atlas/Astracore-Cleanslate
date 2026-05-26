#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8080}"
OPS_TOKEN="${ASTRACORE_OPS_TOKEN:-dev-ops-token}"

status_code=$(curl -sS -o /tmp/astracore_healthz.out -w "%{http_code}" -H "x-ops-token: ${OPS_TOKEN}" "${BASE_URL}/ops/alerts/healthz")
body=$(cat /tmp/astracore_healthz.out)

if [[ "$status_code" == "200" && "$body" == "ok" ]]; then
  echo "OK: ${BASE_URL}/ops/alerts/healthz"
  exit 0
fi

echo "DEGRADED: ${BASE_URL}/ops/alerts/healthz status=${status_code} body=${body}"
exit 1
