"""数据库会话与引擎：SQLAlchemy 2.0。

- 默认使用 SQLite 文件（data/app.db），零外部依赖即可运行；
- 通过环境变量 QIHANG_DB_URL 可一键切换到 MySQL 8（如
  ``mysql+pymysql://user:pass@host:3306/training_platform?charset=utf8mb4``），
  业务代码无需改动（连接串在 config 中解析）；
- 所有查询走参数化 / ORM，杜绝 SQL 注入。

连接池策略（并发正确性的关键）：

- **文件型 SQLite 用连接池（QueuePool）**：FastAPI 的同步端点在线程池中并发执行
  （前端一次 ``hydrate`` 会并行发出多个请求）。若所有会话共享同一条连接
  （``StaticPool``），多线程会互相干扰查询游标，出现「偶发 401/403、查询返回错行」
  这类诡异问题。改用连接池后每个会话独占连接，互不影响。
- **内存型 SQLite 仍用 ``StaticPool``**：内存库每个连接都是独立数据库，
  必须共享同一连接，否则看不到彼此写入。
- 同时开启 **WAL** 与 ``busy_timeout``，让读不阻塞写、写等待而非直接报错。
"""
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool

from app.core.config import DB_URL

_is_sqlite = DB_URL.startswith("sqlite")
# 内存库形态：sqlite:// 或 sqlite:///:memory:
_is_memory_sqlite = _is_sqlite and (":memory:" in DB_URL or DB_URL.rstrip("/") == "sqlite:")

_connect_args: dict = {}
_engine_kwargs: dict = {"future": True}

if _is_sqlite:
    # SQLite 连接会被 uvicorn 线程池 / 测试客户端跨线程使用，需关闭单线程检查。
    _connect_args["check_same_thread"] = False
    # 写锁等待时间（秒），缓解并发写时的 "database is locked"。
    _connect_args["timeout"] = 30

if _is_memory_sqlite:
    # 内存库必须共享同一连接，否则各连接看到的是不同的空库。
    _engine_kwargs["poolclass"] = StaticPool
elif _is_sqlite:
    # 文件库：每会话独占连接，避免多线程共用连接造成查询串扰。
    _engine_kwargs["poolclass"] = QueuePool
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20
    _engine_kwargs["pool_timeout"] = 30

# 确保 SQLite 文件所在目录存在（否则会报 unable to open database file）。
if DB_URL.startswith("sqlite:///"):
    _db_path = Path(DB_URL[len("sqlite:///"):])
    _db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(DB_URL, connect_args=_connect_args, **_engine_kwargs)


if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _connection_record):  # pragma: no cover
        """连接建立时设置 SQLite 运行参数（仅文件库开启 WAL）。"""
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA busy_timeout=30000")
            if not _is_memory_sqlite:
                # WAL：读写并发，显著降低多请求下的锁冲突
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
        finally:
            cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_session() -> Session:
    """请求级会话工厂（依赖注入用）。"""
    return SessionLocal()


def _ensure_columns() -> None:
    """轻量增量迁移：为 v0.4 已有库补 ``payments.billId``（本项目未引入 Alembic）。

    ``create_all`` 只建缺失的表，不会给已存在的表加列；这里对 SQLite / MySQL
    统一用 ``ALTER TABLE ... ADD COLUMN`` 幂等补齐，避免老库启动即报错。
    """
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "payments" not in set(inspector.get_table_names()):
        return
    columns = {c["name"] for c in inspector.get_columns("payments")}
    if "billId" in columns:
        return
    quote = '"' if engine.dialect.name == "sqlite" else "`"
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE payments ADD COLUMN {quote}billId{quote} VARCHAR(16)"))


def init_db() -> None:
    """建表（幂等），并补齐新增列。"""
    import app.db.models  # noqa: F401  确保模型已注册到 Base.metadata

    Base.metadata.create_all(bind=engine)
    _ensure_columns()


def reset_schema() -> None:
    """清空所有表（测试隔离用）。"""
    import app.db.models  # noqa: F401

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def data_dir() -> Path:
    return Path(DB_URL.replace("sqlite:///", "")).parent if DB_URL.startswith("sqlite") else Path(".")
