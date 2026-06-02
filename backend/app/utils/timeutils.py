from __future__ import annotations

import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from dateutil import parser

DEFAULT_APP_TIMEZONE = "America/Sao_Paulo"


def app_timezone_name() -> str:
    return os.getenv("APP_TIMEZONE") or os.getenv("TZ") or DEFAULT_APP_TIMEZONE


def app_timezone() -> ZoneInfo:
    try:
        return ZoneInfo(app_timezone_name())
    except Exception:
        return ZoneInfo(DEFAULT_APP_TIMEZONE)


def utc_now() -> datetime:
    """UTC sem timezone para manter compatibilidade com colunas DateTime existentes."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def as_utc(dt: datetime | None) -> datetime | None:
    if not dt:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def to_local(dt: datetime | None) -> datetime | None:
    if not dt:
        return None
    return as_utc(dt).astimezone(app_timezone())


def iso_local(dt: datetime | None) -> str | None:
    local = to_local(dt)
    return local.isoformat(timespec="seconds") if local else None


def display_local(dt: datetime | None) -> str:
    local = to_local(dt)
    return local.strftime("%d/%m/%Y, %H:%M:%S") if local else "—"


def parse_dt(s: str):
    if not s:
        return None
    try:
        dt = parser.parse(s)
        if not getattr(dt, "tzinfo", None):
            return dt
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        return None
