"""种子数据：与 web/js/data.js 的 DEFAULT_DB 完全一致（2026 秋季学期背景）。

与前端原型的差异（有意为之）：
- 密码不再明文落盘，初始化时转为 PBKDF2 哈希（passwordHash 字段）；
- 每条记录补充 createdAt / updatedAt 时间戳（前端不展示，留审计用）；
- 字段命名保持前端 camelCase（desc、parentPhone 等），迁移 MySQL 时
  再按《01-数据库设计》映射为下划线列名。
"""
from typing import Any

from app.core.security import hash_password
from app.db.jsondb import now_iso

_ORG: dict[str, Any] = {
    "name": "启航编程教育",
    "phone": "0571-88886666",
    "address": "杭州市西湖区文三路 100 号 启航大厦 3 楼",
    "intro": "专注 6-18 岁青少年编程教育，课程覆盖 Scratch、Python、C++ 信奥、人工智能启蒙、Web 前端与机器人方向。",
}

_SETTINGS: dict[str, Any] = {
    "allowLeave": True,         # 允许学员自助请假
    "scheduleRemind": True,     # 上课前自动推送课表提醒
    "receiptPrint": False,      # 缴费后自动打印收据
    "newStudentStatus": "在读",  # 新学员默认状态
}

# 明文密码仅在此处出现一次，落盘前即转哈希
_USERS: list[dict[str, Any]] = [
    {"username": "admin",   "password": "admin123", "name": "张明远", "role": "超级管理员", "phone": "13800000001", "email": "admin@qihangcode.cn",   "joinDate": "2024-01-10", "status": "启用"},
    {"username": "jiaowu",  "password": "123456",   "name": "李文静", "role": "教务管理员", "phone": "13800000002", "email": "jiaowu@qihangcode.cn",  "joinDate": "2024-03-15", "status": "启用"},
    {"username": "caiwu",   "password": "123456",   "name": "周慧敏", "role": "财务专员",   "phone": "13800000003", "email": "caiwu@qihangcode.cn",   "joinDate": "2024-06-01", "status": "启用"},
    {"username": "qiantai", "password": "123456",   "name": "刘晓燕", "role": "前台接待",   "phone": "13800000004", "email": "qiantai@qihangcode.cn", "joinDate": "2025-02-10", "status": "启用"},
    {"username": "wangzq",  "password": "123456",   "name": "王志强", "role": "教师",       "phone": "13957100001", "email": "wangzq@qihangcode.cn",  "joinDate": "2021-03-15", "status": "禁用"},
]

_TEACHERS: list[dict[str, Any]] = [
    {"id": "JS001", "name": "王志强", "gender": "男", "phone": "13957100001", "email": "wangzq@qihangcode.cn", "subject": "Python", "title": "高级讲师", "hireDate": "2021-03-15", "status": "在职"},
    {"id": "JS002", "name": "林晓芸", "gender": "女", "phone": "13957100002", "email": "linxy@qihangcode.cn", "subject": "Scratch", "title": "讲师", "hireDate": "2022-06-01", "status": "在职"},
    {"id": "JS003", "name": "陈国栋", "gender": "男", "phone": "13957100003", "email": "chengd@qihangcode.cn", "subject": "C++", "title": "金牌竞赛教练", "hireDate": "2020-09-10", "status": "在职"},
    {"id": "JS004", "name": "赵雨桐", "gender": "女", "phone": "13957100004", "email": "zhaoyt@qihangcode.cn", "subject": "人工智能", "title": "讲师", "hireDate": "2023-02-20", "status": "在职"},
    {"id": "JS005", "name": "孙浩然", "gender": "男", "phone": "13957100005", "email": "sunhr@qihangcode.cn", "subject": "Web", "title": "讲师", "hireDate": "2022-11-05", "status": "在职"},
    {"id": "JS006", "name": "周美琳", "gender": "女", "phone": "13957100006", "email": "zhouml@qihangcode.cn", "subject": "机器人", "title": "助教", "hireDate": "2024-07-08", "status": "在职"},
    {"id": "JS007", "name": "吴建军", "gender": "男", "phone": "13957100007", "email": "wujj@qihangcode.cn", "subject": "Java", "title": "讲师", "hireDate": "2019-04-18", "status": "离职"},
]

_COURSES: list[dict[str, Any]] = [
    {"id": "KC001", "name": "Scratch 趣味编程启蒙", "category": "Scratch", "level": "启蒙", "hours": 32, "price": 2400, "target": "6-9 岁，零基础", "status": "在售", "desc": "拖拽积木式编程，培养逻辑思维与创作兴趣，完成互动故事与小游戏作品。"},
    {"id": "KC002", "name": "Python 零基础入门", "category": "Python", "level": "入门", "hours": 48, "price": 3600, "target": "10-15 岁，零基础", "status": "在售", "desc": "学习变量、循环、函数等基础语法，完成计算器、猜数字等小项目。"},
    {"id": "KC003", "name": "Python 进阶与数据处理", "category": "Python", "level": "进阶", "hours": 60, "price": 4800, "target": "已完成 Python 入门", "status": "在售", "desc": "面向对象、文件处理、爬虫入门与数据可视化综合实战。"},
    {"id": "KC004", "name": "C++ 信息学奥赛（CSP-J）", "category": "C++", "level": "竞赛", "hours": 72, "price": 6800, "target": "五年级以上，有编程基础", "status": "在售", "desc": "系统学习 C++ 语法、数据结构与算法，备战 CSP-J/S 入门级认证。"},
    {"id": "KC005", "name": "人工智能启蒙（AI）", "category": "人工智能", "level": "启蒙", "hours": 36, "price": 3200, "target": "8-12 岁", "status": "在售", "desc": "认识机器学习基本概念，动手训练自己的图像识别小模型。"},
    {"id": "KC006", "name": "Web 前端开发实战", "category": "Web", "level": "进阶", "hours": 56, "price": 5200, "target": "12 岁以上", "status": "在售", "desc": "HTML / CSS / JavaScript 全流程，独立开发个人网站与网页应用。"},
    {"id": "KC007", "name": "机器人搭建与编程", "category": "机器人", "level": "入门", "hours": 40, "price": 3800, "target": "7-11 岁", "status": "在售", "desc": "机械结构搭建 + 图形化编程，锻炼动手能力与工程思维。"},
    {"id": "KC008", "name": "Java 计算思维养成", "category": "Java", "level": "入门", "hours": 48, "price": 4200, "target": "13 岁以上", "status": "停售", "desc": "面向对象编程思想训练，为后续深入学习打下基础。"},
]

_CLASSES: list[dict[str, Any]] = [
    {"id": "BJ001", "name": "Scratch 周六启蒙 A 班", "courseId": "KC001", "teacherId": "JS002", "classroom": "A101", "schedule": "周六 09:00-10:30", "capacity": 16, "startDate": "2026-09-05", "endDate": "2026-12-19", "status": "进行中"},
    {"id": "BJ002", "name": "Python 入门 · 周日班", "courseId": "KC002", "teacherId": "JS001", "classroom": "B203", "schedule": "周日 09:00-12:00", "capacity": 20, "startDate": "2026-09-06", "endDate": "2026-12-20", "status": "进行中"},
    {"id": "BJ003", "name": "Python 入门 · 周五晚班", "courseId": "KC002", "teacherId": "JS001", "classroom": "B203", "schedule": "周五 18:30-21:00", "capacity": 20, "startDate": "2026-09-04", "endDate": "2026-12-18", "status": "进行中"},
    {"id": "BJ004", "name": "C++ 信奥秋季集训班", "courseId": "KC004", "teacherId": "JS003", "classroom": "C305", "schedule": "周六 13:30-17:30", "capacity": 24, "startDate": "2026-09-12", "endDate": "2027-01-10", "status": "进行中"},
    {"id": "BJ005", "name": "AI 启蒙 · 周六班", "courseId": "KC005", "teacherId": "JS004", "classroom": "A102", "schedule": "周六 10:40-12:10", "capacity": 16, "startDate": "2026-10-17", "endDate": "2027-01-23", "status": "未开班"},
    {"id": "BJ006", "name": "Web 前端暑期班", "courseId": "KC006", "teacherId": "JS005", "classroom": "C305", "schedule": "周一/三/五 09:00-12:00", "capacity": 20, "startDate": "2026-07-06", "endDate": "2026-08-28", "status": "已结课"},
]

_STUDENTS: list[dict[str, Any]] = [
    {"id": "XS001", "name": "陈一诺", "gender": "女", "grade": "三年级", "parent": "陈大文", "parentPhone": "15868710001", "classId": "BJ001", "enrollDate": "2026-08-20", "status": "在读"},
    {"id": "XS002", "name": "黄子睿", "gender": "男", "grade": "二年级", "parent": "黄志伟", "parentPhone": "15868710002", "classId": "BJ001", "enrollDate": "2026-08-22", "status": "在读"},
    {"id": "XS003", "name": "林诗涵", "gender": "女", "grade": "三年级", "parent": "林建国", "parentPhone": "15868710003", "classId": "BJ001", "enrollDate": "2026-08-25", "status": "在读"},
    {"id": "XS004", "name": "徐浩宇", "gender": "男", "grade": "四年级", "parent": "徐鹏", "parentPhone": "15868710004", "classId": "BJ001", "enrollDate": "2026-09-01", "status": "在读"},
    {"id": "XS005", "name": "李思远", "gender": "男", "grade": "初一", "parent": "李国豪", "parentPhone": "15868710005", "classId": "BJ002", "enrollDate": "2026-08-15", "status": "在读"},
    {"id": "XS006", "name": "王雨欣", "gender": "女", "grade": "六年级", "parent": "王建军", "parentPhone": "15868710006", "classId": "BJ002", "enrollDate": "2026-08-18", "status": "在读"},
    {"id": "XS007", "name": "张一鸣", "gender": "男", "grade": "初二", "parent": "张伟", "parentPhone": "15868710007", "classId": "BJ002", "enrollDate": "2026-08-28", "status": "在读"},
    {"id": "XS008", "name": "刘美琪", "gender": "女", "grade": "初一", "parent": "刘强", "parentPhone": "15868710008", "classId": "BJ002", "enrollDate": "2026-09-03", "status": "在读"},
    {"id": "XS009", "name": "周子墨", "gender": "男", "grade": "六年级", "parent": "周涛", "parentPhone": "15868710009", "classId": "BJ003", "enrollDate": "2026-08-30", "status": "在读"},
    {"id": "XS010", "name": "吴佳怡", "gender": "女", "grade": "初一", "parent": "吴斌", "parentPhone": "15868710010", "classId": "BJ003", "enrollDate": "2026-09-05", "status": "在读"},
    {"id": "XS011", "name": "郑天佑", "gender": "男", "grade": "五年级", "parent": "郑成", "parentPhone": "15868710011", "classId": "BJ003", "enrollDate": "2026-09-08", "status": "休学"},
    {"id": "XS012", "name": "孙铭泽", "gender": "男", "grade": "初二", "parent": "孙立", "parentPhone": "15868710012", "classId": "BJ004", "enrollDate": "2026-08-10", "status": "在读"},
    {"id": "XS013", "name": "马悦然", "gender": "女", "grade": "初一", "parent": "马啸", "parentPhone": "15868710013", "classId": "BJ004", "enrollDate": "2026-08-12", "status": "在读"},
    {"id": "XS014", "name": "朱柏宇", "gender": "男", "grade": "初三", "parent": "朱宏", "parentPhone": "15868710014", "classId": "BJ004", "enrollDate": "2026-09-10", "status": "在读"},
    {"id": "XS015", "name": "何静怡", "gender": "女", "grade": "高一", "parent": "何强", "parentPhone": "15868710015", "classId": "BJ006", "enrollDate": "2026-06-20", "status": "已结课"},
    {"id": "XS016", "name": "罗一鸣", "gender": "男", "grade": "高二", "parent": "罗刚", "parentPhone": "15868710016", "classId": "BJ006", "enrollDate": "2026-06-22", "status": "已结课"},
]

_PAYMENTS: list[dict[str, Any]] = [
    {"id": "JF001", "studentId": "XS001", "classId": "BJ001", "amount": 2400, "method": "微信",     "date": "2026-08-20", "status": "已支付", "note": "秋季班学费"},
    {"id": "JF002", "studentId": "XS002", "classId": "BJ001", "amount": 2400, "method": "支付宝",   "date": "2026-08-22", "status": "已支付", "note": "秋季班学费"},
    {"id": "JF003", "studentId": "XS003", "classId": "BJ001", "amount": 2400, "method": "微信",     "date": "2026-08-25", "status": "已支付", "note": "秋季班学费"},
    {"id": "JF004", "studentId": "XS004", "classId": "BJ001", "amount": 1200, "method": "现金",     "date": "2026-09-01", "status": "待确认", "note": "报名定金，余款待缴"},
    {"id": "JF005", "studentId": "XS005", "classId": "BJ002", "amount": 3600, "method": "微信",     "date": "2026-08-15", "status": "已支付", "note": "秋季班学费"},
    {"id": "JF006", "studentId": "XS006", "classId": "BJ002", "amount": 3600, "method": "支付宝",   "date": "2026-08-18", "status": "已支付", "note": "秋季班学费"},
    {"id": "JF007", "studentId": "XS007", "classId": "BJ002", "amount": 3600, "method": "银行转账", "date": "2026-08-28", "status": "已支付", "note": "秋季班学费"},
    {"id": "JF008", "studentId": "XS008", "classId": "BJ002", "amount": 1800, "method": "微信",     "date": "2026-09-03", "status": "待确认", "note": "分期第一期"},
    {"id": "JF009", "studentId": "XS009", "classId": "BJ003", "amount": 3600, "method": "微信",     "date": "2026-08-30", "status": "已支付", "note": "秋季班学费"},
    {"id": "JF010", "studentId": "XS010", "classId": "BJ003", "amount": 3600, "method": "支付宝",   "date": "2026-09-05", "status": "已支付", "note": "秋季班学费"},
    {"id": "JF011", "studentId": "XS011", "classId": "BJ003", "amount": 3600, "method": "微信",     "date": "2026-09-08", "status": "已退款", "note": "学员休学，全额退费"},
    {"id": "JF012", "studentId": "XS012", "classId": "BJ004", "amount": 6800, "method": "银行转账", "date": "2026-08-10", "status": "已支付", "note": "秋季集训学费"},
    {"id": "JF013", "studentId": "XS013", "classId": "BJ004", "amount": 6800, "method": "微信",     "date": "2026-08-12", "status": "已支付", "note": "秋季集训学费"},
    {"id": "JF014", "studentId": "XS014", "classId": "BJ004", "amount": 6800, "method": "银行转账", "date": "2026-09-10", "status": "已支付", "note": "秋季集训学费"},
    {"id": "JF015", "studentId": "XS015", "classId": "BJ006", "amount": 5200, "method": "微信",     "date": "2026-06-20", "status": "已支付", "note": "暑期班学费"},
    {"id": "JF016", "studentId": "XS016", "classId": "BJ006", "amount": 5200, "method": "支付宝",   "date": "2026-06-22", "status": "已支付", "note": "暑期班学费"},
    {"id": "JF017", "studentId": "XS005", "classId": "BJ002", "amount": 600,  "method": "现金",     "date": "2026-09-15", "status": "已支付", "note": "教材费补缴"},
    {"id": "JF018", "studentId": "XS012", "classId": "BJ004", "amount": 800,  "method": "微信",     "date": "2026-09-18", "status": "已支付", "note": "竞赛模拟赛报名费"},
]

_NEWS: list[dict[str, Any]] = [
    {"id": "XW001", "title": "2026 秋季班全面开班：Python / C++ 信奥热门班级仅剩少量余位", "category": "开班信息", "top": True,  "date": "2026-09-02", "author": "张明远", "views": 486, "status": "已发布",
     "summary": "秋季学期各班级已陆续开课，Python 入门周日班、C++ 信奥秋季集训班报名火爆，目前仅剩少量余位，欢迎新老学员咨询。",
     "content": [
         "新学期伊始，启航编程 2026 秋季班已全面开班。本学期共开设 Scratch、Python、C++ 信奥、人工智能启蒙、Web 前端等六大方向 16 个班级，在读学员突破 400 人。",
         "其中 Python 零基础入门周日班、C++ 信息学奥赛（CSP-J）秋季集训班报名情况最为火爆，两类班级目前仅剩少量余位。有意向的家长可致电 0571-88886666 或到前台咨询详情。",
         "尚未报名的学员可根据自身基础选择合适班型：零基础学员推荐从 Scratch 启蒙或 Python 入门起步；有编程基础、希望冲刺竞赛的学员可预约陈国栋教练的 C++ 信奥集训班入学测评。",
         "秋季班课程表已同步更新至「班级管理」模块，学员家长可联系班主任获取详细上课时间安排。",
     ]},
    {"id": "XW002", "title": "喜报！我机构 6 名学员晋级 CSP-J/S 复赛", "category": "比赛获奖", "top": False, "date": "2026-09-25", "author": "陈国栋", "views": 352, "status": "已发布",
     "summary": "在刚公布的 CSP-J/S 2026 第一轮认证成绩中，我机构 6 名学员成功晋级第二轮（复赛），创历史最好成绩。",
     "content": [
         "9 月 24 日，CCF CSP-J/S 2026 第一轮认证成绩公布，启航编程信奥集训班共 6 名学员成功晋级第二轮认证，其中孙铭泽、朱柏宇两名学员入门级成绩突破 200 分，创机构历史最好成绩。",
         "本次晋级的 6 名学员均来自陈国栋教练执教的 C++ 信奥秋季集训班，备赛期间坚持每周 6 小时高强度训练，累计完成模拟赛 12 场、专项题单 300 余道。",
         "第二轮认证将于 10 月底举行，集训班将进入冲刺阶段，针对动态规划、图论等高频考点开展专题突破。祝愿晋级学员再创佳绩！",
     ]},
    {"id": "XW003", "title": "「编程奇妙夜」中秋亲子体验活动圆满举办", "category": "活动通知", "top": False, "date": "2026-09-15", "author": "林晓芸", "views": 275, "status": "已发布",
     "summary": "9 月 14 日晚，中秋亲子编程体验活动在机构一层多功能厅举行，60 余组家庭参与了 Scratch 月兔奔月挑战。",
     "content": [
         "9 月 14 日晚，启航编程「编程奇妙夜」中秋亲子体验活动在机构一层多功能厅热闹举行，共有 60 余组家庭到场参与。",
         "活动以「月兔奔月」为主题，家长与孩子组队用 Scratch 完成闯关小游戏：从控制月兔躲避陨石，到设计属于自己的广寒宫场景，孩子们在欢声笑语中体验了编程的乐趣。",
         "活动现场还为每组家庭拍摄了中秋主题合影，并赠送了定制月饼礼盒。不少家长表示，这是孩子第一次独立完成一个完整的小作品，非常有成就感。",
         "下一场亲子体验活动计划于万圣节周末举办，敬请关注公众号后续通知。",
     ]},
    {"id": "XW004", "title": "新课程上线：人工智能启蒙（AI）系列课", "category": "机构动态", "top": False, "date": "2026-09-10", "author": "赵雨桐", "views": 198, "status": "已发布",
     "summary": "面向 8-12 岁青少年的人工智能启蒙课程正式上线，孩子们将亲手训练自己的图像识别小模型。",
     "content": [
         "经过三个月的课程研发与试讲打磨，启航编程「人工智能启蒙（AI）」系列课于本学期正式上线，首期周六班将于 10 月 17 日开课。",
         "课程共 36 课时，围绕「看见 AI、理解 AI、创造 AI」三个阶段展开：从认识生活中的智能应用，到理解机器学习的基本原理，最后动手训练专属的图像识别模型。",
         "课程由人工智能方向讲师赵雨桐主讲，采用「不插电 + 上机」结合的教学方式，无需任何编程基础。首期班级开放 16 个名额，目前剩余 9 个。",
     ]},
    {"id": "XW005", "title": "关于国庆节放假及课程调整安排的通知", "category": "活动通知", "top": False, "date": "2026-09-26", "author": "李文静", "views": 413, "status": "已发布",
     "summary": "国庆假期（10 月 1 日—7 日）全机构停课，10 月 4 日（周日）原课程顺延或调至线上，详见正文安排。",
     "content": [
         "根据国家法定节假日安排，结合机构实际，现将 2026 年国庆节放假及课程调整安排通知如下：",
         "一、10 月 1 日（周四）至 10 月 7 日（周三）全体班级停课放假；",
         "二、10 月 3 日（周六）、10 月 4 日（周日）原周末课程统一顺延一周，如有特殊安排以班主任通知为准；",
         "三、假期期间机构前台正常值班（10:00-16:00），报名咨询、缴费业务均可正常办理；",
         "四、10 月 8 日（周四）起所有课程恢复正常。祝各位学员和家长节日愉快！",
     ]},
    {"id": "XW006", "title": "Python 入门班学员作品展示：小创意大能量", "category": "机构动态", "top": False, "date": "2026-09-18", "author": "王志强", "views": 241, "status": "已发布",
     "summary": "Python 入门班学员本周完成了结课作品展示，从猜数字到成语接龙，14 个小项目各具巧思。",
     "content": [
         "本周，Python 入门周日班与周五晚班联合举办了阶段作品展示课，14 名学员依次上台演示了自己的编程小项目。",
         "张一鸣同学的「成语接龙闯关」将语文知识融入程序逻辑，设计了三级难度；王雨欣同学的「校园失物招领助手」用字典实现了登记与检索，赢得了全班掌声。",
         "「孩子们不仅写出了能跑的程序，更学会了把生活中的问题拆解成计算机能理解的任务，这正是编程思维的价值。」任课教师王志强评价道。",
         "作品源代码已上传至「课件资源」模块，学员和家长可登录系统查看。",
     ]},
]

_RESOURCES: list[dict[str, Any]] = [
    {"id": "ZY001", "title": "第1讲 初识 Python 与开发环境搭建", "type": "课件PPT", "courseId": "KC002", "teacherId": "JS001", "size": "8.2 MB", "duration": "", "downloads": 156, "date": "2026-09-06", "status": "已发布"},
    {"id": "ZY002", "title": "第3讲 变量与数据类型（含课堂练习）", "type": "课件PPT", "courseId": "KC002", "teacherId": "JS001", "size": "11.6 MB", "duration": "", "downloads": 132, "date": "2026-09-13", "status": "已发布"},
    {"id": "ZY003", "title": "循环结构精讲 · 名师教学录像", "type": "教学视频", "courseId": "KC002", "teacherId": "JS001", "size": "326 MB", "duration": "42 分钟", "downloads": 98, "date": "2026-09-15", "status": "已发布"},
    {"id": "ZY004", "title": "Scratch 舞台与角色入门示范课录像", "type": "教学视频", "courseId": "KC001", "teacherId": "JS002", "size": "512 MB", "duration": "38 分钟", "downloads": 87, "date": "2026-09-08", "status": "已发布"},
    {"id": "ZY005", "title": "CSP-J 入门级语法专项习题册（含解析）", "type": "习题册", "courseId": "KC004", "teacherId": "JS003", "size": "2.6 MB", "duration": "", "downloads": 204, "date": "2026-09-12", "status": "已发布"},
    {"id": "ZY006", "title": "Python 入门综合测试卷 A / B 卷", "type": "习题册", "courseId": "KC002", "teacherId": "JS001", "size": "1.8 MB", "duration": "", "downloads": 118, "date": "2026-09-18", "status": "已发布"},
    {"id": "ZY007", "title": "机器人课程机械结构素材包（图纸+3D）", "type": "素材包", "courseId": "KC007", "teacherId": "JS006", "size": "128 MB", "duration": "", "downloads": 64, "date": "2026-09-05", "status": "已发布"},
    {"id": "ZY008", "title": "AI 启蒙：什么是机器学习（教师版）", "type": "课件PPT", "courseId": "KC005", "teacherId": "JS004", "size": "14.3 MB", "duration": "", "downloads": 45, "date": "2026-09-20", "status": "已发布"},
    {"id": "ZY009", "title": "Web 前端暑期班结课作品路演全程录像", "type": "教学视频", "courseId": "KC006", "teacherId": "JS005", "size": "754 MB", "duration": "65 分钟", "downloads": 73, "date": "2026-08-30", "status": "已发布"},
    {"id": "ZY010", "title": "Scratch 主题素材合集：太空探险", "type": "素材包", "courseId": "KC001", "teacherId": "JS002", "size": "86 MB", "duration": "", "downloads": 121, "date": "2026-09-10", "status": "已发布"},
]


def _stamped(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """为种子记录补 createdAt / updatedAt 时间戳。"""
    ts = now_iso()
    return [{**row, "createdAt": ts, "updatedAt": ts} for row in rows]


def build_seed_db() -> dict[str, Any]:
    """构建完整初始数据库（明文密码在此转为哈希后返回）。"""
    ts = now_iso()
    users = [
        {
            "username": u["username"],
            "passwordHash": hash_password(u["password"]),
            "name": u["name"],
            "role": u["role"],
            "phone": u["phone"],
            "email": u["email"],
            "joinDate": u["joinDate"],
            "status": u["status"],
            "createdAt": ts,
            "updatedAt": ts,
        }
        for u in _USERS
    ]
    return {
        "org": dict(_ORG),
        "settings": dict(_SETTINGS),
        "users": users,
        "teachers": _stamped(_TEACHERS),
        "courses": _stamped(_COURSES),
        "classes": _stamped(_CLASSES),
        "students": _stamped(_STUDENTS),
        "payments": _stamped(_PAYMENTS),
        "news": _stamped(_NEWS),
        "resources": _stamped(_RESOURCES),
        "meta": {"version": 2, "generatedAt": ts},
    }



