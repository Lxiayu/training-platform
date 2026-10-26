"""课程 / 班级 / 学员 业务规则（含级联删除）。"""
from typing import Any

from app.core.exceptions import BizException
from app.db.repository import db
from app.services.base import CrudService, today


class CourseService(CrudService):
    coll = "courses"
    prefix = "KC"
    label = "课程"
    search_fields = ("id", "name", "category", "level", "target")

    def list(self, *, category: str | None = None, level: str | None = None, **kwargs) -> dict:
        return super().list(extra_filters={"category": category, "level": level}, **kwargs)

    def _before_delete(self, code: str) -> None:
        used = [c for c in db.alive("classes") if c.get("courseId") == code]
        if used:
            raise BizException(409, f"该课程下仍有 {len(used)} 个班级，无法删除")
        # 扩展预留：课件资源引用保护（《01-数据库设计》规划，原型暂不拦截）


class ClassService(CrudService):
    coll = "classes"
    prefix = "BJ"
    label = "班级"
    search_fields = ("id", "name", "classroom", "schedule")

    def list(self, *, course_id: str | None = None, teacher_id: str | None = None, **kwargs) -> dict:
        return super().list(extra_filters={"courseId": course_id, "teacherId": teacher_id}, **kwargs)

    def decorate(self, row: dict) -> dict:
        enrolled = sum(1 for s in db.alive("students") if s.get("classId") == row.get("id"))
        course = db.find("courses", row.get("courseId") or "")
        teacher = db.find("teachers", row.get("teacherId") or "")
        return {
            **row,
            "enrolled": enrolled,
            "isFull": enrolled >= int(row.get("capacity") or 0),
            "courseName": course["name"] if course else "",
            "teacherName": teacher["name"] if teacher else "",
        }

    def create(self, data: dict[str, Any]) -> dict:
        course = db.locate("courses", data.get("courseId") or "", label="课程")
        if course.get("status") != "在售":
            raise BizException(409, f"课程「{course['name']}」已停售，无法开班")
        teacher = db.locate("teachers", data.get("teacherId") or "", label="教师")
        if teacher.get("status") != "在职":
            raise BizException(409, f"教师「{teacher['name']}」已离职，无法排课")
        data = {**data}
        data.setdefault("startDate", None)
        if not data.get("startDate"):
            data["startDate"] = today()
        record = super().create(data)
        # 新班级按「上课时间」文本自动建立排课规则与整个学期的课次
        from app.services.schedule import ScheduleService

        ScheduleService().bootstrap_class(record, full=True)
        return record

    def update(self, code: str, data: dict[str, Any]) -> dict:
        if data.get("courseId"):
            course = db.locate("courses", data["courseId"], label="课程")
            if course.get("status") != "在售":
                raise BizException(409, f"课程「{course['name']}」已停售，无法切换")
        if data.get("teacherId"):
            teacher = db.locate("teachers", data["teacherId"], label="教师")
            if teacher.get("status") != "在职":
                raise BizException(409, f"教师「{teacher['name']}」已离职，无法任教")
        before = db.locate("classes", code, label="班级")
        rec = super().update(code, data)
        from app.services.schedule import ScheduleService

        schedule_service = ScheduleService()
        teacher_changed = bool(data.get("teacherId") and data["teacherId"] != before.get("teacherId"))
        schedule_changed = data.get("schedule") is not None and data["schedule"] != before.get("schedule")
        window_changed = any(
            data.get(field) is not None and data[field] != before.get(field)
            for field in ("startDate", "endDate")
        )
        classroom_changed = data.get("classroom") is not None and data["classroom"] != before.get("classroom")
        if teacher_changed:
            schedule_service.reassign_teacher(code, data["teacherId"])
        if classroom_changed:
            # 规则里仍是旧教室时，跟随班级一起更新
            for rule in db.alive("classSchedules"):
                if (rule.get("classId") == code
                        and (rule.get("classroom") or "") == (before.get("classroom") or "")):
                    db.update_fields(
                        "classSchedules", rule["id"],
                        {"classroom": rec.get("classroom") or ""}, label="排课规则",
                    )
        if schedule_changed:
            # 文本排课是简写入口：文本变化时按新文本重建规则，再重建未来课次
            schedule_service.rebuild_rules_from_text(rec)
            schedule_service.regenerate_future(code)
        elif window_changed or classroom_changed or teacher_changed:
            schedule_service.regenerate_future(code)
        return rec

    def delete(self, code: str) -> None:
        super().delete(code)
        # 级联归档该班级的排课规则与课次，避免课表出现无主数据
        for rule in db.alive("classSchedules"):
            if rule.get("classId") == code:
                db.soft_delete("classSchedules", rule["id"], label="排课规则")
        for session in db.alive("classSessions"):
            if session.get("classId") == code:
                db.soft_delete("classSessions", session["id"], label="课次")

    def _before_delete(self, code: str) -> None:
        students = [s for s in db.alive("students") if s.get("classId") == code]
        if students:
            raise BizException(409, f"该班级仍有 {len(students)} 名学员，请先转移或移除学员")


class StudentService(CrudService):
    coll = "students"
    prefix = "XS"
    label = "学员"
    search_fields = ("id", "name", "parent", "parentPhone", "grade")

    def list(self, *, class_id: str | None = None, **kwargs) -> dict:
        return super().list(extra_filters={"classId": class_id} if class_id else None, **kwargs)

    def decorate(self, row: dict) -> dict:
        cls = db.find("classes", row.get("classId") or "")
        return {**row, "className": cls["name"] if cls else ""}

    def create(self, data: dict[str, Any]) -> dict:
        cls = db.locate("classes", data.get("classId") or "", label="班级")
        if cls.get("status") == "已结课":
            raise BizException(409, f"班级「{cls['name']}」已结课，无法再报名")
        data = {**data}
        if not data.get("enrollDate"):
            data["enrollDate"] = today()
        if not data.get("status"):
            data["status"] = db.settings.get("newStudentStatus") or "在读"
        rec = super().create(data)
        # 报名即生成应收账单（家长端「应缴」口径）；失败不阻断报名
        from app.services.finance import BillService

        try:
            BillService().create_for_student(rec)
        except BizException:
            pass
        return rec

    def delete(self, code: str) -> None:
        """删除学员并级联软删其全部缴费记录（同一数据库事务内完成）。"""
        db.soft_delete_student_cascade(code)
