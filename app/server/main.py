from fastapi import FastAPI

from app.server.routes_ingest import router as ingest_router
from app.server.routes_ops import router as ops_router
from app.server.routes_sessions import router as session_router

app = FastAPI(title="AstraCore Cleanslate API", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(ingest_router)
app.include_router(session_router)
app.include_router(ops_router)
