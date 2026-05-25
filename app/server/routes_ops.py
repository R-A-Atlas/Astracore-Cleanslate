import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Response

from app.core.ops_observability import RECENT_ERRORS, RECENT_REQUESTS, get_ops_metrics
from app.core.security_guardrails import OPS_TOKEN_HEADER, RATE_LIMIT_PER_MIN, RATE_LIMIT_WINDOW_SEC
from app.core.settings import load_ops_alert_settings, load_runtime_settings
from app.server.routes_sessions import UPLOAD_INTERCEPTOR
from app.server.state import SESSIONS

router = APIRouter(prefix="/ops", tags=["ops"])


def _parse_iso_z(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


@router.get("/status")
async def ops_status():
    by_status: dict[str, int] = {}
    for s in SESSIONS.values():
        by_status[s.status] = by_status.get(s.status, 0) + 1
    return {
        "sessions_total": len(SESSIONS),
        "by_status": by_status,
        "metrics": get_ops_metrics(),
    }


@router.get("/metrics")
async def ops_metrics():
    return get_ops_metrics()


@router.get("/upload-interceptor")
async def ops_upload_interceptor(limit_failed: int = 10):
    rows = UPLOAD_INTERCEPTOR.get_results()
    ready = UPLOAD_INTERCEPTOR.get_ready_results()
    failed = UPLOAD_INTERCEPTOR.get_failed_results()
    processing_sessions = [s.__dict__ for s in SESSIONS.values() if s.status == "processing"]
    return {
        "results_total": len(rows),
        "ready_total": len(ready),
        "failed_total": len(failed),
        "queue_depth": len(processing_sessions),
        "processing_sessions": processing_sessions,
        "recent_failed": failed[-limit_failed:],
    }


@router.get("/throughput-trend")
async def ops_throughput_trend(window_min: int = 15):
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=max(1, min(window_min, 240)))
    rows = list(RECENT_REQUESTS)
    recent = [r for r in rows if (_parse_iso_z(r.get("at", "")) or cutoff) >= cutoff]
    total = len(recent)
    err_5xx = sum(1 for r in recent if int(r.get("status", 0)) >= 500)
    avg_latency_ms = round(sum(float(r.get("latency_ms", 0.0)) for r in recent) / total, 2) if total else 0.0
    rpm = round(total / max(1, window_min), 2)
    return {
        "window_min": window_min,
        "requests": total,
        "requests_per_min": rpm,
        "errors_5xx": err_5xx,
        "error_rate_5xx_pct": round((err_5xx / total) * 100, 2) if total else 0.0,
        "avg_latency_ms": avg_latency_ms,
    }


@router.get("/alerts")
async def ops_alerts(window_min: int = 15):
    trend = await ops_throughput_trend(window_min=window_min)
    interceptor = await ops_upload_interceptor(limit_failed=5)
    alert_cfg = load_ops_alert_settings()

    error_rate = trend["error_rate_5xx_pct"]
    queue_depth = interceptor["queue_depth"]

    error_level = "ok"
    if error_rate >= alert_cfg.error_rate_crit_pct:
        error_level = "critical"
    elif error_rate >= alert_cfg.error_rate_warn_pct:
        error_level = "warning"

    queue_level = "ok"
    if queue_depth >= alert_cfg.queue_depth_crit:
        queue_level = "critical"
    elif queue_depth >= alert_cfg.queue_depth_warn:
        queue_level = "warning"

    overall = "ok"
    if "critical" in (error_level, queue_level):
        overall = "critical"
    elif "warning" in (error_level, queue_level):
        overall = "warning"

    return {
        "level": overall,
        "window_min": window_min,
        "checks": {
            "error_rate_5xx": {
                "value_pct": error_rate,
                "warn_pct": alert_cfg.error_rate_warn_pct,
                "crit_pct": alert_cfg.error_rate_crit_pct,
                "level": error_level,
            },
            "queue_depth": {
                "value": queue_depth,
                "warn": alert_cfg.queue_depth_warn,
                "crit": alert_cfg.queue_depth_crit,
                "level": queue_level,
            },
        },
        "context": {
            "throughput": trend,
            "upload_interceptor": {
                "results_total": interceptor["results_total"],
                "ready_total": interceptor["ready_total"],
                "failed_total": interceptor["failed_total"],
                "recent_failed": interceptor["recent_failed"],
            },
        },
    }


@router.get("/alerts/health")
async def ops_alerts_health(window_min: int = 15):
    alerts = await ops_alerts(window_min=window_min)
    status_code = 200 if alerts.get("level") == "ok" else 503
    return Response(
        content=(
            '{"status":"ok","level":"ok"}'
            if status_code == 200
            else '{"status":"degraded","level":"' + str(alerts.get("level")) + '"}'
        ),
        status_code=status_code,
        media_type="application/json",
    )


@router.get("/config")
async def ops_config():
    runtime = load_runtime_settings()
    token = os.getenv("ASTRACORE_OPS_TOKEN", "").strip()
    return {
        "app": {
            "port": runtime.port,
            "environment": runtime.environment,
        },
        "ops_auth": {
            "header": OPS_TOKEN_HEADER,
            "token_configured": bool(token),
        },
        "rate_limit": {
            "sensitive_endpoints_per_min": RATE_LIMIT_PER_MIN,
            "window_seconds": RATE_LIMIT_WINDOW_SEC,
        },
    }


@router.get("/recent-requests")
async def ops_recent_requests(limit: int = 50):
    rows = list(RECENT_REQUESTS)
    return {"count": len(rows), "rows": rows[-limit:]}


@router.get("/recent-errors")
async def ops_recent_errors(limit: int = 20):
    failed_sessions = [s.__dict__ for s in SESSIONS.values() if s.status == "failed"]
    request_errors = list(RECENT_ERRORS)
    return {
        "failed_sessions_count": len(failed_sessions),
        "request_errors_count": len(request_errors),
        "failed_sessions": failed_sessions[-limit:],
        "request_errors": request_errors[-limit:],
    }
