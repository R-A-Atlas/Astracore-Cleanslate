from fastapi import APIRouter, Depends

from app.core.user_settings_store import get_user_settings, put_user_settings
from app.security.auth import get_current_user
from app.server.schemas_settings import UserSettingsV1

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/me", response_model=UserSettingsV1)
async def get_my_settings(user=Depends(get_current_user)):
    return get_user_settings(user["email"])


@router.put("/me", response_model=UserSettingsV1)
async def put_my_settings(payload: UserSettingsV1, user=Depends(get_current_user)):
    return put_user_settings(user["email"], payload.model_dump())
