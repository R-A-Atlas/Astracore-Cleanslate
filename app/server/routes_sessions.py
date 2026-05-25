import asyncio
from datetime import datetime, timezone
import json
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
from app.intel.fusion import build_query_timeline
from app.intel.session_summary import build_session_summary
from app.intel.store import save_fusion_timeline, save_summary, save_transcript
from app.intel.transcription import transcribe_audio
from app.core.checksum import verify_timeline_alignment
from app.core.incidents import write_failure_incident_bundle
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


def _fusion_path(user_id: str, session_id: str) -> Path:
    return Path("workspace/memory/intel") / f"{user_id}__{session_id}__fusion_timeline.json"


def _snippet(text: str, query: str, radius: int = 32) -> str:
    idx = text.lower().find(query)
    if idx < 0:
        return text[: radius * 2].strip()
    start = max(0, idx - radius)
    end = min(len(text), idx + len(query) + radius)
    return text[start:end].strip()


def _tokenize_query(query: str) -> list[str]:
    return [t for t in query.strip().lower().split() if t]


def _score_match(row: dict, tokens: list[str]) -> tuple[int, str, str]:
    fields = [
        ("text", str(row.get("text") or "")),
        ("event", str(row.get("event") or "")),
        ("frame", str(row.get("frame") or "")),
        ("source", str(row.get("source") or "")),
    ]
    best_score = 0
    best_field = ""
    best_snippet = ""
    for name, value in fields:
        lowered = value.lower()
        token_hits = [tok for tok in tokens if tok in lowered]
        if not token_hits:
            continue
        count = sum(lowered.count(tok) for tok in token_hits)
        score = count * 10
        if len(token_hits) == len(tokens):
            score += 8
        if name == "text":
            score += 4
        if name == "event":
            score += 2
        if score > best_score:
            best_score = score
            best_field = name
            best_snippet = _snippet(value, token_hits[0])

    if str(row.get("type") or "").lower() == "transcript" and best_score > 0:
        best_score += 1

    return best_score, best_field, best_snippet


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
            transcript_path = save_transcript(
                payload.user_id,
                payload.session_id,
                audio_path=audio_path,
                segments=transcript_segments,
                provider="local_stub",
            )
            frame_events = _run_sync_with_retries(
                lambda: extract_frame_events(frame_paths),
                attempts=STOP_COMMIT_RETRY_ATTEMPTS,
                label="frame OCR extraction",
            )
            event_rows = build_event_rows(transcript_segments, frame_events)
            verify_timeline_alignment(event_rows, context=f"{payload.user_id}:{payload.session_id}")
            behavior_tags = infer_behavior_tags(transcript_segments, frame_events)
            fusion_payload = build_query_timeline(
                user_id=payload.user_id,
                session_id=payload.session_id,
                transcript_segments=transcript_segments,
                frame_events=frame_events,
                event_rows=event_rows,
            )
            fusion_timeline_path = save_fusion_timeline(payload.user_id, payload.session_id, fusion_payload)

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
                "transcript_path": transcript_path,
                "fusion_timeline_path": fusion_timeline_path,
                "daily_review_path": daily_review_path,
                "behavior_tags": behavior_tags,
            }
    except Exception as exc:
        state.status = "failed"
        state.error = str(exc)
        state.updated_at = datetime.now(timezone.utc).isoformat()
        incident_path = write_failure_incident_bundle(
            user_id=payload.user_id,
            session_id=payload.session_id,
            operator_key=payload.operator_key,
            stage="stop_commit",
            error=str(exc),
            state=state.__dict__,
        )
        save_session(state)
        raise HTTPException(status_code=500, detail=f"Stop-commit failed: {exc} | incident={incident_path}")


@router.get("/{session_id}/consult")
async def session_consult(
    session_id: str,
    user_id: str,
    query: str,
    limit: int = 5,
    mode: str = "or",
    min_score: int = 0,
    include_context: bool = False,
    row_type: str | None = None,
    start_epoch_ms: int | None = None,
    end_epoch_ms: int | None = None,
):
    fusion_path = _fusion_path(user_id, session_id)
    if not fusion_path.exists():
        raise HTTPException(status_code=404, detail="Fusion timeline not found")

    payload = json.loads(fusion_path.read_text())
    rows = payload.get("timeline_rows", [])
    q = (query or "").strip().lower()
    if not q:
        raise HTTPException(status_code=400, detail="query is required")
    tokens = _tokenize_query(q)

    query_mode = (mode or "or").strip().lower()
    if query_mode not in {"or", "and"}:
        raise HTTPException(status_code=400, detail="mode must be and or or")
    if min_score < 0 or min_score > 200:
        raise HTTPException(status_code=400, detail="min_score must be between 0 and 200")

    allowed_type = (row_type or "").strip().lower() or None
    if allowed_type and allowed_type not in {"transcript", "frame"}:
        raise HTTPException(status_code=400, detail="row_type must be transcript or frame")

    effective_limit = max(1, min(limit, 20))
    ranked = []
    scanned = 0
    for row in rows:
        scanned += 1
        epoch_ms = int(row.get("epoch_ms") or 0)
        if start_epoch_ms is not None and epoch_ms < start_epoch_ms:
            continue
        if end_epoch_ms is not None and epoch_ms > end_epoch_ms:
            continue
        if allowed_type and str(row.get("type") or "").lower() != allowed_type:
            continue

        blob = " ".join(
            [
                str(row.get("text") or ""),
                str(row.get("event") or ""),
                str(row.get("frame") or ""),
                str(row.get("source") or ""),
            ]
        ).lower()
        token_presence = [tok in blob for tok in tokens]
        if query_mode == "and" and not all(token_presence):
            continue
        if query_mode == "or" and not any(token_presence):
            continue

        score, matched_field, matched_snippet = _score_match(row, tokens)
        if score <= 0 or score < min_score:
            continue
        ranked.append(
            {
                "score": score,
                "epoch_ms": epoch_ms,
                "row": row,
                "matched_field": matched_field,
                "matched_snippet": matched_snippet,
            }
        )

    ranked.sort(key=lambda x: (-x["score"], x["epoch_ms"]))
    top = ranked[:effective_limit]
    matches = []
    for item in top:
        out_row = {
            **item["row"],
            "match_score": item["score"],
            "matched_field": item["matched_field"],
            "matched_snippet": item["matched_snippet"],
        }
        if include_context:
            row_epoch = int(item["row"].get("epoch_ms") or 0)
            context_before = [
                r
                for r in rows
                if int(r.get("epoch_ms") or 0) < row_epoch
            ][-1:]
            context_after = [
                r
                for r in rows
                if int(r.get("epoch_ms") or 0) > row_epoch
            ][:1]
            out_row["context"] = {
                "before": context_before,
                "after": context_after,
            }
        matches.append(out_row)

    return {
        "status": "ok",
        "user_id": user_id,
        "session_id": session_id,
        "query": query,
        "filters": {
            "mode": query_mode,
            "min_score": min_score,
            "include_context": include_context,
            "row_type": allowed_type,
            "start_epoch_ms": start_epoch_ms,
            "end_epoch_ms": end_epoch_ms,
            "limit": effective_limit,
        },
        "scanned_rows": scanned,
        "match_count": len(matches),
        "matches": matches,
        "fusion_timeline_path": str(fusion_path),
    }


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
