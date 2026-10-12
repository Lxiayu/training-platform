"""认证 / 用户 / 教师 业务规则。"""
from typing import Any

from app.core.config import DEFAULT_USER_PASSWORD
from app.core.exceptions import BizException
from app.core.security import create_token, hash_password, verify_password
from app.db.jsondb import db, now_iso
from app.services.base import CrudService, today

ROLE_ADMIN = "超级管理员"


def public_user(user: dict) -> dict:
    """用户安全视图：剔除密码哈希与软删标记（任何响应不得泄漏）。"""
    return {k: v for k, v in user.items() if k not in ("passwordHash", "deletedAt")}


class AuthService:
    def login(self, username: str, password: str) -> dict:
        user = db.find("users", (username or "").strip())
        if user is None or not verify_password(password or "", user.get("passwordHash", "")):
            raise BizException(401, "账号或密码错误")
        if user.get("status") != "启用":
            raise BizException(403, "账号已被禁用，请联系管理员")
        return {"token": create_token(user["username"]), "user": public_user(user)}

    def change_password(self, user: dict, old_password: str, new_password: str) -> None:
        if not verify_password(old_password, user.get("passwordHash", "")):
            raise BizException(400, "原密码不正确")
        db.update_fields(
            "users", user["username"],
            {"passwordHash": hash_password(new_password), "updatedAt": now_iso()},
            label="用户",
        )

    def update_profile(self, user: dict, patch: dict) -> dict:
        """普通用户自助维护姓名 / 手机 / 邮箱（不能改角色与状态）。"""
        fields = {k: v for k, v in patch.items() if v is not None}
        if not fields:
            raise BizException(400, "没有需要更新的内容")
        fields["updatedAt"] = now_iso()
        rec = db.update_fields("users", user["username"], fields, label="用户")
        return public_user(rec)


class UserService(CrudService):
    coll = "users"
    label = "用户"
    search_fields = ("username", "name", "phone", "email")

    def list(self, *, role: str | None = None, **kwargs) -> dict:
        return super().list(extra_filters={"role": role} if role else None, **kwargs)

    def create(self, data: dict[str, Any]) -> dict:
        username = (data.get("username") or "").strip()
        if db.find("users", username):
            raise BizException(409, f"用户名「{username}」已存在")
        ts = now_iso()
        record = {
            "username": username,
            "passwordHash": hash_password(data.get("password") or DEFAULT_USER_PASSWORD),
            "name": data.get("name") or username,
            "role": data.get("role") or "教务管理员",
            "phone": data.get("phone") or "",
            "email": data.get("email") or None,
            "joinDate": data.get("joinDate") or today(),
            "status": data.get("status") or "启用",
            "createdAt": ts,
            "updatedAt": ts,
        }
        db.insert("users", record)
        return public_user(record)

    def update(self, code: str, data: dict[str, Any], *, current: dict | None = None) -> dict:
        target = db.locate("users", code, label="用户")
        fields = {k: v for k, v in data.items() if v is not None}
        if current and target["username"] == current.get("username") and fields.get("status") == "禁用":
            raise BizException(409, "不能禁用当前登录的账号")
        self._guard_admin_supply(target, fields)
        rec = super().update(code, fields)
        return public_user(rec)

    def delete(self, code: str, *, current: dict | None = None) -> None:
        target = db.locate("users", code, label="用户")
        if current and target["username"] == current.get("username"):
            raise BizException(409, "不能删除当前登录的账号")
        self._guard_admin_supply(target, {"status": "禁用"})
        db.soft_delete("users", code, label="用户")

    def reset_password(self, code: str) -> str:
        db.locate("users", code, label="用户")
        db.update_fields(
            "users", code,
            {"passwordHash": hash_password(DEFAULT_USER_PASSWORD), "updatedAt": now_iso()},
            label="用户",
        )
        return DEFAULT_USER_PASSWORD

    def _guard_admin_supply(self, target: dict, changes: dict) -> None:
        """删除 / 禁用 / 降级前，保证系统仍至少保留一个启用的超级管理员。"""
        if target.get("role") != ROLE_ADMIN or target.get("status") != "启用":
            return
        losing = changes.get("status") == "禁用" or (
            changes.get("role") is not None and changes["role"] != ROLE_ADMIN
        )
        if losing:
            admins = [u for u in db.alive("users")
                      if u.get("role") == ROLE_ADMIN and u.get("status") == "启用"]
            if len(admins) <= 1:
                raise BizException(409, "系统至少需保留一个启用的超级管理员")


class TeacherService(CrudService):
    coll = "teachers"
    prefix = "JS"
    label = "教师"
    search_fields = ("id", "name", "phone", "email", "subject", "title")

    def list(self, *, subject: str | None = None, **kwargs) -> dict:
        return super().list(extra_filters={"subject": subject} if subject else None, **kwargs)

    def _before_delete(self, code: str) -> None:
        used = [c for c in db.alive("classes") if c.get("teacherId") == code]
        if used:
            names = "、".join(c["name"] for c in used[:3]) + ("等" if len(used) > 3 else "")
            raise BizException(409, f"该教师仍负责 {len(used)} 个班级（{names}），请先调整班级任教教师")
