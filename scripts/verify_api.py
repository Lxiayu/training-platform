"""API 冒烟验证脚本：覆盖核心业务规则的 ~25 组断言。

运行：python scripts/verify_api.py
- 使用独立临时数据文件（QIHANG_DB_FILE），不污染 data/app.json；
- 全部通过退出码 0，否则退出码 1 并打印失败明细。

覆盖：认证/权限、用户保护（最后管理员、自删自禁、重置密码）、
教师/课程删除保护、班级开班校验、学员级联删除、缴费状态机、
统计口径（仅已支付计入收入）、新闻置顶排序与阅读数、资源下载数、
工作台聚合、系统设置联动（新学员默认状态）、取号防复用。
"""
import os
import sys
import tempfile
from pathlib import Path

# 必须在导入 app 之前设置独立数据文件
os.environ["QIHANG_DB_FILE"] = str(Path(tempfile.mkdtemp(prefix="qihang-verify-")) / "app.json")

# 项目根目录加入模块搜索路径（支持从任意目录运行）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)

PASSED = 0
FAILED: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASSED
    if cond:
        PASSED += 1
        print(f"  [PASS] {name}")
    else:
        FAILED.append(f"{name} {detail}")
        print(f"  [FAIL] {name}  {detail}")


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def login(username: str, password: str):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def data_of(resp: dict):
    return resp["data"]


# ---------------------------------------------------------------- 认证与权限

def scenario_auth():
    print("== 认证与权限 ==")
    r = client.get("/api/v1/health")
    check("健康检查", r.status_code == 200 and r.json()["code"] == 0)

    r = login("admin", "admin123")
    check("管理员登录成功", r.status_code == 200 and data_of(r.json())["token"])
    admin_token = data_of(r.json())["token"]

    r = login("admin", "wrong-password")
    check("错误密码 -> 401", r.status_code == 401)

    r = login("wangzq", "123456")
    check("禁用账号登录 -> 403", r.status_code == 403)

    r = login("jiaowu", "123456")
    check("教务登录成功", r.status_code == 200)
    jw_token = data_of(r.json())["token"]

    r = client.get("/api/v1/auth/me", headers=auth(admin_token))
    check("auth/me 返回当前用户", r.status_code == 200 and data_of(r.json())["username"] == "admin"
          and "passwordHash" not in data_of(r.json()))

    r = client.get("/api/v1/teachers")
    check("无令牌访问 -> 401", r.status_code == 401)

    r = client.get("/api/v1/teachers", headers={"Authorization": "Bearer invalid.token.here"})
    check("无效令牌 -> 401", r.status_code == 401)

    r = client.get("/api/v1/users", headers=auth(jw_token))
    check("非管理员访问用户管理 -> 403", r.status_code == 403)

    r = client.get("/api/v1/users", headers=auth(admin_token))
    check("用户列表（5 个种子账号）", r.status_code == 200 and data_of(r.json())["total"] == 5)

    r = client.get("/api/v1/users", params={"keyword": "李文静"}, headers=auth(admin_token))
    rows = data_of(r.json())["list"]
    check("用户关键词搜索", len(rows) == 1 and rows[0]["username"] == "jiaowu")

    return admin_token, jw_token


# ---------------------------------------------------------------- 教师与课程

def scenario_teachers_courses(admin_token: str):
    print("== 教师 / 课程 ==")
    r = client.post("/api/v1/teachers", headers=auth(admin_token), json={
        "name": "测试教师", "gender": "女", "phone": "13900000099",
        "subject": "Python", "title": "助教",
    })
    check("新建教师自动取号 JS008", r.status_code == 200 and data_of(r.json())["id"] == "JS008")

    r = client.delete("/api/v1/teachers/JS008", headers=auth(admin_token))
    check("删除未被引用的教师", r.status_code == 200)

    r = client.delete("/api/v1/teachers/JS001", headers=auth(admin_token))
    check("删除被班级引用的教师 -> 409", r.status_code == 409)

    r = client.post("/api/v1/teachers", headers=auth(admin_token), json={
        "name": "再建教师", "gender": "男", "phone": "13900000098", "subject": "Web",
    })
    check("软删后取号不复用（JS009）", r.status_code == 200 and data_of(r.json())["id"] == "JS009")

    r = client.get("/api/v1/courses", params={"category": "Python"}, headers=auth(admin_token))
    check("课程分类筛选", r.status_code == 200 and data_of(r.json())["total"] == 2)

    r = client.delete("/api/v1/courses/KC001", headers=auth(admin_token))
    check("删除被班级引用的课程 -> 409", r.status_code == 409)


# ---------------------------------------------------------------- 班级

def scenario_classes(admin_token: str):
    print("== 班级 ==")
    r = client.post("/api/v1/classes", headers=auth(admin_token), json={
        "name": "测试班级", "courseId": "KC008", "teacherId": "JS001", "capacity": 10,
    })
    check("停售课程开班 -> 409", r.status_code == 409)

    r = client.post("/api/v1/classes", headers=auth(admin_token), json={
        "name": "测试班级", "courseId": "KC002", "teacherId": "JS007", "capacity": 10,
    })
    check("离职教师排课 -> 409", r.status_code == 409)

    r = client.post("/api/v1/classes", headers=auth(admin_token), json={
        "name": "Python 测试晚班", "courseId": "KC002", "teacherId": "JS001",
        "classroom": "T001", "schedule": "周日 14:00-16:30", "capacity": 8,
    })
    body = data_of(r.json())
    check("新建班级 BJ007（默认未开班）", r.status_code == 200 and body["id"] == "BJ007"
          and body["status"] == "未开班" and body["enrolled"] == 0 and body["isFull"] is False)

    r = client.get("/api/v1/classes", params={"pageSize": 50}, headers=auth(admin_token))
    rows = {c["id"]: c for c in data_of(r.json())["list"]}
    check("班级列表派生字段（BJ001 报名 4 人）", rows["BJ001"]["enrolled"] == 4)
    check("班级列表关联名称", rows["BJ001"]["courseName"] == "Scratch 趣味编程启蒙"
          and rows["BJ001"]["teacherName"] == "林晓芸")

    r = client.put("/api/v1/classes/BJ007", headers=auth(admin_token), json={"status": "进行中"})
    check("班级改为进行中", r.status_code == 200 and data_of(r.json())["status"] == "进行中")

    r = client.delete("/api/v1/classes/BJ001", headers=auth(admin_token))
    check("删除有学员的班级 -> 409", r.status_code == 409)


# ---------------------------------------------------------------- 学员与缴费

def scenario_students_payments(admin_token: str):
    print("== 学员 / 缴费 ==")
    r = client.post("/api/v1/students", headers=auth(admin_token), json={
        "name": "测试学员", "gender": "男", "grade": "四年级",
        "parent": "测试家长", "parentPhone": "15800000099", "classId": "BJ007",
    })
    body = data_of(r.json())
    check("新学员取号 XS017（默认状态读设置=在读）", r.status_code == 200
          and body["id"] == "XS017" and body["status"] == "在读" and body["enrollDate"])

    # 统计基线（避免与真实运行月份耦合，按差值断言）
    base = data_of(client.get("/api/v1/payments/stats", headers=auth(admin_token)).json())
    check("统计基线：累计收入 57400 / 15 笔", base["totalIncome"] == 57400 and base["totalCount"] == 15)
    check("统计基线：待确认 3000 / 2 笔", base["pendingAmount"] == 3000 and base["pendingCount"] == 2)

    r = client.post("/api/v1/payments", headers=auth(admin_token), json={
        "studentId": "XS017", "classId": "BJ007", "amount": 1800, "method": "微信",
    })
    check("新建缴费默认待确认", r.status_code == 200 and data_of(r.json())["status"] == "待确认")

    r = client.post("/api/v1/payments", headers=auth(admin_token), json={
        "studentId": "XS999", "classId": "BJ007", "amount": 100, "method": "现金",
    })
    check("学员不存在 -> 404", r.status_code == 404)

    st = data_of(client.get("/api/v1/payments/stats", headers=auth(admin_token)).json())
    check("待确认统计联动", st["pendingAmount"] == 4800 and st["pendingCount"] == 3)

    r = client.post("/api/v1/payments/JF019/confirm", headers=auth(admin_token))
    check("确认收款：待确认 -> 已支付", r.status_code == 200 and data_of(r.json())["status"] == "已支付")

    r = client.post("/api/v1/payments/JF019/confirm", headers=auth(admin_token))
    check("重复确认 -> 409", r.status_code == 409)

    st = data_of(client.get("/api/v1/payments/stats", headers=auth(admin_token)).json())
    check("收入只计已支付", st["totalIncome"] == 59200 and st["totalCount"] == 16
          and st["pendingAmount"] == 3000 and st["pendingCount"] == 2
          and st["monthIncome"] == base["monthIncome"] + 1800)

    r = client.post("/api/v1/payments/JF019/void", headers=auth(admin_token))
    check("作废已支付缴费", r.status_code == 200 and data_of(r.json())["status"] == "已作废")

    r = client.post("/api/v1/payments/JF019/void", headers=auth(admin_token))
    check("重复作废 -> 409", r.status_code == 409)

    r = client.post("/api/v1/payments/JF011/void", headers=auth(admin_token))
    check("已退款（终态）作废 -> 409", r.status_code == 409)

    st = data_of(client.get("/api/v1/payments/stats", headers=auth(admin_token)).json())
    check("作废不计入收入", st["totalIncome"] == 57400 and st["totalCount"] == 15)

    # 级联删除：学员删除 -> 名下缴费一并归档
    r = client.delete("/api/v1/students/XS017", headers=auth(admin_token))
    check("删除学员", r.status_code == 200)
    r = client.get("/api/v1/payments/JF019", headers=auth(admin_token))
    check("级联删除其缴费记录 -> 404", r.status_code == 404)
    r = client.get("/api/v1/students", params={"pageSize": 50}, headers=auth(admin_token))
    check("学员总数回落 16", data_of(r.json())["total"] == 16)

    r = client.delete("/api/v1/classes/BJ007", headers=auth(admin_token))
    check("删除无学员班级", r.status_code == 200)


# ---------------------------------------------------------------- 工作台

def scenario_dashboard(admin_token: str):
    print("== 工作台 ==")
    # 此刻数据态：教师 8（7 在职 + JS009）、班级 7（含 BJ007 进行中）、学员 16、收入 61000
    r = client.get("/api/v1/dashboard/summary", headers=auth(admin_token))
    s = data_of(r.json())
    check("学员汇总 16/13（休学1 + 已结课2）", s["students"] == {"total": 16, "active": 13})
    check("教师汇总 8/7（含新建 JS009）", s["teachers"] == {"total": 8, "active": 7})
    check("班级汇总 7/5/1（含 BJ007）", s["classes"] == {"total": 7, "running": 5, "notStarted": 1})
    check("累计收入与缴费统计一致", s["income"]["total"] == 57400)

    r = client.get("/api/v1/dashboard/heat", headers=auth(admin_token))
    heat = data_of(r.json())
    check("热度榜第一名为 BJ001（4 人）", heat[0]["id"] == "BJ001" and heat[0]["enrolled"] == 4)

    r = client.get("/api/v1/dashboard/recent-classes", headers=auth(admin_token))
    rc = data_of(r.json())
    check("近期班级按开班日期升序（首：BJ003）", rc[0]["id"] == "BJ003" and len(rc) == 4)

    r = client.get("/api/v1/dashboard/recent-payments", headers=auth(admin_token))
    rp = data_of(r.json())
    check("最新缴费按日期倒序（首：JF018）", rp[0]["id"] == "JF018" and rp[0]["studentName"] == "孙铭泽")


# ---------------------------------------------------------------- 新闻与资源

def scenario_news_resources(admin_token: str):
    print("== 新闻 / 资源 ==")
    r = client.post("/api/v1/news", headers=auth(admin_token), json={
        "title": "测试公告：后端联调完成", "category": "机构动态", "date": "2026-09-01",
        "summary": "验证脚本自动创建。", "content": ["第一段。"],
    })
    body = data_of(r.json())
    check("新建新闻（默认草稿 / views=0 / 作者=当前用户）", r.status_code == 200
          and body["status"] == "草稿" and body["views"] == 0 and body["author"] == "张明远")

    r = client.put("/api/v1/news/" + body["id"], headers=auth(admin_token), json={"status": "已发布"})
    check("新闻发布", r.status_code == 200 and data_of(r.json())["status"] == "已发布")

    r = client.post(f"/api/v1/news/{body['id']}/view", headers=auth(admin_token))
    check("阅读计数 +1", data_of(r.json())["views"] == 1)

    r = client.get("/api/v1/news", params={"pageSize": 50}, headers=auth(admin_token))
    rows = data_of(r.json())["list"]
    check("列表置顶优先", rows[0]["id"] == "XW001" and rows[0]["top"] is True)
    check("非置顶按日期倒序（最新 XW005 在前，自建 09-01 垫底）",
          rows[1]["id"] == "XW005" and rows[-1]["id"] == body["id"])

    r = client.delete(f"/api/v1/news/{body['id']}", headers=auth(admin_token))
    check("删除新闻", r.status_code == 200)

    r = client.post("/api/v1/resources/ZY001/download", headers=auth(admin_token))
    check("下载计数 +1（156 -> 157）", r.status_code == 200 and data_of(r.json())["downloads"] == 157)

    r = client.post("/api/v1/resources", headers=auth(admin_token), json={
        "title": "无效资源", "type": "课件PPT", "courseId": "KC999", "teacherId": "JS001",
    })
    check("资源关联课程不存在 -> 404", r.status_code == 404)


# ---------------------------------------------------------------- 设置与用户保护

def scenario_settings_users(admin_token: str, jw_token: str):
    print("== 设置 / 用户保护 ==")
    r = client.get("/api/v1/settings", headers=auth(jw_token))
    check("读取设置（登录即可）", r.status_code == 200
          and data_of(r.json())["settings"]["newStudentStatus"] == "在读")

    r = client.put("/api/v1/settings", headers=auth(jw_token), json={"intro": "x"})
    check("非管理员保存设置 -> 403", r.status_code == 403)

    r = client.put("/api/v1/settings", headers=auth(admin_token), json={"newStudentStatus": "休学"})
    check("修改新学员默认状态", r.status_code == 200
          and data_of(r.json())["settings"]["newStudentStatus"] == "休学")

    r = client.post("/api/v1/students", headers=auth(admin_token), json={
        "name": "休学默认验证", "gender": "女", "grade": "二年级",
        "parent": "验证家长", "parentPhone": "15800000098", "classId": "BJ001",
    })
    check("新学员状态联动设置为休学", data_of(r.json())["status"] == "休学")

    r = client.put("/api/v1/settings", headers=auth(admin_token), json={"newStudentStatus": "在读"})
    check("恢复默认状态为在读", r.status_code == 200)

    r = client.put("/api/v1/settings", headers=auth(admin_token), json={"newStudentStatus": "已结课"})
    check("非法默认状态 -> 400", r.status_code == 400)

    # ---- 用户保护 ----
    r = client.delete("/api/v1/users/admin", headers=auth(admin_token))
    check("删除当前登录账号 -> 409", r.status_code == 409)
    r = client.put("/api/v1/users/admin", headers=auth(admin_token), json={"status": "禁用"})
    check("禁用当前登录账号 -> 409", r.status_code == 409)
    r = client.put("/api/v1/users/admin", headers=auth(admin_token), json={"role": "教务管理员"})
    check("降级最后一个超管 -> 409", r.status_code == 409)

    r = client.post("/api/v1/users", headers=auth(admin_token), json={
        "username": "jiaowu", "name": "重复名", "phone": "13800000099",
    })
    check("重复用户名 -> 409", r.status_code == 409)

    r = client.post("/api/v1/users", headers=auth(jw_token), json={
        "username": "nope", "name": "越权", "phone": "13800000098",
    })
    check("非管理员创建用户 -> 403", r.status_code == 403)

    r = client.post("/api/v1/users", headers=auth(admin_token), json={
        "username": "temp_user", "name": "临时用户", "phone": "13800000097",
    })
    check("创建用户（默认密码 123456）", r.status_code == 200
          and data_of(r.json())["username"] == "temp_user")
    r = login("temp_user", "123456")
    check("新用户使用默认密码登录", r.status_code == 200)

    r = client.put("/api/v1/users/temp_user", headers=auth(admin_token), json={"status": "禁用"})
    check("禁用普通用户", r.status_code == 200)
    r = login("temp_user", "123456")
    check("禁用后登录 -> 403", r.status_code == 403)
    r = client.delete("/api/v1/users/temp_user", headers=auth(admin_token))
    check("删除普通用户", r.status_code == 200)

    r = client.post("/api/v1/users/jiaowu/reset-password", headers=auth(admin_token))
    check("重置密码返回初始密码", r.status_code == 200
          and data_of(r.json())["initialPassword"] == "123456")
    r = login("jiaowu", "123456")
    check("重置后可用 123456 登录", r.status_code == 200)

    r = client.put("/api/v1/auth/password", headers=auth(jw_token),
                   json={"oldPassword": "123456", "newPassword": "jiaowu@2026"})
    check("修改密码", r.status_code == 200)
    r = login("jiaowu", "jiaowu@2026")
    check("新密码登录成功", r.status_code == 200)
    r = login("jiaowu", "123456")
    check("旧密码登录 -> 401", r.status_code == 401)

    # ---- 参数校验中文提示 ----
    r = client.post("/api/v1/teachers", headers=auth(admin_token), json={"phone": "13900000000"})
    check("缺必填字段 -> 422 中文提示", r.status_code == 422
          and "参数校验失败" in r.json()["message"])
    r = client.post("/api/v1/students", headers=auth(admin_token), json={
        "name": "x", "grade": "x", "parent": "x", "parentPhone": "123", "classId": "BJ001",
    })
    check("字段长度校验 -> 422", r.status_code == 422)


# ---------------------------------------------------------------- 前端对齐项（阶段三）

def scenario_align(admin_token: str, jw_token: str):
    print("== 前端对齐项（搜索字段 / 待确认金额 / 重置数据） ==")

    # ---- 搜索字段对齐：支持按业务编号搜索（大小写不敏感） ----
    r = client.get("/api/v1/courses", params={"keyword": "kc001"}, headers=auth(admin_token))
    rows = data_of(r.json())["list"]
    check("课程按编号搜索（大小写不敏感）", len(rows) == 1 and rows[0]["id"] == "KC001")

    r = client.get("/api/v1/teachers", params={"keyword": "JS001"}, headers=auth(admin_token))
    check("教师按编号搜索", len(data_of(r.json())["list"]) == 1)

    r = client.get("/api/v1/classes", params={"keyword": "A101"}, headers=auth(admin_token))
    check("班级按教室搜索", len(data_of(r.json())["list"]) >= 1)

    r = client.get("/api/v1/students", params={"keyword": "XS001"}, headers=auth(admin_token))
    check("学员按编号搜索", len(data_of(r.json())["list"]) == 1)

    # ---- 缴费支持按学员姓名搜索（前端搜索框行为） ----
    r = client.get("/api/v1/payments", params={"pageSize": 1}, headers=auth(admin_token))
    first = data_of(r.json())["list"][0]
    r = client.get("/api/v1/payments", params={"keyword": first["studentName"], "pageSize": 100}, headers=auth(admin_token))
    rows = data_of(r.json())["list"]
    check("缴费按学员姓名搜索", len(rows) >= 1
          and any(p["studentName"] == first["studentName"] for p in rows))

    # ---- 工作台收入卡片补充待确认口径 ----
    r = client.get("/api/v1/dashboard/summary", headers=auth(admin_token))
    summary = data_of(r.json())
    r = client.get("/api/v1/payments/stats", headers=auth(admin_token))
    stats = data_of(r.json())
    check("summary 含待确认金额且口径一致",
          summary["income"]["pending"] == stats["pendingAmount"]
          and summary["income"]["pendingCount"] == stats["pendingCount"])

    # ---- 一键重置演示数据 ----
    r = client.get("/api/v1/courses", params={"pageSize": 100}, headers=auth(admin_token))
    course_total = data_of(r.json())["total"]

    r = client.post("/api/v1/courses", headers=auth(admin_token), json={
        "name": "对齐测试临时课程", "category": "Scratch", "level": "入门",
        "hours": 8, "price": 800, "target": "测试", "desc": "将被重置",
    })
    check("创建临时课程", r.status_code == 200)

    r = client.post("/api/v1/settings/reset", headers=auth(jw_token))
    check("非管理员重置 -> 403", r.status_code == 403)

    r = client.post("/api/v1/settings/reset", headers=auth(admin_token))
    check("管理员重置演示数据", r.status_code == 200 and "org" in data_of(r.json()))

    r = client.get("/api/v1/courses", params={"keyword": "对齐测试临时课程"}, headers=auth(admin_token))
    check("重置后临时课程已清除", data_of(r.json())["total"] == 0)

    r = client.get("/api/v1/courses", params={"pageSize": 100}, headers=auth(admin_token))
    check("课程数量回到种子状态", data_of(r.json())["total"] == course_total)

    r = client.get("/api/v1/users", headers=auth(admin_token))
    check("重置后管理员仍可正常使用", r.status_code == 200 and data_of(r.json())["total"] == 5)


def main() -> int:
    admin_token, jw_token = scenario_auth()
    scenario_teachers_courses(admin_token)
    scenario_classes(admin_token)
    scenario_dashboard(admin_token)
    scenario_students_payments(admin_token)
    scenario_news_resources(admin_token)
    scenario_settings_users(admin_token, jw_token)
    scenario_align(admin_token, jw_token)

    total = PASSED + len(FAILED)
    print(f"\n===== 冒烟验证：{PASSED}/{total} 通过 =====")
    if FAILED:
        print("失败项：")
        for item in FAILED:
            print(f"  - {item}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())



