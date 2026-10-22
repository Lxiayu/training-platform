"""作业管理与考勤管理路由（教师 / 学员 / 家长三类门户）。

所有端点均按登录身份做服务端门禁：
- ``require_teacher``：布置/维护作业、查看提交、批改、录入考勤；
- ``require_student``：查看并提交本班作业、查看本人考勤；
- ``require_parent``：查看关联学员的作业批改与考勤。
"""
from fastapi import APIRouter, Depends, Query

from app.core.deps import require_parent, require_student, require_teacher
from app.core.response import ok
from app.schemas import AssignmentCreate, AssignmentUpdate, AttendanceSave, GradeRequest, SubmissionCreate
from app.services.teaching import AssignmentService, AttendanceService

router = APIRouter(prefix="/portal", tags=["作业与考勤"])
assignment_service = AssignmentService()
attendance_service = AttendanceService()


# ---------- 教师：作业 ----------

@router.get("/teacher/assignments")
def teacher_assignments(
    classId: str | None = Query(default=None),
    user: dict = Depends(require_teacher),
):
    return ok(assignment_service.list_for_teacher(user["refId"], classId))


@router.post("/teacher/assignments")
def create_assignment(body: AssignmentCreate, user: dict = Depends(require_teacher)):
    return ok(assignment_service.create(user["refId"], body.model_dump(by_alias=True)))


@router.put("/teacher/assignments/{code}")
def update_assignment(code: str, body: AssignmentUpdate, user: dict = Depends(require_teacher)):
    return ok(assignment_service.update(
        user["refId"], code, body.model_dump(by_alias=True, exclude_unset=True)
    ))


@router.delete("/teacher/assignments/{code}")
def delete_assignment(code: str, user: dict = Depends(require_teacher)):
    assignment_service.delete(user["refId"], code)
    return ok(None, "作业已删除")


@router.get("/teacher/assignments/{code}/submissions")
def assignment_submissions(code: str, user: dict = Depends(require_teacher)):
    return ok(assignment_service.submissions(user["refId"], code))


@router.post("/teacher/submissions/{code}/grade")
def grade_submission(code: str, body: GradeRequest, user: dict = Depends(require_teacher)):
    return ok(assignment_service.grade(user["refId"], code, body.score, body.comment), "批改成功")


# ---------- 教师：考勤 ----------

@router.get("/teacher/attendance")
def teacher_attendance(
    classId: str = Query(...),
    date: str = Query(...),
    user: dict = Depends(require_teacher),
):
    return ok(attendance_service.roster(user["refId"], classId, date))


@router.post("/teacher/attendance")
def save_attendance(body: AttendanceSave, user: dict = Depends(require_teacher)):
    items = [item.model_dump(by_alias=True) for item in body.items]
    return ok(attendance_service.save(user["refId"], body.class_id, body.date, items), "考勤已保存")


# ---------- 学员 ----------

@router.get("/student/assignments")
def student_assignments(user: dict = Depends(require_student)):
    return ok(assignment_service.list_for_student(user["refId"]))


@router.post("/student/assignments/{code}/submit")
def submit_assignment(code: str, body: SubmissionCreate, user: dict = Depends(require_student)):
    return ok(assignment_service.submit(user["refId"], code, body.content), "作业已提交")


@router.get("/student/attendance")
def student_attendance(user: dict = Depends(require_student)):
    return ok(attendance_service.list_for_student(user["refId"]))


# ---------- 家长 ----------

@router.get("/parent/assignments")
def parent_assignments(
    studentId: str | None = Query(default=None),
    user: dict = Depends(require_parent),
):
    return ok(assignment_service.list_for_parent(user["refId"], studentId))


@router.get("/parent/attendance")
def parent_attendance(
    studentId: str | None = Query(default=None),
    user: dict = Depends(require_parent),
):
    return ok(attendance_service.list_for_parent(user["refId"], studentId))
