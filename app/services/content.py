"""内容管理：新闻中心 / 课件资源。"""
from typing import Any

from app.db.jsondb import db, now_iso
from app.services.base import CrudService, today


class NewsService(CrudService):
    coll = "news"
    prefix = "XW"
    label = "新闻"
    search_fields = ("id", "title", "summary", "author")
    default_order = "date"          # 置顶优先 + 日期倒序（见 _sort 覆盖）

    def _sort(self, rows: list[dict], field: str) -> list[dict]:
        if field != "date":
            return super()._sort(rows, field)
        # 置顶优先，其余按发布日期倒序（两次稳定排序实现）
        rows = sorted(rows, key=lambda r: str(r.get("date") or ""), reverse=True)
        return sorted(rows, key=lambda r: not bool(r.get("top")))

    def list(self, *, category: str | None = None, **kwargs) -> dict:
        return super().list(extra_filters={"category": category} if category else None, **kwargs)

    def create(self, data: dict[str, Any], *, author: str | None = None) -> dict:
        data = {**data}
        if not data.get("author"):
            data["author"] = author or "管理员"
        if not data.get("date"):
            data["date"] = today()
        data["views"] = 0
        return super().create(data)

    def view(self, code: str) -> dict:
        """阅读计数 +1（原子递增）。"""
        rec = db.locate("news", code, label="新闻")
        return db.update_fields(
            "news", code,
            {"views": int(rec.get("views") or 0) + 1, "updatedAt": now_iso()},
            label="新闻",
        )


class ResourceService(CrudService):
    coll = "resources"
    prefix = "ZY"
    label = "课件资源"
    search_fields = ("id", "title", "type")

    def list(
        self,
        *,
        type_: str | None = None,
        course_id: str | None = None,
        teacher_id: str | None = None,
        **kwargs,
    ) -> dict:
        return super().list(
            extra_filters={"type": type_, "courseId": course_id, "teacherId": teacher_id},
            **kwargs,
        )

    def create(self, data: dict[str, Any]) -> dict:
        db.locate("courses", data.get("courseId") or "", label="课程")
        db.locate("teachers", data.get("teacherId") or "", label="教师")
        data = {**data}
        if not data.get("date"):
            data["date"] = today()
        data.setdefault("downloads", 0)
        return super().create(data)

    def download(self, code: str) -> dict:
        """下载计数 +1（原子递增）。"""
        rec = db.locate("resources", code, label="课件资源")
        return db.update_fields(
            "resources", code,
            {"downloads": int(rec.get("downloads") or 0) + 1, "updatedAt": now_iso()},
            label="课件资源",
        )
