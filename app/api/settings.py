"""系统设置路由。"""
from fastapi import APIRouter, Depends

from app.core.deps import require_admin, require_staff
from app.core.response import ok
from app.schemas import SettingsUpdate
from app.services.platform import SettingsService

router = APIRouter(prefix="/settings", tags=["系统设置"])
settings_service = SettingsService()


@router.get("")
def get_settings(_user: dict = Depends(require_staff)):
    """机构信息与业务开关仅员工可读（后台页面展示用）；学员 / 教师 / 家长 403。"""
    return ok(settings_service.get())


@router.put("")
def update_settings(body: SettingsUpdate, _admin: dict = Depends(require_admin)):
    return ok(settings_service.update(body.model_dump(by_alias=True, exclude_unset=True)))


@router.post("/reset")
def reset_demo_data(_admin: dict = Depends(require_admin)):
    """一键重置演示数据：全部业务数据回到初始种子状态。"""
    return ok(settings_service.reset(), "演示数据已重置为初始状态")
