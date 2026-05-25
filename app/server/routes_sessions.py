from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.billing.usage_enforcement import (
    can_start_session,
    mark_session_committed,
    mark_session_started,
)
from app.intel.behavior_tags import infer_behavior_tags
from app.intel.event_extractor import build_event_rows
from app.intel.frame_ocr import extract_frame_events
from app.intel.session_summary import build_session_summary
from app.intel.store import save_summary
from app.intel.transcription import transcribe_audio
from app.media_processing.splitter import finalize_session_output, process_session
from app.reports.daily_review import build_daily_review, save_daily_review
from app.server.schemas import SessionStartRequest, SessionStopCommitRequest
from app.server.session_store import load_session, save_session
from app.server.state import SESSIONS, SessionState, key

router = APIRouter(prefix="/api/session", tags=["session"])


@router.post("/start")
async def session_start(payload: SessionStartRequest):
    allowed, reason = can_start_session(
        user_id=payload.user_id,
        plan=payload.plan,
        operator_key=payload.operator_key,
    )
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)

    session_key = key(payload.user_id, payload.session_id)
    SESSIONS[session_key] = SessionState(
        user_id=payload.user_id,
        session_id=payload.session_id,
        operator_key=payload.operator_key,
        plan=payload.plan,
        status="recording",
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
    mark_session_started(user_id=payload.user_id, plan=payload.plan)
    save_session(SESSIONS[session_key])
    return {"status": "ok", "session_key": session_key, "plan": payload.plan}


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
        frame_paths = processed.get("frames", [])
        state.frame_count = len(frame_paths)

        transcript_segments = transcribe_audio(state.audio_path) if state.audio_path else []
        frame_events = extract_frame_events(frame_paths)
        event_rows = build_event_rows(transcript_segments, frame_events)
        behavior_tags = infer_behavior_tags(transcript_segments, frame_events)

        summary = build_session_summary(
            user_id=payload.user_id,
            session_id=payload.session_id,
            operator_key=payload.operator_key,
            audio_path=state.audio_path,
            frame_paths=frame_paths,
            transcript_segments=transcript_segments,
            event_rows=event_rows,
            behavior_tags=behavior_tags,
        )
        summary_path = save_summary(payload.user_id, payload.session_id, summary)
        daily_review = build_daily_review(summary)
        daily_review_path = save_daily_review(daily_review)

        state.status = "ready"
        state.updated_at = datetime.now(timezone.utc).isoformat()
        save_session(state)
        mark_session_committed(user_id=state.user_id, plan=state.plan)

        return {
            "status": "ok",
            "session_key": session_key,
            "merged_video": state.merged_video,
            "audio": state.audio_path,
            "frame_count": state.frame_count,
            "summary_path": summary_path,
            "daily_review_path": daily_review_path,
            "behavior_tags": behavior_tags,
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
