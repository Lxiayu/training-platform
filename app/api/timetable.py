"""三端课表路由（教师 / 学员 / 家长）。

服务端按登录身份与归属关系解析数据范围：
- 教师只能看到自己所带班级的课次；
- 学员只能看到本班课次；
- 家长只能看到与本人关联学员的课次，越权返回 403。
"""
from fastapi import APIRouter, Depends, Query

from app.core.deps import require_parent, require_student, require_teacher
from app.core.response import ok
from app.schemas import SessionUpdate
from app.services.schedule import ScheduleService, TimetableService

router = APIRouter(prefix="/portal", tags=["课表"])
timetable_service = TimetableService()
schedule_service = ScheduleService()


@router.get("/teacher/timetable")
def teacher_timetable(
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    user: dict = Depends(require_teacher),
):
    return ok(timetable_service.for_teacher(user.get("refId") or "", from_, to))


@router.get("/teacher/sessions")
def teacher_sessions(
    classId: str | None = Query(default=None),
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    user: dict = Depends(require_teacher),
):
    """教师查看自己的课次：传 classId 只返回该班，缺省返回全部所带班级。"""
    return ok(schedule_service.teacher_sessions(
        user.get("refId") or "", classId, date_from=from_, date_to=to,
    ))


@router.put("/teacher/sessions/{code}")
def teacher_update_session(
    code: str,
    body: SessionUpdate,
    user: dict = Depends(require_teacher),
):
    """教师维护本人班级课次的主题 / 状态（日期时间由教务统一调整）。"""
    data = body.model_dump(by_alias=True, exclude_unset=True)
    data = {k: v for k, v in data.items() if k in ("topic", "status")}
    return ok(
        schedule_service.update_session(code, data, teacher_code=user.get("refId")),
        "课次已更新",
    )


@router.get("/student/timetable")
def student_timetable(
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    user: dict = Depends(require_student),
):
    return ok(timetable_service.for_student(user.get("refId") or "", from_, to))


@router.get("/parent/{student_id}/timetable")
def parent_timetable(
    student_id: str,
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    user: dict = Depends(require_parent),
):
    return ok(timetable_service.for_parent(
        user.get("refId") or "", student_id, from_, to,
    ))
