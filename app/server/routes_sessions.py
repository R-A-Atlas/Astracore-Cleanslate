from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.media_processing.splitter import finalize_session_output, process_session
from app.server.schemas import SessionStartRequest, SessionStopCommitRequest
from app.server.session_store import load_session, save_session
from app.server.state import SESSIONS, SessionState, key

router = APIRouter(prefix="/api/session", tags=["session"])


@router.post("/start")
async def session_start(payload: SessionStartRequest):
    session_key = key(payload.user_id, payload.session_id)
    SESSIONS[session_key] = SessionState(
        user_id=payload.user_id,
        session_id=payload.session_id,
        operator_key=payload.operator_key,
        status="recording",
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
    save_session(SESSIONS[session_key])
    return {"status": "ok", "session_key": session_key}


@router.post("/stop-commit")
async def session_stop_commit(payload: SessionStopCommitRequest):
    session_key = key(payload.user_id, payload.session_id)
    state = SESSIONS.get(session_key)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    state.status = "processing"
    state.updated_at = datetime.now(timezone.utc).isoformat()
    save_session(state)

    try:
        merged = await finalize_session_output(payload.user_id, payload.session_id)
        processed = await process_session(str(merged), "workspace/captures")

        state.merged_video = str(merged)
        state.audio_path = processed.get("audio")
        state.frame_count = len(processed.get("frames", []))
        state.status = "ready"
        state.updated_at = datetime.now(timezone.utc).isoformat()
        save_session(state)

        return {
            "status": "ok",
            "session_key": session_key,
            "merged_video": state.merged_video,
            "audio": state.audio_path,
            "frame_count": state.frame_count,
        }
    except Exception as exc:
        state.status = "failed"
        state.error = str(exc)
        state.updated_at = datetime.now(timezone.utc).isoformat()
        save_session(state)
        raise HTTPException(status_code=500, detail=f"Stop-commit failed: {exc}")


@router.get("/{session_id}/status")
async def session_status(session_id: str, user_id: str):
    session_key = key(user_id, session_id)
    state = SESSIONS.get(session_key)
    if state:
        return state.__dict__

    stored = load_session(user_id, session_id)
    if not stored:
        raise HTTPException(status_code=404, detail="Session not found")
    return stored
