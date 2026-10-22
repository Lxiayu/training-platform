"""身份门户路由：教师 / 学员 / 家长专属数据（服务端身份门禁）。

- ``/portal/overview``：任意登录身份可获取自己的专属工作台（数据按登录身份隔离）；
- ``/portal/teacher/classes``：仅「教师」可访问，越权返回 403；
- ``/portal/student/profile``：仅「学员」可访问；
- ``/portal/student/payments``：仅「学员」可访问，返回本人账单 / 流水 / 汇总；
- ``/portal/parent/children``：仅「家长」可访问；
- ``/portal/parent/{student_id}/payments``：仅「家长」可访问，且只能查看关联学员。

这些端点复用 ``AccountContextService.build``，确保与 ``/auth/context`` 一致，
并通过 ``require_identity`` 在路由层显式落地「不同身份区分」。
"""
from fastapi import APIRouter, Depends

from app.core.deps import get_current_user, require_teacher, require_student, require_parent
from app.core.response import ok
from app.db.repository import db
from app.services.finance import BillService
from app.services.people import AccountContextService

router = APIRouter(prefix="/portal", tags=["身份门户"])
context_service = AccountContextService()
bill_service = BillService()


@router.get("/overview")
def overview(user: dict = Depends(get_current_user)):
    """当前登录身份的工作台总览（员工 / 教师 / 学员 / 家长各自不同）。"""
    return ok(context_service.build(user))


@router.get("/teacher/classes")
def teacher_classes(user: dict = Depends(require_teacher)):
    """教师门户：所带班级与学员概况。"""
    return ok(context_service.build(user).get("classes", []))


@router.get("/student/profile")
def student_profile(user: dict = Depends(require_student)):
    """学员门户：我的班级 / 课程 / 教师 / 已缴费用。"""
    return ok(context_service.build(user))


@router.get("/student/payments")
def student_payments(user: dict = Depends(require_student)):
    """学员门户：我的缴费详情（应缴 / 已缴 / 待确认 / 欠费 + 账单 + 流水）。"""
    student = db.locate("students", user.get("refId") or "", label="学员")
    return ok(bill_service.student_payload(student))


@router.get("/parent/children")
def parent_children(user: dict = Depends(require_parent)):
    """家长门户：关联学员动态。"""
    return ok(context_service.build(user).get("children", []))


@router.get("/parent/{student_id}/payments")
def parent_payments(student_id: str, user: dict = Depends(require_parent)):
    """家长门户：孩子的缴费详情（只能查看与本人关联的学员，越权 403）。"""
    return ok(bill_service.parent_payload(user.get("refId") or "", student_id))
