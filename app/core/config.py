"""全局配置：路径与令牌参数。

均可通过环境变量覆盖，便于测试与部署：
- QIHANG_DB_FILE      数据文件路径（默认 data/app.json）
- QIHANG_TOKEN_SECRET 令牌签名密钥（演示用默认值，生产必须覆盖）
"""
import os
from pathlib import Path

# 项目根目录：app/core/config.py 向上三级
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 数据目录与文件（已被 .gitignore 的 /data/ 忽略）
DATA_DIR = BASE_DIR / "data"
DB_FILE = Path(os.environ.get("QIHANG_DB_FILE") or (DATA_DIR / "app.json"))

# 前端静态资源目录（main.py 挂载为 /，便于一体化预览）
WEB_DIR = BASE_DIR / "web"

# 轻量令牌参数
TOKEN_SECRET = os.environ.get("QIHANG_TOKEN_SECRET", "qihang-demo-secret-change-me")
TOKEN_TTL_SECONDS = 8 * 3600

# 业务默认值
DEFAULT_USER_PASSWORD = "123456"     # 新建用户 / 重置密码后的初始密码
STUDENT_STATUSES = ("在读", "休学", "已结课")
NEW_STUDENT_STATUS_OPTIONS = ("在读", "休学")
