"""缴费业务：状态机（待确认 -> 已支付 / 已作废，已退款为终态）与统计。"""
from datetime import datetime
from typing import Any

from app.core.exceptions import BizException
from app.core.config import now_iso
from app.db.repository import db
from app.services.base import CrudService, today

STATUS_PENDING = "待确认"
STATUS_PAID = "已支付"
STATUS_REFUNDED = "已退款"
STATUS_VOIDED = "已作废"


class PaymentService(CrudService):
    coll = "payments"
    prefix = "JF"
    label = "缴费记录"
    search_fields = ("id", "note", "method")

    def _match(self, row: dict, kw: str) -> bool:
        """扩展：支持按学员姓名搜索（前端搜索框行为）。"""
        if super()._match(row, kw):
            return True
        student = db.find("students", row.get("studentId") or "")
        return bool(student and kw in str(student.get("name") or "").lower())

    def list(
        self,
        *,
        class_id: str | None = None,
        student_id: str | None = None,
        method: str | None = None,
        **kwargs,
    ) -> dict:
        return super().list(
            extra_filters={"classId": class_id, "studentId": student_id, "method": method},
            **kwargs,
        )

    def decorate(self, row: dict) -> dict:
        student = db.find("students", row.get("studentId") or "")
        cls = db.find("classes", row.get("classId") or "")
        course = db.find("courses", cls.get("courseId") or "") if cls else None
        return {
            **row,
            "studentName": student["name"] if student else "",
            "className": cls["name"] if cls else "",
            "courseName": course["name"] if course else "",
        }

    def create(self, data: dict[str, Any]) -> dict:
        db.locate("students", data.get("studentId") or "", label="学员")
        db.locate("classes", data.get("classId") or "", label="班级")
        data = {**data}
        if not data.get("date"):
            data["date"] = today()
        return super().create(data)

    def confirm(self, code: str) -> dict:
        """确认收款：仅「待确认」可流转为「已支付」。"""
        rec = db.locate("payments", code, label="缴费记录")
        if rec.get("status") != STATUS_PENDING:
            raise BizException(409, f"当前状态为「{rec.get('status')}」，只有待确认的缴费才能确认收款")
        return db.update_fields(
            "payments", code, {"status": STATUS_PAID, "updatedAt": now_iso()}, label="缴费记录"
        )

    def void(self, code: str) -> dict:
        """作废：待确认 / 已支付可作废；已退款、已作废为终态。"""
        rec = db.locate("payments", code, label="缴费记录")
        if rec.get("status") in (STATUS_REFUNDED, STATUS_VOIDED):
            raise BizException(409, f"该笔缴费已{rec.get('status')}，不能再作废")
        return db.update_fields(
            "payments", code, {"status": STATUS_VOIDED, "updatedAt": now_iso()}, label="缴费记录"
        )

    def stats(self) -> dict:
        """三卡片统计：本月收入 / 待确认 / 累计收入（仅「已支付」计入收入口径）。"""
        rows = db.alive("payments")
        paid = [p for p in rows if p.get("status") == STATUS_PAID]
        pending = [p for p in rows if p.get("status") == STATUS_PENDING]
        month_prefix = datetime.now().strftime("%Y-%m")
        month_paid = [p for p in paid if str(p.get("date") or "").startswith(month_prefix)]

        def _sum(items: list[dict]) -> float:
            return round(sum(float(p.get("amount") or 0) for p in items), 2)

        return {
            "monthIncome": _sum(month_paid),
            "monthCount": len(month_paid),
            "totalIncome": _sum(paid),
            "totalCount": len(paid),
            "pendingAmount": _sum(pending),
            "pendingCount": len(pending),
        }
