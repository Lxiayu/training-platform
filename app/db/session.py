"""数据库会话与引擎：SQLAlchemy 2.0。

- 默认使用 SQLite 文件（data/app.db），零外部依赖即可运行；
- 通过环境变量 QIHANG_DB_URL 可一键切换到 MySQL 8（如
  ``mysql+pymysql://user:pass@host:3306/training_platform?charset=utf8mb4``），
  业务代码无需改动（连接串在 config 中解析）；
- 所有查询走参数化 / ORM，杜绝 SQL 注入。
"""
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import DB_URL

# SQLite 在多线程（uvicorn worker / 测试客户端）下需关闭单线程检查。
_connect_args = {"check_same_thread": False} if DB_URL.startswith("sqlite") else {}

# SQLite 使用单连接池（StaticPool）：所有会话共享同一连接，
# 避免连接池复用导致跨会话「提交不可见 / 更新被静默回滚」的经典坑。
_engine_kwargs = {
    "connect_args": _connect_args,
    "future": True,
}
if DB_URL.startswith("sqlite"):
    _engine_kwargs["poolclass"] = StaticPool

# 确保 SQLite 文件所在目录存在（否则会报 unable to open database file）。
if DB_URL.startswith("sqlite:///"):
    _db_path = Path(DB_URL[len("sqlite:///"):])
    _db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(DB_URL, **_engine_kwargs)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_session() -> Session:
    """请求级会话工厂（依赖注入用）。"""
    return SessionLocal()


def init_db() -> None:
    """建表（幂等）。"""
    import app.db.models  # noqa: F401  确保模型已注册到 Base.metadata

    Base.metadata.create_all(bind=engine)


def reset_schema() -> None:
    """清空所有表（测试隔离用）。"""
    import app.db.models  # noqa: F401

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def data_dir() -> Path:
    return Path(DB_URL.replace("sqlite:///", "")).parent if DB_URL.startswith("sqlite") else Path(".")
