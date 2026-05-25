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
- `GET /ops/recent-requests?limit=50` → rolling request log window
- `GET /ops/recent-errors?limit=20` → failed sessions + request exceptions
- `GET /ops/status` → session status summary + embedded metrics
