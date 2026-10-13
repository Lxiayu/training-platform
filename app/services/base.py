"""通用 CRUD 服务基类：列表筛选 / 排序 / 分页 / 取号 / 软删。

字段约定：service 层直接使用前端 camelCase 键（与 JSON 存储一致），
路由层负责 Pydantic 模型 -> dict(by_alias=True) 的转换。
"""
from __future__ import annotations

from datetime import date
from typing import Any

from app.core.exceptions import BizException
from app.core.config import now_iso
from app.db.repository import db


def today() -> str:
    return date.today().isoformat()


class CrudService:
    coll: str = ""                 # 集合名
    prefix: str = ""               # 编号前缀（users 以 username 为主键，留空）
    label: str = "记录"             # 404 / 409 提示文案
    search_fields: tuple[str, ...] = ()   # keyword 模糊匹配字段
    default_order: str = ""        # 默认排序字段（空 = 保持插入序）

    # ---------- 查询 ----------

    def list(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        extra_filters: dict[str, Any] | None = None,
        order_by: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        rows = db.alive(self.coll)
        filters = dict(extra_filters or {})
        if status:
            filters["status"] = status
        for key, value in filters.items():
            if value not in (None, "", "全部"):
                rows = [r for r in rows if str(r.get(key)) == str(value)]
        if keyword and keyword.strip():
            kw = keyword.strip().lower()
            rows = [r for r in rows if self._match(r, kw)]
        rows = self._sort(rows, order_by or self.default_order)
        total = len(rows)
        start = (page - 1) * page_size
        return {
            "list": [self.decorate(r) for r in rows[start:start + page_size]],
            "total": total,
            "page": page,
            "pageSize": page_size,
        }

    def decorate(self, row: dict) -> dict:
        """输出前加工：子类覆盖以附加派生字段（enrolled、关联名等）。"""
        return row

    def _match(self, row: dict, kw: str) -> bool:
        """关键词匹配（已 lower）：默认按 search_fields 模糊包含。子类可扩展关联字段。"""
        return any(kw in str(row.get(f) or "").lower() for f in self.search_fields)

    def _sort(self, rows: list[dict], field: str) -> list[dict]:
        if not field:
            return rows
        return sorted(rows, key=lambda r: str(r.get(field) or ""))

    def get(self, code: str) -> dict:
        return self.decorate(db.locate(self.coll, code, label=self.label))

    # ---------- 写入 ----------

    def create(self, data: dict[str, Any]) -> dict:
        record = {k: v for k, v in data.items()}
        if self.prefix:
            record["id"] = db.next_code(self.coll, self.prefix)
        ts = now_iso()
        record.setdefault("createdAt", ts)
        record["updatedAt"] = ts
        db.insert(self.coll, record)
        return self.decorate(record)

    def update(self, code: str, data: dict[str, Any]) -> dict:
        fields = {k: v for k, v in data.items() if v is not None}
        if not fields:
            raise BizException(400, "没有需要更新的字段")
        fields["updatedAt"] = now_iso()
        rec = db.update_fields(self.coll, code, fields, label=self.label)
        return self.decorate(rec)

    def delete(self, code: str) -> None:
        self._before_delete(code)
        db.soft_delete(self.coll, code, label=self.label)

    def _before_delete(self, code: str) -> None:
        """删除保护钩子：子类覆盖以实现引用校验。"""
