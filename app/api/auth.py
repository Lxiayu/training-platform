"""认证路由。"""
from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.core.response import ok
from app.schemas import ChangePasswordRequest, LoginRequest
from app.services.people import AuthService, public_user

router = APIRouter(tags=["认证"])
auth_service = AuthService()


@router.post("/auth/login")
def login(body: LoginRequest):
    return ok(auth_service.login(body.username, body.password))


@router.get("/auth/me")
def me(user: dict = Depends(get_current_user)):
    return ok(public_user(user))


@router.put("/auth/password")
def change_password(body: ChangePasswordRequest, user: dict = Depends(get_current_user)):
    auth_service.change_password(user, body.old_password, body.new_password)
    return ok(None, "密码修改成功，下次登录请使用新密码")
