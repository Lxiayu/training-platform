"""作业管理与考勤管理回归测试（教师 / 学员 / 家长三类身份）。

覆盖：
- 教师作业列表按本人班级隔离；跨班布置返回 403；
- 学员只能看到本班作业，跨班提交返回 403；
- 提交可重复（同一条记录更新），重新提交会清空旧批改；
- 教师批改后家长可见分数与评语；跨教师批改返回 403；
- 考勤按「班级 + 日期 + 学员」幂等保存；非法状态 400；跨班录入 403；
- 学员 / 家长只能查看本人或本人关联学员的考勤与作业。
"""
import os
import tempfile
from datetime import date, timedelta

# 与 test_identities 共用同一隔离库，避免重复 engine；本模块 fixture 会重置并播种
_DB_FILE = os.path.join(tempfile.gettempdir(), "qihang_identities_test.db")
os.environ["QIHANG_DB_URL"] = f"sqlite:///{_DB_FILE}"

import pytest
from fastapi.testclient import TestClient

from app.db.seed import seed_db
from app.db.session import init_db, reset_schema
from app.main import app

API = "/api/v1"

CRED = {
    "teacher": ("JS001", "123456"),   # 王志强，带 BJ002 / BJ003
    "teacher2": ("JS002", "123456"),  # 林晓芸，带 BJ001
    "student": ("XS005", "123456"),   # 李思远，BJ002
    "student2": ("XS001", "123456"),  # 陈一诺，BJ001
    "parent": ("P005", "123456"),     # 李国豪，关联 XS005
}


@pytest.fixture(scope="module")
def client():
    # 不要删除数据库文件：共享 engine 仍持有句柄，Windows 下 os.remove 会抛 WinError 32
    init_db()
    reset_schema()
    seed_db()
    with TestClient(app) as c:
        yield c


def token(client, who):
    username, password = CRED[who]
    r = client.post(f"{API}/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["data"]["token"]


def headers(client, who):
    return {"Authorization": f"Bearer {token(client, who)}"}


# ---------------- 教师：作业 ----------------

def test_teacher_assignments_scoped_to_own_classes(client):
    h = headers(client, "teacher")
    rows = client.get(f"{API}/portal/teacher/assignments", headers=h).json()["data"]
    assert {a["id"] for a in rows} == {"HW001", "HW002", "HW003"}
    assert all(a["teacherId"] == "JS001" for a in rows)


def test_teacher_cannot_create_assignment_for_other_class(client):
    h = headers(client, "teacher")
    r = client.post(f"{API}/portal/teacher/assignments", headers=h,
                    json={"classId": "BJ001", "title": "越权作业", "content": "x"})
    assert r.status_code == 403


def test_assignment_lifecycle_and_grading_visible_to_parent(client):
    teacher = headers(client, "teacher")
    student = headers(client, "student")
    parent = headers(client, "parent")

    created = client.post(f"{API}/portal/teacher/assignments", headers=teacher,
                          json={"classId": "BJ002", "title": "循环练习", "content": "完成 1-3 题",
                                "dueDate": "2026-11-10"})
    assert created.status_code == 200
    aid = created.json()["data"]["id"]
    assert aid.startswith("HW")

    # 学员提交两次 -> 同一条记录
    first = client.post(f"{API}/portal/student/assignments/{aid}/submit", headers=student,
                        json={"content": "第一版答案"})
    assert first.status_code == 200
    sid = first.json()["data"]["id"]
    second = client.post(f"{API}/portal/student/assignments/{aid}/submit", headers=student,
                         json={"content": "第二版答案"})
    assert second.json()["data"]["id"] == sid
    assert second.json()["data"]["status"] == "已提交"

    # 教师批改
    graded = client.post(f"{API}/portal/teacher/submissions/{sid}/grade", headers=teacher,
                         json={"score": 90, "comment": "思路清晰"})
    assert graded.status_code == 200
    assert graded.json()["data"]["status"] == "已批改"

    # 家长可见孩子作业与批改结果
    rows = client.get(f"{API}/portal/parent/assignments", headers=parent).json()["data"]
    target = [x for x in rows if x["assignmentId"] == aid]
    assert target and target[0]["score"] == 90 and target[0]["comment"] == "思路清晰"

    # 已批改的提交不可直接改交（需教师退回）
    blocked = client.post(f"{API}/portal/student/assignments/{aid}/submit", headers=student,
                          json={"content": "第三版答案"})
    assert blocked.status_code == 409

    # 教师退回后，原成绩作废，学员可重新提交
    returned = client.post(f"{API}/portal/teacher/submissions/{sid}/return", headers=teacher,
                           json={"reason": "请补充边界情况说明"})
    assert returned.status_code == 200
    assert returned.json()["data"]["status"] == "已退回"
    assert returned.json()["data"]["score"] is None
    assert returned.json()["data"]["returnReason"] == "请补充边界情况说明"

    # 已退回、学员尚未重交时不能直接批改
    regrade = client.post(f"{API}/portal/teacher/submissions/{sid}/grade", headers=teacher,
                          json={"score": 80, "comment": "直接改分"})
    assert regrade.status_code == 409

    resubmit = client.post(f"{API}/portal/student/assignments/{aid}/submit", headers=student,
                           json={"content": "第三版答案"})
    assert resubmit.status_code == 200
    assert resubmit.json()["data"]["status"] == "已提交"
    assert resubmit.json()["data"]["score"] is None
    assert resubmit.json()["data"]["returnReason"] is None


def test_student_cannot_submit_other_class_assignment(client):
    h = headers(client, "student")
    r = client.post(f"{API}/portal/student/assignments/HW004/submit", headers=h,
                    json={"content": "越权提交"})
    assert r.status_code == 403


def test_teacher_cannot_grade_other_teachers_submission(client):
    h = headers(client, "teacher")
    r = client.post(f"{API}/portal/teacher/submissions/TJ005/grade", headers=h,
                    json={"score": 60, "comment": "x"})
    assert r.status_code == 403


def test_student_and_parent_cannot_use_teacher_assignment_api(client):
    assert client.get(f"{API}/portal/teacher/assignments", headers=headers(client, "student")).status_code == 403
    assert client.get(f"{API}/portal/teacher/assignments", headers=headers(client, "parent")).status_code == 403


# ---------------- 考勤 ----------------

def test_attendance_roster_save_and_visibility(client):
    teacher = headers(client, "teacher")
    student = headers(client, "student")
    parent = headers(client, "parent")

    # 新日期：默认全部出勤，尚未保存
    roster = client.get(f"{API}/portal/teacher/attendance?classId=BJ002&date=2026-11-08", headers=teacher).json()["data"]
    assert roster["saved"] is False
    assert len(roster["rows"]) == 4
    assert all(r["status"] == "出勤" for r in roster["rows"])

    items = [{"studentId": r["studentId"], "status": "出勤", "note": ""} for r in roster["rows"]]
    items[0]["status"] = "迟到"
    items[0]["note"] = "迟到 8 分钟"
    saved = client.post(f"{API}/portal/teacher/attendance", headers=teacher,
                        json={"classId": "BJ002", "date": "2026-11-08", "items": items})
    assert saved.status_code == 200
    assert saved.json()["data"]["saved"] is True
    assert saved.json()["data"]["summary"]["迟到"] == 1

    # 幂等：重复保存不新增记录
    again = client.post(f"{API}/portal/teacher/attendance", headers=teacher,
                        json={"classId": "BJ002", "date": "2026-11-08", "items": items})
    assert len(again.json()["data"]["rows"]) == 4

    # 学员与家长可见
    stu_rows = client.get(f"{API}/portal/student/attendance", headers=student).json()["data"]
    assert any(r["date"] == "2026-11-08" and r["status"] == "迟到" for r in stu_rows)
    par_rows = client.get(f"{API}/portal/parent/attendance", headers=parent).json()["data"]
    assert any(r["date"] == "2026-11-08" and r["status"] == "迟到" for r in par_rows)


def test_attendance_validation_and_scope(client):
    teacher = headers(client, "teacher")
    # 跨班录入
    r = client.post(f"{API}/portal/teacher/attendance", headers=teacher,
                    json={"classId": "BJ001", "date": "2026-11-08",
                          "items": [{"studentId": "XS001", "status": "出勤"}]})
    assert r.status_code == 403
    # 非法状态
    r = client.post(f"{API}/portal/teacher/attendance", headers=teacher,
                    json={"classId": "BJ002", "date": "2026-11-09",
                          "items": [{"studentId": "XS005", "status": "旷课"}]})
    assert r.status_code == 400
    # 非本班学员
    r = client.post(f"{API}/portal/teacher/attendance", headers=teacher,
                    json={"classId": "BJ002", "date": "2026-11-09",
                          "items": [{"studentId": "XS001", "status": "出勤"}]})
    assert r.status_code == 400


def test_parent_cannot_read_unrelated_child(client):
    h = headers(client, "parent")
    assert client.get(f"{API}/portal/parent/assignments?studentId=XS006", headers=h).status_code == 403
    assert client.get(f"{API}/portal/parent/attendance?studentId=XS006", headers=h).status_code == 403


def test_teacher_cannot_read_other_class_attendance(client):
    h = headers(client, "teacher")
    assert client.get(f"{API}/portal/teacher/attendance?classId=BJ001&date=2026-10-17", headers=h).status_code == 403


# ---------------- 作业规则补齐（截止 / 退回 / 删除保护） ----------------

def test_assignment_due_date_validation(client):
    teacher = headers(client, "teacher")
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    r = client.post(f"{API}/portal/teacher/assignments", headers=teacher,
                    json={"classId": "BJ002", "title": "过期作业", "dueDate": yesterday})
    assert r.status_code == 422
    r = client.post(f"{API}/portal/teacher/assignments", headers=teacher,
                    json={"classId": "BJ002", "title": "格式错误", "dueDate": "2026/01/01"})
    assert r.status_code == 400


def test_assignment_cannot_be_deleted_after_submission(client):
    teacher = headers(client, "teacher")
    student = headers(client, "student")

    # 无提交可删除
    free = client.post(f"{API}/portal/teacher/assignments", headers=teacher,
                       json={"classId": "BJ002", "title": "可删除作业",
                             "dueDate": (date.today() + timedelta(days=5)).isoformat()}).json()["data"]
    assert client.delete(f"{API}/portal/teacher/assignments/{free['id']}", headers=teacher).status_code == 200

    # 有提交不可删除（409）
    used = client.post(f"{API}/portal/teacher/assignments", headers=teacher,
                       json={"classId": "BJ002", "title": "已有提交作业",
                             "dueDate": (date.today() + timedelta(days=5)).isoformat()}).json()["data"]
    assert client.post(f"{API}/portal/student/assignments/{used['id']}/submit",
                       headers=student, json={"content": "答案"}).status_code == 200
    blocked = client.delete(f"{API}/portal/teacher/assignments/{used['id']}", headers=teacher)
    assert blocked.status_code == 409


def test_late_submission_blocked_unless_allow_late(client):
    from app.db.repository import db

    teacher = headers(client, "teacher")
    student = headers(client, "student")
    created = client.post(f"{API}/portal/teacher/assignments", headers=teacher,
                          json={"classId": "BJ002", "title": "截止校验作业",
                                "dueDate": (date.today() + timedelta(days=2)).isoformat()}).json()["data"]
    aid = created["id"]

    # 模拟时间流逝：把截止日改到过去
    db.update_fields("assignments", aid, {"dueDate": "2020-01-01"}, label="作业")
    late = client.post(f"{API}/portal/student/assignments/{aid}/submit",
                       headers=student, json={"content": "迟交答案"})
    assert late.status_code == 409

    # 教师开启「允许迟交」后可以提交
    assert client.put(f"{API}/portal/teacher/assignments/{aid}", headers=teacher,
                      json={"allowLate": True}).status_code == 200
    ok = client.post(f"{API}/portal/student/assignments/{aid}/submit",
                     headers=student, json={"content": "迟交答案"})
    assert ok.status_code == 200
    assert ok.json()["data"]["status"] == "已提交"


def test_return_requires_graded_submission(client):
    teacher = headers(client, "teacher")
    # TJ001 状态「已提交」，未批改不可退回
    r = client.post(f"{API}/portal/teacher/submissions/TJ001/return", headers=teacher,
                    json={"reason": "未批改不能退回"})
    assert r.status_code == 409
    # 退回理由必填
    r = client.post(f"{API}/portal/teacher/submissions/TJ002/return", headers=teacher,
                    json={"reason": "x"})
    assert r.status_code == 422
