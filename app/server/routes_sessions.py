import asyncio
from datetime import datetime, timezone
from pathlib import Path

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
from app.core.checksum import verify_timeline_alignment
from app.core.upload_handler import BatchUploadInterceptor
from app.media_processing.splitter import finalize_session_output, process_session
from app.reports.daily_review import build_daily_review, save_daily_review
from app.server.schemas import SessionStartRequest, SessionStopCommitRequest
from app.server.session_store import load_session, save_session
from app.server.state import SESSIONS, SessionState, key

router = APIRouter(prefix="/api/session", tags=["session"])

_ORG_COMMIT_LOCKS: dict[str, asyncio.Lock] = {}
STOP_COMMIT_RETRY_ATTEMPTS = 2


def _org_lock(org_id: str) -> asyncio.Lock:
    return _ORG_COMMIT_LOCKS.setdefault(org_id, asyncio.Lock())


async def _run_with_retries(coro_factory, *, attempts: int, label: str):
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            return await coro_factory()
        except Exception as exc:  # pragma: no cover - behavior verified via route tests
            last_exc = exc
            if attempt >= attempts:
                break
    raise RuntimeError(f"{label} failed after {attempts} attempts: {last_exc}")


def _run_sync_with_retries(fn, *, attempts: int, label: str):
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:  # pragma: no cover
            last_exc = exc
            if attempt >= attempts:
                break
    raise RuntimeError(f"{label} failed after {attempts} attempts: {last_exc}")


async def _batch_process_asset(asset_path: Path, _operator_key: str) -> dict:
    return await process_session(str(asset_path), "workspace/captures")


UPLOAD_INTERCEPTOR = BatchUploadInterceptor(_batch_process_asset)


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
        async with _org_lock(payload.user_id):
            merged = await _run_with_retries(
                lambda: finalize_session_output(payload.user_id, payload.session_id),
                attempts=STOP_COMMIT_RETRY_ATTEMPTS,
                label="merge finalize",
            )

            _batch_meta, rows = await _run_with_retries(
                lambda: UPLOAD_INTERCEPTOR.submit_with_results(
                    [(Path(str(merged)), payload.operator_key)]
                ),
                attempts=STOP_COMMIT_RETRY_ATTEMPTS,
                label="batch processing",
            )
            processed_row = rows[0] if rows else {}
            if processed_row.get("status") != "ready":
                raise RuntimeError(processed_row.get("error") or "batch processing failed")

            state.merged_video = str(merged)
            state.audio_path = processed_row.get("audio")
            frame_paths = processed_row.get("frames", [])
            state.frame_count = len(frame_paths)

            audio_path = state.audio_path
            transcript_segments = (
                _run_sync_with_retries(
                    lambda: transcribe_audio(audio_path),
                    attempts=STOP_COMMIT_RETRY_ATTEMPTS,
                    label="audio transcription",
                )
                if audio_path
                else []
            )
            frame_events = _run_sync_with_retries(
                lambda: extract_frame_events(frame_paths),
                attempts=STOP_COMMIT_RETRY_ATTEMPTS,
                label="frame OCR extraction",
            )
            event_rows = build_event_rows(transcript_segments, frame_events)
            verify_timeline_alignment(event_rows, context=f"{payload.user_id}:{payload.session_id}")
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
