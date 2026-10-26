"""排课规则与课次管理路由（后台）。

- 读：员工（含教务 / 财务 / 前台）可查看班级排课与课次；
- 写：仅超级管理员 / 教务管理员；
- 课次生成、取消、调课均由服务层校验业务规则（已上课不可改等）。
"""
from datetime import date

from fastapi import APIRouter, Depends, Query

from app.core.config import ROLE_ACADEMIC, ROLE_ADMIN
from app.core.deps import require_roles, require_staff
from app.core.exceptions import BizException
from app.core.response import ok
from app.schemas import (
    ScheduleCreate,
    ScheduleUpdate,
    SessionGenerate,
    SessionReschedule,
    SessionUpdate,
)
from app.services.schedule import ScheduleService

router = APIRouter(tags=["排课与课次"])
schedule_service = ScheduleService()


def _date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise BizException(400, "日期格式应为 YYYY-MM-DD")


# ---------- 员工课表（跨班级周视图） ----------

@router.get("/sessions")
def list_all_sessions(
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    classId: str | None = Query(default=None),
    teacherId: str | None = Query(default=None),
    _user: dict = Depends(require_staff),
):
    return ok(schedule_service.list_all(
        date_from=start, date_to=end, class_id=classId, teacher_id=teacherId,
    ))


@router.post("/sessions/generate")
def generate_sessions_for_class(
    body: SessionGenerate,
    _user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_ACADEMIC)),
):
    """兼容「班级 + 起始日」的补课次入口。"""
    if not body.class_id:
        raise BizException(400, "请选择班级")
    return ok(schedule_service.generate(
        body.class_id, start=_date(body.from_date), end=_date(body.date_to),
    ), "课次已生成")


@router.put("/sessions/{session_id}")
def update_session(
    session_id: str,
    body: SessionUpdate,
    _user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_ACADEMIC)),
):
    """维护课次主题 / 状态 / 教室；调课请使用 /reschedule 保留原时间。"""
    return ok(
        schedule_service.update_session(
            session_id, body.model_dump(by_alias=True, exclude_unset=True)
        ),
        "课次已更新",
    )


# ---------- 排课规则 ----------

@router.get("/classes/{code}/schedules")
def list_schedules(code: str, _user: dict = Depends(require_staff)):
    return ok(schedule_service.list_rules(code))


@router.post("/classes/{code}/schedules")
def create_schedule(
    code: str,
    body: ScheduleCreate,
    _user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_ACADEMIC)),
):
    return ok(schedule_service.create_rule(code, body.model_dump(by_alias=True)), "排课规则已保存")


@router.put("/schedules/{rule_id}")
def update_schedule(
    rule_id: str,
    body: ScheduleUpdate,
    _user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_ACADEMIC)),
):
    return ok(
        schedule_service.update_rule(rule_id, body.model_dump(by_alias=True, exclude_unset=True)),
        "排课规则已更新",
    )


@router.delete("/schedules/{rule_id}")
def delete_schedule(
    rule_id: str,
    _user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_ACADEMIC)),
):
    schedule_service.delete_rule(rule_id)
    return ok(None, "排课规则已删除")


# ---------- 课次 ----------

@router.get("/classes/{code}/sessions")
def list_sessions(
    code: str,
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    _user: dict = Depends(require_staff),
):
    return ok(schedule_service.sessions(code, date_from=from_, date_to=to))


@router.post("/classes/{code}/sessions/generate")
def generate_sessions(
    code: str,
    body: SessionGenerate | None = None,
    _user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_ACADEMIC)),
):
    """按当前规则补齐课次（幂等；不删除已有课次）。"""
    payload = body or SessionGenerate()
    return ok(
        schedule_service.generate(
            code, start=_date(payload.date_from), end=_date(payload.date_to),
        ),
        "课次已生成",
    )


@router.post("/sessions/{session_id}/cancel")
def cancel_session(
    session_id: str,
    _user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_ACADEMIC)),
):
    return ok(schedule_service.cancel(session_id), "课次已取消")


@router.post("/sessions/{session_id}/reschedule")
def reschedule_session(
    session_id: str,
    body: SessionReschedule,
    _user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_ACADEMIC)),
):
    return ok(
        schedule_service.reschedule(session_id, body.model_dump(by_alias=True)),
        "调课成功",
    )
