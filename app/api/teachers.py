"""教师管理路由。"""
from fastapi import APIRouter, Depends

from app.core.deps import get_current_user, require_staff
from app.core.response import ok
from app.api.pagination import Pagination
from app.schemas import TeacherCreate, TeacherUpdate
from app.services.people import TeacherService

router = APIRouter(prefix="/teachers", tags=["教师管理"])
teacher_service = TeacherService()


@router.get("")
def list_teachers(
    p: Pagination = Depends(),
    keyword: str | None = None,
    subject: str | None = None,
    status: str | None = None,
    _user: dict = Depends(require_staff),
):
    return ok(teacher_service.list(
        keyword=keyword, subject=subject, status=status, page=p.page, page_size=p.page_size
    ))


@router.get("/{code}")
def get_teacher(code: str, _user: dict = Depends(require_staff)):
    return ok(teacher_service.get(code))


@router.post("")
def create_teacher(body: TeacherCreate, _user: dict = Depends(require_staff)):
    return ok(teacher_service.create(body.model_dump(by_alias=True)))


@router.put("/{code}")
def update_teacher(code: str, body: TeacherUpdate, _user: dict = Depends(require_staff)):
    return ok(teacher_service.update(code, body.model_dump(by_alias=True, exclude_unset=True)))


@router.delete("/{code}")
def delete_teacher(code: str, _user: dict = Depends(require_staff)):
    teacher_service.delete(code)
    return ok(None, "删除成功")
