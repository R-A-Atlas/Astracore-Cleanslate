from __future__ import annotations

import json
import logging
import time
from collections import deque
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Deque

from fastapi import Request


logger = logging.getLogger("astracore.ops")

OPS_DIR = Path("workspace/ops")
LOGS_DIR = Path("workspace/logs")
METRICS_SNAPSHOT_PATH = OPS_DIR / "metrics_snapshot.json"
MAX_RECENT_REQUESTS = 200
MAX_RECENT_ERRORS = 50


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_metrics() -> dict:
    return {
        "started_at": utc_now_iso(),
        "last_updated_at": utc_now_iso(),
        "requests_total": 0,
        "requests_2xx": 0,
        "requests_4xx": 0,
        "requests_5xx": 0,
        "errors_total": 0,
        "avg_latency_ms": 0.0,
        "boot_count": 1,
    }


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load_metrics_snapshot() -> dict:
    OPS_DIR.mkdir(parents=True, exist_ok=True)
    if not METRICS_SNAPSHOT_PATH.exists():
        return _default_metrics()

    try:
        payload = json.loads(METRICS_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("metrics_snapshot_load_failed path=%s", METRICS_SNAPSHOT_PATH)
        return _default_metrics()

    baseline = _default_metrics()
    baseline.update(
        {
            "requests_total": _safe_int(payload.get("requests_total"), 0),
            "requests_2xx": _safe_int(payload.get("requests_2xx"), 0),
            "requests_4xx": _safe_int(payload.get("requests_4xx"), 0),
            "requests_5xx": _safe_int(payload.get("requests_5xx"), 0),
            "errors_total": _safe_int(payload.get("errors_total"), 0),
            "avg_latency_ms": round(_safe_float(payload.get("avg_latency_ms"), 0.0), 2),
            "boot_count": _safe_int(payload.get("boot_count"), 0) + 1,
        }
    )
    baseline["started_at"] = utc_now_iso()
    baseline["last_updated_at"] = utc_now_iso()
    return baseline


OPS_METRICS = load_metrics_snapshot()
RECENT_REQUESTS: Deque[dict] = deque(maxlen=MAX_RECENT_REQUESTS)
RECENT_ERRORS: Deque[dict] = deque(maxlen=MAX_RECENT_ERRORS)


def persist_metrics_snapshot() -> None:
    OPS_DIR.mkdir(parents=True, exist_ok=True)
    OPS_METRICS["last_updated_at"] = utc_now_iso()
    tmp_path = METRICS_SNAPSHOT_PATH.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(OPS_METRICS, indent=2, sort_keys=True), encoding="utf-8")
    tmp_path.replace(METRICS_SNAPSHOT_PATH)


def configure_logging() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    if not root.handlers:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        root.addHandler(stream_handler)

    file_path = LOGS_DIR / "api.log"
    already_has_rotating = any(
        isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", "") == str(file_path)
        for h in root.handlers
    )
    if not already_has_rotating:
        rotating = RotatingFileHandler(
            file_path,
            maxBytes=2_000_000,
            backupCount=5,
            encoding="utf-8",
        )
        rotating.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        root.addHandler(rotating)


async def observability_middleware(request: Request, call_next):
    start = time.perf_counter()
    method = request.method
    path = request.url.path

    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as exc:
        status_code = 500
        OPS_METRICS["errors_total"] += 1
        error_row = {
            "at": utc_now_iso(),
            "method": method,
            "path": path,
            "error": str(exc),
        }
        RECENT_ERRORS.append(error_row)
        logger.exception("request_failed path=%s method=%s error=%s", path, method, exc)
        raise
    finally:
        latency_ms = (time.perf_counter() - start) * 1000

        OPS_METRICS["requests_total"] += 1
        total = OPS_METRICS["requests_total"]
        OPS_METRICS["avg_latency_ms"] = round(
            ((OPS_METRICS["avg_latency_ms"] * (total - 1)) + latency_ms) / total,
            2,
        )

        if 200 <= status_code < 300:
            OPS_METRICS["requests_2xx"] += 1
        elif 400 <= status_code < 500:
            OPS_METRICS["requests_4xx"] += 1
        elif status_code >= 500:
            OPS_METRICS["requests_5xx"] += 1

        request_row = {
            "at": utc_now_iso(),
            "method": method,
            "path": path,
            "status": status_code,
            "latency_ms": round(latency_ms, 2),
        }
        RECENT_REQUESTS.append(request_row)
        logger.info(
            "request method=%s path=%s status=%s latency_ms=%.2f",
            method,
            path,
            status_code,
            latency_ms,
        )
        persist_metrics_snapshot()

    return response


def get_ops_metrics() -> dict:
    return {
        **OPS_METRICS,
        "recent_requests_count": len(RECENT_REQUESTS),
        "recent_errors_count": len(RECENT_ERRORS),
        "snapshot_path": str(METRICS_SNAPSHOT_PATH),
        "log_path": str(LOGS_DIR / "api.log"),
    }
