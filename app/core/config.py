"""全局配置：路径与令牌参数。

均可通过环境变量覆盖，便于测试与部署：
- QIHANG_DB_URL        SQLAlchemy 数据库 URL（默认 data/app.db 的 SQLite）
                       生产可切 MySQL：mysql+pymysql://user:pass@host:3306/training_platform?charset=utf8mb4
- QIHANG_DB_FILE       （兼容）仅用于旧版 JSON 引擎，新版本忽略
- QIHANG_TOKEN_SECRET 令牌签名密钥（演示用默认值，生产必须覆盖）
"""
import os
from datetime import datetime, timezone
from pathlib import Path

# 项目根目录：app/core/config.py 向上三级
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 数据目录与文件（已被 .gitignore 的 /data/ 忽略）
DATA_DIR = BASE_DIR / "data"
DB_FILE = Path(os.environ.get("QIHANG_DB_FILE") or (DATA_DIR / "app.json"))

# 数据库 URL：默认 SQLite 文件库；可通过环境变量切换到 MySQL 等
DB_URL = os.environ.get("QIHANG_DB_URL") or f"sqlite:///{DATA_DIR / 'app.db'}"

# 前端静态资源目录（main.py 挂载为 /，便于一体化预览）
WEB_DIR = BASE_DIR / "web"

# 轻量令牌参数
TOKEN_SECRET = os.environ.get("QIHANG_TOKEN_SECRET", "qihang-demo-secret-change-me")
TOKEN_TTL_SECONDS = 8 * 3600

# 业务默认值
DEFAULT_USER_PASSWORD = "123456"     # 新建用户 / 重置密码后的初始密码
STUDENT_STATUSES = ("在读", "休学", "已结课")
NEW_STUDENT_STATUS_OPTIONS = ("在读", "休学")


def now_iso() -> str:
    """统一的本地时区时间戳（与种子/审计列一致）。"""
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


# 四类登录身份（账号 identity 字段取值）
IDENTITY_STAFF = "staff"        # 后台员工（超级管理员 / 教务 / 财务 / 前台 / 教师岗）
IDENTITY_TEACHER = "teacher"    # 教师门户
IDENTITY_STUDENT = "student"    # 学员门户
IDENTITY_PARENT = "parent"      # 家长门户
IDENTITIES = (IDENTITY_STAFF, IDENTITY_TEACHER, IDENTITY_STUDENT, IDENTITY_PARENT)

# 员工（staff）职务角色：users.role 取值，即《02-总体设计》§4.3 权限矩阵的列维度。
# require_roles 据此在接口层做细粒度授权；前端按同一矩阵隐藏入口（仅体验优化）。
ROLE_ADMIN = "超级管理员"        # 全部模块，含用户管理 / 系统设置
ROLE_ACADEMIC = "教务管理员"     # 教师 / 课程 / 班级 / 学员写操作、新闻发布、资源管理
ROLE_FINANCE = "财务专员"        # 缴费写操作（登记 / 确认 / 作废 / 删除）
ROLE_FRONTDESK = "前台接待"      # 学员报名（学员写操作）
ROLE_TEACHER = "教师"            # 员工教师岗（staff 身份）：课件资源上传
STAFF_ROLES = (ROLE_ADMIN, ROLE_ACADEMIC, ROLE_FINANCE, ROLE_FRONTDESK, ROLE_TEACHER)
