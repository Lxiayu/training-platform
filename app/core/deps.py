"""请求依赖：当前登录用户与角色校验。

前端将来接入时只需在请求头携带 ``Authorization: Bearer <token>``。
"""
from typing import Any

from fastapi import Depends, Header

from app.core.exceptions import BizException
from app.core.security import parse_token
from app.db.jsondb import db


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
    if user.get("role") != "超级管理员":
        raise BizException(403, "无权限执行该操作，需要超级管理员身份")
    return user
