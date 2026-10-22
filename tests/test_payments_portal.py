"""缴费详情（学员端 / 家长端）接口测试。

覆盖：
- 学员查看自己的应缴 / 已缴 / 待确认 / 欠费与账单、流水明细；
- 家长只能查看关联学员（跨孩子 403），身份不匹配 403；
- 待确认 -> 已支付 -> 作废对家长端口径的实时影响；
- 新学员报名自动生成账单，缴费自动挂账单。

运行：``python -m pytest tests/test_payments_portal.py -q``
"""
import os
import tempfile

# 与 test_identities.py 共存于同一测试进程时复用其数据库；单独运行时使用独立临时库
os.environ.setdefault(
    "QIHANG_DB_URL",
    f"sqlite:///{os.path.join(tempfile.gettempdir(), 'qihang_payments_test.db')}",
)

import pytest
from fastapi.testclient import TestClient

from app.db.repository import db
from app.db.seed import seed_db
from app.db.session import reset_schema
from app.main import app
from app.services.finance import BillService

API = "/api/v1"

CRED = {
    "staff": ("admin", "admin123"),
    "teacher": ("JS001", "123456"),
    "student": ("XS001", "123456"),
    "parent": ("P001", "123456"),
    "parent_xs004": ("P004", "123456"),
}


@pytest.fixture(scope="module")
def client():
    # 每个测试模块从干净的种子状态开始（共享 engine 时也可隔离前序模块的写操作）
    reset_schema()
    seed_db()
    with TestClient(app) as c:
        yield c


def login(client, username, password="123456"):
    r = client.post(f"{API}/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["data"]


def bearer(client, key):
    u, p = CRED[key]
    return {"Authorization": f"Bearer {login(client, u, p)['token']}"}


def payments_of(client, path, headers):
    r = client.get(f"{API}{path}", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["data"]


# ---------------- 学员端 ----------------

def test_student_payment_summary(client):
    data = payments_of(client, "/portal/student/payments", bearer(client, "student"))
    assert data["student"]["studentId"] == "XS001"
    assert data["hasBills"] is True

    summary = data["summary"]
    assert summary["dueTotal"] == 2400.0
    assert summary["paidTotal"] == 2400.0
    assert summary["pendingTotal"] == 0.0
    assert summary["outstanding"] == 0.0

    bill = data["bills"][0]
    assert bill["amount"] == 2400.0
    assert bill["paidAmount"] == 2400.0
    assert bill["displayStatus"] == "已缴"
    assert bill["courseName"] == "Scratch 趣味编程启蒙"

    payment = next(p for p in data["payments"] if p["id"] == "JF001")
    assert payment["billId"] == bill["id"]
    assert payment["amount"] == 2400.0


def test_summary_balanced_and_sorted(client):
    data = payments_of(client, "/portal/student/payments", bearer(client, "student"))
    s = data["summary"]
    assert s["dueTotal"] - s["paidTotal"] == s["outstanding"]
    dates = [p["date"] for p in data["payments"]]
    assert dates == sorted(dates, reverse=True)


# ---------------- 家长端与越权 ----------------

def test_parent_sees_linked_child(client):
    data = payments_of(client, "/portal/parent/XS001/payments", bearer(client, "parent"))
    assert data["student"]["studentId"] == "XS001"
    assert data["summary"]["paidTotal"] == 2400.0


def test_parent_cannot_see_unlinked_child(client):
    r = client.get(f"{API}/portal/parent/XS002/payments", headers=bearer(client, "parent"))
    assert r.status_code == 403


def test_identity_gating(client):
    # 教师不能看学员缴费详情
    assert client.get(f"{API}/portal/student/payments", headers=bearer(client, "teacher")).status_code == 403
    # 学员不能走家长端接口
    assert client.get(f"{API}/portal/parent/XS001/payments", headers=bearer(client, "student")).status_code == 403
    # 家长不能看学员端「本人」接口
    assert client.get(f"{API}/portal/student/payments", headers=bearer(client, "parent")).status_code == 403


# ---------------- 状态流转对口径的影响 ----------------

def test_pending_confirm_void_flow(client):
    h = bearer(client, "parent_xs004")
    data = payments_of(client, "/portal/parent/XS004/payments", h)
    assert data["summary"]["dueTotal"] == 2400.0
    assert data["summary"]["paidTotal"] == 0.0
    assert data["summary"]["pendingTotal"] == 1200.0
    assert data["summary"]["outstanding"] == 2400.0
    assert data["bills"][0]["displayStatus"] == "已逾期"

    admin = bearer(client, "staff")
    assert client.post(f"{API}/payments/JF004/confirm", headers=admin).status_code == 200
    data = payments_of(client, "/portal/parent/XS004/payments", h)
    assert data["summary"]["paidTotal"] == 1200.0
    assert data["summary"]["pendingTotal"] == 0.0
    assert data["summary"]["outstanding"] == 1200.0
    assert data["bills"][0]["displayStatus"] == "部分缴"

    assert client.post(f"{API}/payments/JF004/void", headers=admin).status_code == 200
    data = payments_of(client, "/portal/parent/XS004/payments", h)
    assert data["summary"]["paidTotal"] == 0.0
    assert data["summary"]["outstanding"] == 2400.0
    assert data["bills"][0]["displayStatus"] == "已逾期"


# ---------------- 新学员：自动账单 + 流水挂账 ----------------

def test_new_student_gets_bill_and_payment_links(client):
    admin = bearer(client, "staff")
    r = client.post(f"{API}/students", headers=admin, json={
        "name": "缴费测试生", "gender": "男", "grade": "五年级",
        "parent": "测试家长", "parentPhone": "15800000000", "classId": "BJ002",
    })
    assert r.status_code == 200, r.text
    student_id = r.json()["data"]["id"]

    bills = [b for b in db.alive("bills") if b.get("studentId") == student_id]
    assert len(bills) == 1
    bill = bills[0]
    assert bill["amount"] == 3600.0  # KC002 课程价
    assert bill["status"] == "待缴"

    r = client.post(f"{API}/payments", headers=admin, json={
        "studentId": student_id, "classId": "BJ002", "amount": 3600,
        "method": "微信", "note": "秋季班学费",
    })
    assert r.status_code == 200, r.text
    payment = r.json()["data"]
    assert payment["billId"] == bill["id"]

    assert client.post(f"{API}/payments/{payment['id']}/confirm", headers=admin).status_code == 200
    decorated = BillService().decorate(db.find("bills", bill["id"]))
    assert decorated["paidAmount"] == 3600.0
    assert decorated["displayStatus"] == "已缴"
