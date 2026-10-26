"""排课规则 / 课次 / 三端课表回归测试（E1）。

覆盖：
- 存量排课文本解析为规则，整个学期课次生成且幂等；
- 教师 / 学员 / 家长课表的数据范围与越权 403；
- 课次取消、调课（原课次保留、新时间可追溯）；
- 规则校验（时间、重复）与规则删除后未来课次回收。
"""
import os
import tempfile
from datetime import date, timedelta

_DB_FILE = os.path.join(tempfile.gettempdir(), "qihang_identities_test.db")
os.environ["QIHANG_DB_URL"] = f"sqlite:///{_DB_FILE}"

import pytest
from fastapi.testclient import TestClient

from app.db.seed import seed_db
from app.db.session import init_db, reset_schema
from app.main import app

API = "/api/v1"

CRED = {
    "admin": ("admin", "admin123"),
    "teacher": ("JS001", "123456"),    # 王志强：BJ002 / BJ003
    "teacher2": ("JS002", "123456"),   # 林晓芸：BJ001
    "student": ("XS005", "123456"),    # 李思远：BJ002
    "student2": ("XS001", "123456"),   # 陈一诺：BJ001
    "parent": ("P005", "123456"),      # 李国豪：关联 XS005
}


@pytest.fixture(scope="module")
def client():
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


# ---------------- 规则与课次生成 ----------------

def test_legacy_schedule_text_becomes_rules(client):
    h = headers(client, "admin")
    rules = client.get(f"{API}/classes/BJ002/schedules", headers=h).json()["data"]
    assert len(rules) == 1
    assert rules[0]["weekday"] == 7
    assert rules[0]["startTime"] == "09:00" and rules[0]["endTime"] == "12:00"
    assert rules[0]["effectiveFrom"] == "2026-09-06"

    # 「周一/三/五」解析为 3 条规则
    rules6 = client.get(f"{API}/classes/BJ006/schedules", headers=h).json()["data"]
    assert [r["weekday"] for r in rules6] == [1, 3, 5]


def test_sessions_generated_for_term_and_idempotent(client):
    h = headers(client, "admin")
    rows = client.get(
        f"{API}/classes/BJ002/sessions?from=2026-09-01&to=2026-12-31", headers=h
    ).json()["data"]
    assert len(rows) == 16                       # 2026-09-06 ~ 2026-12-20 的 16 个周日
    assert all(r["classId"] == "BJ002" for r in rows)
    assert all(r["status"] in ("待上课", "已上课") for r in rows)

    again = client.post(
        f"{API}/classes/BJ002/sessions/generate", headers=h,
        json={"from": "2026-09-01", "to": "2026-12-31"},
    ).json()["data"]
    assert again["created"] == 0                 # 幂等：不重复生成


def test_rule_validation_and_regeneration(client):
    h = headers(client, "admin")
    bad = client.post(
        f"{API}/classes/BJ005/schedules", headers=h,
        json={"weekday": 2, "startTime": "10:00", "endTime": "09:00"},
    )
    assert bad.status_code == 400

    payload = {"weekday": 2, "startTime": "18:00", "endTime": "19:30",
               "effectiveFrom": "2026-10-01", "effectiveTo": "2026-12-31"}
    created = client.post(f"{API}/classes/BJ005/schedules", headers=h, json=payload)
    assert created.status_code == 200
    rule_id = created.json()["data"]["id"]

    duplicated = client.post(f"{API}/classes/BJ005/schedules", headers=h, json=payload)
    assert duplicated.status_code == 409

    # 规则删除后，未来未上课的自动课次被回收
    before = client.get(f"{API}/classes/BJ005/sessions", headers=h).json()["data"]
    future_before = [s for s in before if s["sessionDate"] >= date.today().isoformat()]
    assert future_before
    assert client.delete(f"{API}/schedules/{rule_id}", headers=h).status_code == 200
    after = client.get(f"{API}/classes/BJ005/sessions", headers=h).json()["data"]
    assert len(after) < len(before)


def test_creating_class_auto_builds_rules_and_sessions(client):
    h = headers(client, "admin")
    today = date.today()
    created = client.post(f"{API}/classes", headers=h, json={
        "name": "自动化测试班", "courseId": "KC007", "teacherId": "JS006",
        "classroom": "A102", "capacity": 10, "schedule": "周二 14:00-15:30",
        "startDate": today.isoformat(),
        "endDate": (today + timedelta(days=28)).isoformat(),
        "status": "进行中",
    })
    assert created.status_code == 200, created.text
    class_id = created.json()["data"]["id"]

    rules = client.get(f"{API}/classes/{class_id}/schedules", headers=h).json()["data"]
    assert len(rules) == 1 and rules[0]["weekday"] == 2

    sessions = client.get(
        f"{API}/classes/{class_id}/sessions?from={today.isoformat()}"
        f"&to={(today + timedelta(days=28)).isoformat()}", headers=h,
    ).json()["data"]
    assert len(sessions) == 4                    # 28 天内的 4 个周二
    assert all(s["classId"] == class_id for s in sessions)
    assert all(s["sessionDate"] == (today + timedelta(days=(2 - today.isoweekday()) % 7 + 7 * i)).isoformat()
               for i, s in enumerate(sessions))


# ---------------- 三端课表 ----------------

def test_teacher_timetable_scoped(client):
    h = headers(client, "teacher")
    data = client.get(f"{API}/portal/teacher/timetable", headers=h).json()["data"]
    assert data["sessions"]
    assert {s["classId"] for s in data["sessions"]} <= {"BJ002", "BJ003"}
    assert all(s["teacherId"] == "JS001" for s in data["sessions"])

    other = client.get(f"{API}/portal/teacher/timetable", headers=headers(client, "teacher2")).json()["data"]
    assert {s["classId"] for s in other["sessions"]} <= {"BJ001"}


def test_student_timetable_scoped(client):
    h = headers(client, "student")
    data = client.get(f"{API}/portal/student/timetable", headers=h).json()["data"]
    assert data["student"]["studentId"] == "XS005"
    assert data["sessions"]
    assert {s["classId"] for s in data["sessions"]} == {"BJ002"}

    h2 = headers(client, "student2")
    data2 = client.get(f"{API}/portal/student/timetable", headers=h2).json()["data"]
    assert {s["classId"] for s in data2["sessions"]} == {"BJ001"}


def test_parent_timetable_scope_and_gate(client):
    h = headers(client, "parent")
    data = client.get(f"{API}/portal/parent/XS005/timetable", headers=h).json()["data"]
    assert data["sessions"]
    assert {s["classId"] for s in data["sessions"]} == {"BJ002"}
    # 非关联孩子 403
    assert client.get(f"{API}/portal/parent/XS001/timetable", headers=h).status_code == 403
    # 学员 / 家长不能访问教师课表
    assert client.get(f"{API}/portal/teacher/timetable", headers=headers(client, "student")).status_code == 403


def test_admin_schedule_apis_are_staff_only(client):
    assert client.get(f"{API}/classes/BJ002/schedules", headers=headers(client, "teacher")).status_code == 403
    assert client.get(f"{API}/classes/BJ002/sessions", headers=headers(client, "student")).status_code == 403
    # 教师只能查看自己班级的课次
    assert client.get(
        f"{API}/portal/teacher/sessions?classId=BJ001", headers=headers(client, "teacher")
    ).status_code == 403
    assert client.get(
        f"{API}/portal/teacher/sessions?classId=BJ002", headers=headers(client, "teacher")
    ).status_code == 200


# ---------------- 取消 / 调课 ----------------

def test_cancel_session_visible_to_student(client):
    admin = headers(client, "admin")
    student = headers(client, "student")
    rows = client.get(
        f"{API}/classes/BJ002/sessions?from={date.today().isoformat()}"
        f"&to={(date.today() + timedelta(days=30)).isoformat()}", headers=admin,
    ).json()["data"]
    target = next(s for s in rows if s["status"] == "待上课")
    r = client.post(f"{API}/sessions/{target['id']}/cancel", headers=admin)
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "已取消"

    tt = client.get(
        f"{API}/portal/student/timetable?from={date.today().isoformat()}"
        f"&to={(date.today() + timedelta(days=30)).isoformat()}", headers=student,
    ).json()["data"]
    assert any(s["id"] == target["id"] and s["status"] == "已取消" for s in tt["sessions"])
    # 已取消的课次不能再次取消
    assert client.post(f"{API}/sessions/{target['id']}/cancel", headers=admin).status_code == 409


def test_reschedule_keeps_original_traceable(client):
    admin = headers(client, "admin")
    student = headers(client, "student")
    rows = client.get(
        f"{API}/classes/BJ002/sessions?from={date.today().isoformat()}"
        f"&to={(date.today() + timedelta(days=40)).isoformat()}", headers=admin,
    ).json()["data"]
    target = next(s for s in rows if s["status"] == "待上课")
    new_day = date.fromisoformat(target["sessionDate"]) + timedelta(days=2)
    payload = {"sessionDate": new_day.isoformat(), "startTime": "20:00", "endTime": "21:30"}
    r = client.post(f"{API}/sessions/{target['id']}/reschedule", headers=admin, json=payload)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["original"]["status"] == "已调课"
    assert data["original"]["rescheduledTo"] == data["session"]["id"]
    assert data["session"]["status"] == "待上课"
    assert data["session"]["originalDate"] == target["sessionDate"]
    assert data["session"]["rescheduledFrom"] == target["id"]

    tt = client.get(
        f"{API}/portal/student/timetable?from={date.today().isoformat()}"
        f"&to={(new_day + timedelta(days=7)).isoformat()}", headers=student,
    ).json()["data"]
    ids = {s["id"] for s in tt["sessions"]}
    assert {target["id"], data["session"]["id"]} <= ids
    # 已调课的旧课次不能再次调课
    assert client.post(
        f"{API}/sessions/{target['id']}/reschedule", headers=admin, json=payload
    ).status_code == 409
