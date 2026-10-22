"""请求依赖：当前登录用户与角色 / 身份校验。

前端接入时只需在请求头携带 ``Authorization: Bearer <token>``。

- ``get_current_user``：解析 token -> 账户（含 identity / role / refId）；
- ``require_admin``：仅超级管理员可过（用户管理 / 系统设置）；
- ``require_roles``：员工内部细粒度角色门禁（《02-总体设计》§4.3 权限矩阵）；
- ``require_identity``：按登录身份门禁，用于教师 / 学员 / 家长专属接口。
"""
from typing import Any

from fastapi import Depends, Header

from app.core.config import (
    IDENTITY_STAFF,
    IDENTITIES,
    ROLE_ADMIN,
    ROLE_ACADEMIC,
    ROLE_FINANCE,
    ROLE_FRONTDESK,
    ROLE_TEACHER,
)
from app.core.exceptions import BizException
from app.core.security import parse_token
from app.db.repository import db


def get_current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise BizException(401, "未登录或缺少令牌")
    username = parse_token(authorization[7:])
    if username is None:
        raise BizException(401, "登录已过期，请重新登录")
    user = db.find("users", username)
    if user is None:
        raise BizException(401, "账号不存在或已被删除")
    if user.get("status") != "启用":
        raise BizException(403, "账号已被禁用，请联系管理员")
    return user


def require_admin(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if user.get("role") != ROLE_ADMIN:
        raise BizException(403, "无权限执行该操作，需要超级管理员身份")
    return user


def require_staff(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """后台员工（含教务 / 财务 / 前台等非管理员）可访问运营后台；教师 / 学员 / 家长走各自 portal。"""
    if user.get("identity") != IDENTITY_STAFF:
        raise BizException(403, "无权限访问后台，请使用员工账号登录")
    return user


def require_roles(*roles: str):
    """角色门禁工厂（《02-总体设计》§4.3 权限矩阵），返回依赖函数，两道闸门：

    1. 身份闸门：非 staff（教师 / 学员 / 家长门户账号）一律 403 —— 防止低权限身份
       直接调用后台写接口提权；
    2. 角色闸门：员工职务（role）必须在允许集合内，否则 403。
       传空 roles 表示仅要求员工身份（与 require_staff 等价）。

    用法：``Depends(require_roles(ROLE_ADMIN, ROLE_ACADEMIC))``。
    """
    def checker(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        if user.get("identity") != IDENTITY_STAFF:
            raise BizException(403, "无权限访问后台，请使用员工账号登录")
        if roles and user.get("role") not in roles:
            raise BizException(403, f"无权限执行该操作，需要「{' / '.join(roles)}」权限")
        return user

    return checker


def require_identity(
    *identities: str, user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    """按登录身份门禁；不传参数表示任意已登录身份均可。"""
    if identities and user.get("identity") not in identities:
        names = {
            "staff": "后台员工",
            "teacher": "教师",
            "student": "学员",
            "parent": "家长",
        }
        allowed = " / ".join(names.get(i, i) for i in identities)
        raise BizException(403, f"本接口仅限「{allowed}」访问")
    return user


# 身份绑定的便捷门禁（供路由 ``Depends(require_teacher)`` 直接使用）
def require_teacher(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return require_identity("teacher", user=user)


def require_student(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return require_identity("student", user=user)


def require_parent(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return require_identity("parent", user=user)
