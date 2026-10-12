"""工作台聚合路由。"""
from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user
from app.core.response import ok
from app.services.platform import DashboardService

router = APIRouter(prefix="/dashboard", tags=["工作台"])
dashboard_service = DashboardService()


@router.get("/summary")
def summary(_user: dict = Depends(get_current_user)):
    """四卡片：学员 / 教师 / 班级 / 收入。"""
    return ok(dashboard_service.summary())


@router.get("/heat")
def heat(limit: int = Query(5, ge=1, le=20), _user: dict = Depends(get_current_user)):
    """班级报名热度（进行中班级，按报名人数降序）。"""
    return ok(dashboard_service.heat(limit))


@router.get("/recent-classes")
def recent_classes(limit: int = Query(4, ge=1, le=20), _user: dict = Depends(get_current_user)):
    """非已结课班级，按开班日期升序。"""
    return ok(dashboard_service.recent_classes(limit))


@router.get("/recent-payments")
def recent_payments(limit: int = Query(6, ge=1, le=50), _user: dict = Depends(get_current_user)):
    """最新缴费动态，按日期倒序。"""
    return ok(dashboard_service.recent_payments(limit))
