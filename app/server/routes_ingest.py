from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.server.session_store import save_session
from app.server.state import SESSIONS, key

router = APIRouter(prefix="/api/upload", tags=["ingest"])


@router.post("/part")
async def upload_part(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    session_id: str = Form(...),
    operator_key: str = Form(...),
    part_index: int = Form(...),
):
    session_key = key(user_id, session_id)
    if session_key not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not started")

    target_dir = Path("workspace/uploads") / user_id / session_id
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"part_{part_index:02d}_usr_{operator_key}.webm"
    target_path = target_dir / filename

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload")

    target_path.write_bytes(data)

    state = SESSIONS[session_key]
    state.parts_uploaded += 1
    state.updated_at = datetime.now(timezone.utc).isoformat()
    save_session(state)

    return {
        "status": "ok",
        "saved": str(target_path),
        "parts_uploaded": state.parts_uploaded,
    }
