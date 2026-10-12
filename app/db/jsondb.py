"""JSON 文件存储引擎。

设计要点：
- 单文件 data/app.json（可用环境变量 QIHANG_DB_FILE 覆盖，供测试隔离）；
- 全局 RLock 串行化全部读写，修复原型 nextId() 的并发重号缺陷；
- 原子落盘：先写临时文件再 os.replace，进程中断不会损坏数据文件；
- 软删除：记录标记 deletedAt，业务查询统一过滤，为恢复/审计留扩展；
- transaction()：一个上下文内多次修改只落盘一次，异常自动回滚快照。

users 集合以 username 为主键，其余集合以业务编号（如 JS001）为主键。
"""
import copy
import json
import os
import tempfile
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from app.core.config import DB_FILE
from app.core.exceptions import BizException

COLLECTIONS = ("users", "teachers", "courses", "classes", "students", "payments", "news", "resources")
# 各集合的主键字段名
KEY_OF = {name: ("username" if name == "users" else "id") for name in COLLECTIONS}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


class JsonDB:
    def __init__(self, path: Path | str = DB_FILE) -> None:
        self._path = Path(path)
        self._lock = threading.RLock()
        self._data: dict[str, Any] | None = None

    # ---------- 生命周期 ----------

    def load(self) -> dict[str, Any]:
        with self._lock:
            if self._data is None:
                if self._path.exists():
                    self._data = json.loads(self._path.read_text(encoding="utf-8"))
                else:
                    from app.db.seed import build_seed_db
                    self._data = build_seed_db()
                    self._flush()
            return self._data

    def reset(self) -> dict[str, Any]:
        """用种子数据覆盖当前数据（对应前端「重置演示数据」入口）。"""
        from app.db.seed import build_seed_db
        with self._lock:
            self._data = build_seed_db()
            self._flush()
            return self._data

    def _flush(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(self._path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, ensure_ascii=False, indent=2)
            os.replace(tmp, self._path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    def save(self) -> None:
        with self._lock:
            self.load()
            self._flush()

    @contextmanager
    def transaction(self) -> Iterator[dict[str, Any]]:
        """事务：块内修改一次落盘；任何异常回滚到进入前快照。"""
        with self._lock:
            data = self.load()
            snapshot = copy.deepcopy(data)
            try:
                yield data
                self._flush()
            except Exception:
                self._data = snapshot
                raise

    # ---------- 集合读取 ----------

    def alive(self, coll: str) -> list[dict[str, Any]]:
        """未删除记录（业务可见数据）。"""
        return [r for r in self.load().get(coll, []) if not r.get("deletedAt")]

    def raw(self, coll: str) -> list[dict[str, Any]]:
        """含软删记录（取号时用于避免编号复用）。"""
        return self.load().get(coll, [])

    def find(self, coll: str, code: str) -> dict[str, Any] | None:
        key = KEY_OF.get(coll, "id")
        for rec in self.alive(coll):
            if rec.get(key) == code:
                return rec
        return None

    def locate(self, coll: str, code: str, *, label: str = "记录") -> dict[str, Any]:
        """定位未删除记录，不存在抛 404。"""
        rec = self.find(coll, code)
        if rec is None:
            raise BizException(404, f"{label}不存在或已被删除")
        return rec

    # ---------- 单条写入 ----------

    def insert(self, coll: str, record: dict[str, Any]) -> dict[str, Any]:
        with self.transaction() as data:
            data[coll].append(record)
        return record

    def update_fields(self, coll: str, code: str, fields: dict[str, Any], *, label: str = "记录") -> dict[str, Any]:
        with self.transaction():
            rec = self.locate(coll, code, label=label)
            rec.update(fields)
        return rec

    def soft_delete(self, coll: str, code: str, *, label: str = "记录") -> dict[str, Any]:
        with self.transaction():
            rec = self.locate(coll, code, label=label)
            rec["deletedAt"] = now_iso()
        return rec

    def next_code(self, coll: str, prefix: str) -> str:
        """生成下一个业务编号：prefix + 三位递增数字（扫描含软删记录防复用）。"""
        with self._lock:
            key = KEY_OF.get(coll, "id")
            best = 0
            for rec in self.raw(coll):
                code = str(rec.get(key, ""))
                tail = code[len(prefix):]
                if code.startswith(prefix) and tail.isdigit():
                    best = max(best, int(tail))
            return f"{prefix}{best + 1:03d}"

    # ---------- 顶层配置 ----------

    @property
    def org(self) -> dict[str, Any]:
        return self.load()["org"]

    @property
    def settings(self) -> dict[str, Any]:
        return self.load()["settings"]

    def save_settings(self, org_patch: dict[str, Any], settings_patch: dict[str, Any]) -> dict[str, Any]:
        with self.transaction() as data:
            data["org"].update(org_patch)
            data["settings"].update(settings_patch)
        return {"org": self.org, "settings": self.settings}


db = JsonDB()
