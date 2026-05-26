from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.ops_observability import configure_logging, observability_middleware
from app.core.runtime_preflight import ensure_runtime_ready
from app.core.security_guardrails import (
    OPS_TOKEN_HEADER,
    RATE_LIMIT_PER_MIN,
    RATE_LIMIT_WINDOW_SEC,
    ops_auth_and_rate_limit_middleware,
)
from app.core.settings import load_runtime_settings
from app.server.routes_auth import router as auth_router
from app.server.routes_auth_google import router as auth_google_router
from app.server.routes_dashboard import router as dashboard_router
from app.server.routes_ingest import router as ingest_router
from app.server.routes_ops import router as ops_router
from app.server.routes_sessions import router as session_router

@asynccontextmanager
async def app_lifespan(app: FastAPI):
    runtime = load_runtime_settings()
    app.state.runtime = ensure_runtime_ready()
    app.state.runtime["app"] = {"port": runtime.port, "environment": runtime.environment}
    app.state.runtime["ops_auth"] = {"header": OPS_TOKEN_HEADER, "token_env": "ASTRACORE_OPS_TOKEN"}
    app.state.runtime["rate_limit"] = {
        "sensitive_endpoints_per_min": RATE_LIMIT_PER_MIN,
        "window_seconds": RATE_LIMIT_WINDOW_SEC,
    }
    yield


app = FastAPI(title="AstraCore Cleanslate API", version="0.1.0", lifespan=app_lifespan)
app.state.runtime = {}
configure_logging()
app.middleware("http")(observability_middleware)
app.middleware("http")(ops_auth_and_rate_limit_middleware)


@app.get("/health")
async def health():
    return {"status": "ok", "runtime": app.state.runtime}


app.include_router(ingest_router)
app.include_router(session_router)
app.include_router(ops_router)
app.include_router(auth_router)
app.include_router(auth_google_router)
app.include_router(dashboard_router)
