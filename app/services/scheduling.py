"""排课纯函数：旧排课文本解析、规则展开日期、课次状态判定。

不依赖数据库，便于种子数据生成、存量迁移与单元测试复用。
"""
from __future__ import annotations

import re
from datetime import date, timedelta

# ISO 口径：1=周一 … 7=周日
WEEKDAY_LABELS = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")

_DAY_CHARS = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
    "日": 7, "天": 7,
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7,
}

# 「周六 09:00-10:30」「周一/三/五 09:00-12:00」「星期五 18:30~21:00」
_SCHEDULE_RE = re.compile(
    r"(?P<days>[^0-9]*?(?:周|星期)[一二三四五六日天\d][^0-9]*?)"
    r"\s*(?P<start>\d{1,2}:\d{2})\s*(?:-|~|—|－|至|到)\s*(?P<end>\d{1,2}:\d{2})"
)


def weekday_label(weekday: int) -> str:
    return WEEKDAY_LABELS[weekday - 1] if 1 <= weekday <= 7 else ""


def normalize_time(value: str) -> str:
    """把 ``9:00`` / ``09:00`` 统一为 ``HH:MM``，非法格式抛 ValueError。"""
    m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", value or "")
    if not m:
        raise ValueError("时间格式应为 HH:MM")
    hour, minute = int(m.group(1)), int(m.group(2))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("时间超出范围")
    return f"{hour:02d}:{minute:02d}"


def parse_schedule_text(text: str | None) -> list[dict]:
    """解析存量自由文本排课，返回若干条规则（解析失败返回空列表）。

    支持 ``周六 09:00-10:30``、``周日 09:00-12:00``、``周一/三/五 09:00-12:00``
    等常见写法；多个时间段用「，」分隔时逐段解析。
    """
    if not text:
        return []
    cleaned = (
        text.replace("：", ":")
        .replace("－", "-")
        .replace("—", "-")
        .replace("–", "-")
        .replace("至", "-")
        .replace("到", "-")
    )
    rules: list[dict] = []
    seen: set[tuple[int, str, str]] = set()
    for segment in re.split(r"[，,；;]", cleaned):
        m = _SCHEDULE_RE.search(segment)
        if not m:
            continue
        weekdays: list[int] = []
        for ch in m.group("days"):
            num = _DAY_CHARS.get(ch)
            if num and num not in weekdays:
                weekdays.append(num)
        if not weekdays:
            continue
        try:
            start = normalize_time(m.group("start"))
            end = normalize_time(m.group("end"))
        except ValueError:
            continue
        if end <= start:
            continue
        for weekday in sorted(weekdays):
            key = (weekday, start, end)
            if key in seen:
                continue
            seen.add(key)
            rules.append({"weekday": weekday, "startTime": start, "endTime": end})
    return rules


def expand_dates(weekday: int, start: date, end: date) -> list[date]:
    """展开区间内所有匹配 weekday 的日期（含首尾，最多 400 天防御）。"""
    if start > end:
        return []
    span = min((end - start).days, 400)
    end = start + timedelta(days=span)
    result: list[date] = []
    cursor = start
    while cursor <= end:
        if cursor.isoweekday() == weekday:
            result.append(cursor)
        cursor += timedelta(days=1)
    return result


def session_status(session_date: date, today: date) -> str:
    return "已上课" if session_date < today else "待上课"


def parse_date(value: str, *, label: str = "日期") -> date:
    """严格解析 YYYY-MM-DD；失败抛 ValueError（由调用方转业务异常）。"""
    try:
        return date.fromisoformat(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(f"{label}格式应为 YYYY-MM-DD")
