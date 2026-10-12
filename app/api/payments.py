"""缴费管理路由（含统计与状态流转）。"""
from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.core.response import ok
from app.api.pagination import Pagination
from app.schemas import PaymentCreate, PaymentUpdate
from app.services.finance import PaymentService

router = APIRouter(prefix="/payments", tags=["缴费管理"])
payment_service = PaymentService()


@router.get("/stats")
def payment_stats(_user: dict = Depends(get_current_user)):
    return ok(payment_service.stats())


@router.get("")
def list_payments(
    p: Pagination = Depends(),
    keyword: str | None = None,
    studentId: str | None = None,
    classId: str | None = None,
    method: str | None = None,
    status: str | None = None,
    _user: dict = Depends(get_current_user),
):
    return ok(payment_service.list(
        keyword=keyword, student_id=studentId, class_id=classId, method=method, status=status,
        page=p.page, page_size=p.page_size,
    ))


@router.get("/{code}")
def get_payment(code: str, _user: dict = Depends(get_current_user)):
    return ok(payment_service.get(code))


@router.post("")
def create_payment(body: PaymentCreate, _user: dict = Depends(get_current_user)):
    return ok(payment_service.create(body.model_dump(by_alias=True)))


@router.put("/{code}")
def update_payment(code: str, body: PaymentUpdate, _user: dict = Depends(get_current_user)):
    return ok(payment_service.update(code, body.model_dump(by_alias=True, exclude_unset=True)))


@router.delete("/{code}")
def delete_payment(code: str, _user: dict = Depends(get_current_user)):
    payment_service.delete(code)
    return ok(None, "删除成功")


@router.post("/{code}/confirm")
def confirm_payment(code: str, _user: dict = Depends(get_current_user)):
    return ok(payment_service.confirm(code), "确认收款成功")


@router.post("/{code}/void")
def void_payment(code: str, _user: dict = Depends(get_current_user)):
    return ok(payment_service.void(code), "作废成功")
