"""系统设置路由。"""
from fastapi import APIRouter, Depends

from app.core.deps import get_current_user, require_admin
from app.core.response import ok
from app.schemas import SettingsUpdate
from app.services.platform import SettingsService

router = APIRouter(prefix="/settings", tags=["系统设置"])
settings_service = SettingsService()


@router.get("")
def get_settings(_user: dict = Depends(get_current_user)):
    return ok(settings_service.get())


@router.put("")
def update_settings(body: SettingsUpdate, _admin: dict = Depends(require_admin)):
    return ok(settings_service.update(body.model_dump(by_alias=True, exclude_unset=True)))
