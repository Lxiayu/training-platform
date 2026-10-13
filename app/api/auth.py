"""认证路由。"""
from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.core.response import ok
from app.schemas import ChangePasswordRequest, LoginRequest, ProfileUpdate
from app.services.people import AuthService, AccountContextService, public_user

router = APIRouter(tags=["认证"])
auth_service = AuthService()
context_service = AccountContextService()


@router.post("/auth/login")
def login(body: LoginRequest):
    return ok(auth_service.login(body.username, body.password))


@router.get("/auth/me")
def me(user: dict = Depends(get_current_user)):
    return ok(public_user(user))


@router.get("/auth/context")
def context(user: dict = Depends(get_current_user)):
    """身份专属工作台数据：按 staff / teacher / student / parent 返回不同内容。"""
    return ok(context_service.build(user))


@router.put("/auth/profile")
def update_profile(body: ProfileUpdate, user: dict = Depends(get_current_user)):
    return ok(auth_service.update_profile(user, body.model_dump(by_alias=True)), "个人信息已保存")


@router.put("/auth/password")
def change_password(body: ChangePasswordRequest, user: dict = Depends(get_current_user)):
    auth_service.change_password(user, body.old_password, body.new_password)
    return ok(None, "密码修改成功，下次登录请使用新密码")
