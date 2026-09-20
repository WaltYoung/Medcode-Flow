from __future__ import annotations

from datetime import datetime, timedelta, timezone as dt_timezone


def get_current_time(
    *,
    timezone: str = "Asia/Shanghai",
    fmt: str = "%Y-%m-%d %H:%M:%S",
) -> str:
    try:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo(timezone)
    except Exception:
        # Windows without tzdata: fall back to fixed UTC+8 for Asia/Shanghai.
        if timezone in {"Asia/Shanghai", "Asia/Chongqing", "PRC"}:
            tz = dt_timezone(timedelta(hours=8))
        else:
            tz = dt_timezone.utc
    return datetime.now(tz).strftime(fmt)
