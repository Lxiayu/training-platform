"""新闻中心路由。"""
from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.core.response import ok
from app.api.pagination import Pagination
from app.schemas import NewsCreate, NewsUpdate
from app.services.content import NewsService

router = APIRouter(prefix="/news", tags=["新闻中心"])
news_service = NewsService()


@router.get("")
def list_news(
    p: Pagination = Depends(),
    keyword: str | None = None,
    category: str | None = None,
    status: str | None = None,
    _user: dict = Depends(get_current_user),
):
    return ok(news_service.list(
        keyword=keyword, category=category, status=status, page=p.page, page_size=p.page_size
    ))


@router.get("/{code}")
def get_news(code: str, _user: dict = Depends(get_current_user)):
    return ok(news_service.get(code))


@router.post("")
def create_news(body: NewsCreate, user: dict = Depends(get_current_user)):
    return ok(news_service.create(body.model_dump(by_alias=True), author=user.get("name")))


@router.put("/{code}")
def update_news(code: str, body: NewsUpdate, _user: dict = Depends(get_current_user)):
    return ok(news_service.update(code, body.model_dump(by_alias=True, exclude_unset=True)))


@router.delete("/{code}")
def delete_news(code: str, _user: dict = Depends(get_current_user)):
    news_service.delete(code)
    return ok(None, "删除成功")


@router.post("/{code}/view")
def view_news(code: str, _user: dict = Depends(get_current_user)):
    """阅读计数 +1。"""
    return ok(news_service.view(code))
