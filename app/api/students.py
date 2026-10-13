"""学员管理路由。"""
from fastapi import APIRouter, Depends

from app.core.deps import get_current_user, require_staff
from app.core.response import ok
from app.api.pagination import Pagination
from app.schemas import StudentCreate, StudentUpdate
from app.services.education import StudentService

router = APIRouter(prefix="/students", tags=["学员管理"])
student_service = StudentService()


@router.get("")
def list_students(
    p: Pagination = Depends(),
    keyword: str | None = None,
    classId: str | None = None,
    status: str | None = None,
    _user: dict = Depends(require_staff),
):
    return ok(student_service.list(
        keyword=keyword, class_id=classId, status=status, page=p.page, page_size=p.page_size
    ))


@router.get("/{code}")
def get_student(code: str, _user: dict = Depends(require_staff)):
    return ok(student_service.get(code))


@router.post("")
def create_student(body: StudentCreate, _user: dict = Depends(require_staff)):
    return ok(student_service.create(body.model_dump(by_alias=True)))


@router.put("/{code}")
def update_student(code: str, body: StudentUpdate, _user: dict = Depends(require_staff)):
    return ok(student_service.update(code, body.model_dump(by_alias=True, exclude_unset=True)))


@router.delete("/{code}")
def delete_student(code: str, _user: dict = Depends(require_staff)):
    student_service.delete(code)
    return ok(None, "删除成功（其名下缴费记录已一并归档）")
