from fastapi import APIRouter, Header

from app.security.auth import complete_google_oauth, get_current_user, issue_oauth_state
from app.security.oauth_google import build_google_authorize_url, resolve_google_identity_from_code
from app.server.schemas_auth import OAuthCodeCallbackRequest, OAuthStartRequest

router = APIRouter(prefix="/api/auth/oauth/google", tags=["auth"])


@router.post("/start")
async def oauth_google_start(payload: OAuthStartRequest, authorization: str | None = Header(default=None)):
    mode = "link" if payload.link_account else "login"
    owner = None
    if payload.link_account:
        owner = get_current_user(authorization)
    state = issue_oauth_state(mode=mode, email=owner["email"] if owner else None)
    return {
        "status": "ok",
        "provider": "google",
        "mode": mode,
        "state": state,
        "authorize_url": build_google_authorize_url(state),
    }


@router.post("/callback")
async def oauth_google_callback(payload: OAuthCodeCallbackRequest):
    identity = resolve_google_identity_from_code(payload.code)
    return complete_google_oauth(
        state=payload.state,
        code=payload.code,
        google_sub=str(identity["sub"]),
        google_email=str(identity["email"]),
    )
