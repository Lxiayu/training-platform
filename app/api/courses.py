"""课程管理路由。"""
from fastapi import APIRouter, Depends

from app.core.deps import get_current_user, require_staff
from app.core.response import ok
from app.api.pagination import Pagination
from app.schemas import CourseCreate, CourseUpdate
from app.services.education import CourseService

router = APIRouter(prefix="/courses", tags=["课程管理"])
course_service = CourseService()


@router.get("")
def list_courses(
    p: Pagination = Depends(),
    keyword: str | None = None,
    category: str | None = None,
    level: str | None = None,
    status: str | None = None,
    _user: dict = Depends(require_staff),
):
    return ok(course_service.list(
        keyword=keyword, category=category, level=level, status=status,
        page=p.page, page_size=p.page_size,
    ))


@router.get("/{code}")
def get_course(code: str, _user: dict = Depends(require_staff)):
    return ok(course_service.get(code))


@router.post("")
def create_course(body: CourseCreate, _user: dict = Depends(require_staff)):
    return ok(course_service.create(body.model_dump(by_alias=True)))


@router.put("/{code}")
def update_course(code: str, body: CourseUpdate, _user: dict = Depends(require_staff)):
    return ok(course_service.update(code, body.model_dump(by_alias=True, exclude_unset=True)))


@router.delete("/{code}")
def delete_course(code: str, _user: dict = Depends(require_staff)):
    course_service.delete(code)
    return ok(None, "删除成功")
