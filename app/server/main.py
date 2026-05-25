from fastapi import FastAPI

from app.core.runtime_preflight import ensure_runtime_ready
from app.server.routes_ingest import router as ingest_router
from app.server.routes_ops import router as ops_router
from app.server.routes_sessions import router as session_router

app = FastAPI(title="AstraCore Cleanslate API", version="0.1.0")
app.state.runtime = {}


@app.on_event("startup")
async def startup_preflight() -> None:
    app.state.runtime = ensure_runtime_ready()


@app.get("/health")
async def health():
    return {"status": "ok", "runtime": app.state.runtime}


app.include_router(ingest_router)
app.include_router(session_router)
app.include_router(ops_router)
