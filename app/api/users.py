"""用户管理路由（仅超级管理员）。"""
from fastapi import APIRouter, Depends

from app.core.deps import require_admin
from app.core.response import ok
from app.api.pagination import Pagination
from app.schemas import UserCreate, UserUpdate
from app.services.people import UserService

router = APIRouter(prefix="/users", tags=["用户管理"])
user_service = UserService()


@router.get("")
def list_users(
    p: Pagination = Depends(),
    keyword: str | None = None,
    role: str | None = None,
    status: str | None = None,
    _admin: dict = Depends(require_admin),
):
    return ok(user_service.list(
        keyword=keyword, role=role, status=status, page=p.page, page_size=p.page_size
    ))


@router.get("/{username}")
def get_user(username: str, _admin: dict = Depends(require_admin)):
    return ok(user_service.get(username))


@router.post("")
def create_user(body: UserCreate, _admin: dict = Depends(require_admin)):
    return ok(user_service.create(body.model_dump(by_alias=True)))


@router.put("/{username}")
def update_user(username: str, body: UserUpdate, admin: dict = Depends(require_admin)):
    return ok(user_service.update(
        username, body.model_dump(by_alias=True, exclude_unset=True), current=admin
    ))


@router.delete("/{username}")
def delete_user(username: str, admin: dict = Depends(require_admin)):
    user_service.delete(username, current=admin)
    return ok(None, "删除成功")


@router.post("/{username}/reset-password")
def reset_password(username: str, _admin: dict = Depends(require_admin)):
    password = user_service.reset_password(username)
    return ok({"initialPassword": password}, f"密码已重置为 {password}")
