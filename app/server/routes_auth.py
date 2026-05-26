from fastapi import APIRouter, Depends, Header

from app.security.auth import (
    authenticate_user,
    complete_github_oauth,
    confirm_password_reset,
    create_user,
    get_current_user,
    issue_oauth_state,
    issue_access_token,
    request_password_reset,
)
from app.server.schemas_auth import (
    AuthLoginRequest,
    OAuthCallbackRequest,
    OAuthStartRequest,
    AuthSignupRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup")
async def signup(payload: AuthSignupRequest):
    user = create_user(payload.email, payload.password)
    token = issue_access_token(user["email"])
    return {"status": "ok", "email": user["email"], "access_token": token, "token_type": "bearer"}


@router.post("/login")
async def login(payload: AuthLoginRequest):
    user = authenticate_user(payload.email, payload.password)
    if not user:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=401,
            detail={"code": "auth_invalid_credentials", "message": "invalid email or password"},
        )
    token = issue_access_token(user["email"])
    return {"status": "ok", "access_token": token, "token_type": "bearer"}


@router.get("/me")
async def me(user=Depends(get_current_user)):
    return {"status": "ok", "email": user["email"]}


@router.post("/password-reset/request")
async def password_reset_request(payload: PasswordResetRequest):
    token = request_password_reset(payload.email)
    # V1 local/dev flow returns token directly; callers should not expose this in prod.
    return {"status": "ok", "reset_token": token}


@router.post("/password-reset/confirm")
async def password_reset_confirm(payload: PasswordResetConfirmRequest):
    email = confirm_password_reset(payload.token, payload.new_password)
    return {"status": "ok", "email": email}


@router.post("/oauth/github/start")
async def oauth_github_start(payload: OAuthStartRequest, authorization: str | None = Header(default=None)):
    mode = "link" if payload.link_account else "login"
    owner = None
    if payload.link_account:
        owner = get_current_user(authorization)
    state = issue_oauth_state(mode=mode, email=owner["email"] if owner else None)
    return {"status": "ok", "provider": "github", "mode": mode, "state": state}


@router.post("/oauth/github/callback")
async def oauth_github_callback(payload: OAuthCallbackRequest):
    return complete_github_oauth(
        state=payload.state,
        code=payload.code,
        github_user_id=payload.github_user_id,
        github_email=payload.github_email,
    )
