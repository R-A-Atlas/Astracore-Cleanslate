# AstraCore Cleanslate (Base Body)

Minimal runtime baseline for local API bring-up.

## 1) Prerequisites
- Python 3.11+
- `ffmpeg` and `ffprobe` available in `PATH`

Quick check:
```bash
ffmpeg -version
ffprobe -version
```

## 2) Install deps
```bash
pip install -r requirements.txt
```

## 3) Run API
From repo root:
```bash
uvicorn app.server.main:app --host 0.0.0.0 --port 8080 --reload
```

## 4) Health check
```bash
curl -s http://localhost:8080/health
```
Expected shape:
- `status: ok`
- `runtime.ffmpeg`: detected path
- `runtime.ffprobe`: detected path

## Runtime preflight (P0-6)
On startup, API now:
- Creates required directories:
  - `workspace/uploads`
  - `workspace/captures`
  - `workspace/memory/sessions`
  - `workspace/memory/intel`
  - `workspace/outputs/reports/daily`
- Hard-fails startup if `ffmpeg/ffprobe` are missing.

## Billing lock (V1)
Session overage is now **hard-locked**:
- once monthly included sessions are exhausted, `/api/session/start` returns `403`.
- overage/add-on behavior is disabled for V1 and can be adjusted later in:
  - `app/billing/usage_enforcement.py`

## Ops visibility baseline (P0-7)
Request-level observability is now enabled:
- structured request logs on every HTTP call (`method`, `path`, `status`, `latency_ms`)
- exception logging for failed requests
- in-memory counters for:
  - total requests
  - 2xx / 4xx / 5xx breakdown
  - average latency
  - total errors

New ops endpoints:
- `GET /ops/metrics` → current counters
- `GET /ops/upload-interceptor?limit_failed=10` → upload/processing visibility (queue depth, ready/failed totals, recent failures)
- `GET /ops/throughput-trend?window_min=15` → request throughput/error-rate trend window
- `GET /ops/alerts?window_min=15` → alert state from error-rate + queue-depth thresholds
- `GET /ops/alerts/health?window_min=15` → monitor-friendly health probe (`200` when alert level is `ok`, else `503`)
- `GET /ops/alerts/healthz?window_min=15` → plain-text probe (`ok` / `degraded`) for simple health-check systems
- `GET /ops/recent-requests?limit=50` → rolling request log window
- `GET /ops/recent-errors?limit=20` → failed sessions + request exceptions
- `GET /ops/config` → sanitized runtime/security config (no secrets)


## Persistence hardening (P0-8)
Ops baseline is now restart-safe and log-safe:
- metrics snapshot persisted to disk: `workspace/ops/metrics_snapshot.json`
- snapshot is atomically rewritten on each request update
- counters survive restarts (with `boot_count` incremented per startup)
- rotating API logs enabled at `workspace/logs/api.log`
  - max size: ~2 MB per file
  - backups kept: 5

Startup/runtime directories now also include:
- `workspace/ops`
- `workspace/logs`

## Security guardrails (P0-9)
Baseline protection for internal operations is now active:
- `/ops/*` endpoints require header auth:
  - header: `x-ops-token`
  - token source env: `ASTRACORE_OPS_TOKEN`
  - default local fallback: `dev-ops-token` (change this in real deployment)
- Sensitive write endpoints now have per-IP rate limiting (rolling 60s window):
  - `/api/session/start`
  - `/api/session/stop-commit`
  - `/api/upload/part`

Rate-limit envs:
- `ASTRACORE_RATE_LIMIT_PER_MIN` (default: `60`)
- `ASTRACORE_RATE_LIMIT_WINDOW_SEC` (default: `60`)

Ops alert threshold envs:
- `ASTRACORE_ALERT_ERROR_RATE_WARN_PCT` (default: `5`)
- `ASTRACORE_ALERT_ERROR_RATE_CRIT_PCT` (default: `15`)
- `ASTRACORE_ALERT_QUEUE_DEPTH_WARN` (default: `5`)
- `ASTRACORE_ALERT_QUEUE_DEPTH_CRIT` (default: `10`)

Quick ops auth check:
```bash
curl -i http://localhost:8080/ops/metrics
curl -i -H "x-ops-token: dev-ops-token" http://localhost:8080/ops/metrics
```

Health monitor script (P1-6):
```bash
bash scripts/ops_alert_healthz_check.sh http://127.0.0.1:8080
```
- returns exit `0` when healthy (`ok`)
- returns exit `1` when degraded (`warning/critical`)

## P2-1 transcript artifact contract
On successful `/api/session/stop-commit`, response now includes:
- `transcript_path`

Transcript artifact file is written at:
- `workspace/memory/intel/<user_id>__<session_id>__transcript.json`

Payload includes:
- `generated_at`
- `user_id`
- `session_id`
- `provider`
- `audio_path`
- `segment_count`
- `segments`

## P2-2 OCR/event normalization contract
`build_event_rows(...)` now emits a normalized timeline for transcript + frame events.
Each row includes:
- `id`
- `type` (`transcript` or `frame`)
- `epoch_ms` (monotonic sortable key)
- `source`

Transcript rows include:
- `start_ms`, `end_ms`, `text`

Frame rows include:
- `index`, `frame`, `event`

Fallback behavior:
- if a frame event has no `epoch_ms`, one is derived after transcript window (`max transcript end + 1 + index*1000`).
- final rows are sorted by `epoch_ms`, then transcript before frame on ties.

## P2-3 fusion lane contract
On successful `/api/session/stop-commit`, response now also includes:
- `fusion_timeline_path`

Fusion artifact file:
- `workspace/memory/intel/<user_id>__<session_id>__fusion_timeline.json`

Payload includes:
- `counts` (`transcript_segments`, `frame_events`, `timeline_rows`)
- `transcript_chunks`
- `frame_chunks`
- `timeline_rows`

Purpose:
- provide a query-ready, unified timeline object for read-only consult APIs.

## P2-4 consult API (read-only)
New route:
- `GET /api/session/{session_id}/consult?user_id=<id>&query=<text>&limit=5&offset=<0+>&mode=<or|and>&sort=<score_desc|time_asc|time_desc>&fields=<csv:text|event|frame|source>&min_token_hits=<1..20>&min_coverage_pct=<0..100>&min_score=<0..200>&include_context=<true|false>&row_type=<transcript|frame>&start_epoch_ms=<int>&end_epoch_ms=<int>`

Behavior:
- loads fusion timeline artifact
- performs case-insensitive keyword match across timeline row fields (`text`, `event`, `frame`, `source`)
- supports optional row-type filter and epoch range filter
- supports query mode: `or` (any token) or `and` (all tokens)
- supports optional `fields` scope filter (`text,event,frame,source`) to constrain search surface
- supports `min_token_hits` threshold (1..20) to require a minimum number of matched query tokens per hit
- supports `min_coverage_pct` threshold (0..100) to enforce query-token coverage quality
- supports `min_score` threshold filtering (0..200)
- supports `include_context=true` to attach one before/after row around each match
- supports pagination via `offset`; response returns `total_matches` and `next_offset`
- supports sort mode: `score_desc` (default), `time_asc`, `time_desc`
- each sort mode has deterministic tie-breakers (score/epoch)
- each match includes `match_score`, `matched_field`, `matched_snippet`, and `matched_tokens`
- response includes `stats` block with `avg_score`, `max_score`, and `token_coverage_pct`
- returns deterministic metadata (`filters`, `scanned_rows`, `match_count`)
- never mutates session artifacts
