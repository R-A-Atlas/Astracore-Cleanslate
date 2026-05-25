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
