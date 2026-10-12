"""班级管理路由。"""
from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.core.response import ok
from app.api.pagination import Pagination
from app.schemas import ClassCreate, ClassUpdate
from app.services.education import ClassService

router = APIRouter(prefix="/classes", tags=["班级管理"])
class_service = ClassService()


@router.get("")
def list_classes(
    p: Pagination = Depends(),
    keyword: str | None = None,
    courseId: str | None = None,
    teacherId: str | None = None,
    status: str | None = None,
    _user: dict = Depends(get_current_user),
):
    return ok(class_service.list(
        keyword=keyword, course_id=courseId, teacher_id=teacherId, status=status,
        page=p.page, page_size=p.page_size,
    ))


@router.get("/{code}")
def get_class(code: str, _user: dict = Depends(get_current_user)):
    return ok(class_service.get(code))


@router.post("")
def create_class(body: ClassCreate, _user: dict = Depends(get_current_user)):
    return ok(class_service.create(body.model_dump(by_alias=True)))


@router.put("/{code}")
def update_class(code: str, body: ClassUpdate, _user: dict = Depends(get_current_user)):
    return ok(class_service.update(code, body.model_dump(by_alias=True, exclude_unset=True)))


@router.delete("/{code}")
def delete_class(code: str, _user: dict = Depends(get_current_user)):
    class_service.delete(code)
    return ok(None, "删除成功")
