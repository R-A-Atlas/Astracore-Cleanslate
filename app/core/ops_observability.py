from __future__ import annotations

import logging
import time
from collections import deque
from datetime import datetime, timezone
from typing import Deque

from fastapi import Request


logger = logging.getLogger("astracore.ops")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


OPS_METRICS = {
    "started_at": utc_now_iso(),
    "requests_total": 0,
    "requests_2xx": 0,
    "requests_4xx": 0,
    "requests_5xx": 0,
    "errors_total": 0,
    "avg_latency_ms": 0.0,
}

RECENT_REQUESTS: Deque[dict] = deque(maxlen=200)
RECENT_ERRORS: Deque[dict] = deque(maxlen=50)


def configure_logging() -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )


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

    return response


def get_ops_metrics() -> dict:
    return {
        **OPS_METRICS,
        "recent_requests_count": len(RECENT_REQUESTS),
        "recent_errors_count": len(RECENT_ERRORS),
    }
