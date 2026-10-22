"""课件资源路由。"""
from fastapi import APIRouter, Depends

from app.core.config import ROLE_ADMIN, ROLE_ACADEMIC, ROLE_TEACHER
from app.core.deps import get_current_user, require_roles
from app.core.response import ok
from app.api.pagination import Pagination
from app.schemas import ResourceCreate, ResourceUpdate
from app.services.content import ResourceService

router = APIRouter(prefix="/resources", tags=["课件资源"])
resource_service = ResourceService()


@router.get("")
def list_resources(
    p: Pagination = Depends(),
    keyword: str | None = None,
    type: str | None = None,
    courseId: str | None = None,
    teacherId: str | None = None,
    status: str | None = None,
    _user: dict = Depends(get_current_user),
):
    return ok(resource_service.list(
        keyword=keyword, type_=type, course_id=courseId, teacher_id=teacherId, status=status,
        page=p.page, page_size=p.page_size,
    ))


@router.get("/{code}")
def get_resource(code: str, _user: dict = Depends(get_current_user)):
    return ok(resource_service.get(code))


@router.post("")
def create_resource(body: ResourceCreate, _user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_ACADEMIC, ROLE_TEACHER))):
    return ok(resource_service.create(body.model_dump(by_alias=True)))


@router.put("/{code}")
def update_resource(code: str, body: ResourceUpdate, _user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_ACADEMIC, ROLE_TEACHER))):
    return ok(resource_service.update(code, body.model_dump(by_alias=True, exclude_unset=True)))


@router.delete("/{code}")
def delete_resource(code: str, _user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_ACADEMIC, ROLE_TEACHER))):
    resource_service.delete(code)
    return ok(None, "删除成功")


@router.post("/{code}/download")
def download_resource(code: str, _user: dict = Depends(get_current_user)):
    """下载计数 +1（原型阶段不返回真实文件）。"""
    return ok(resource_service.download(code))
