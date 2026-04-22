from datetime import datetime
from dateutil import parser

def parse_dt(s: str):
    if not s:
        return None
    try:
        dt = parser.parse(s)
        if not getattr(dt, "tzinfo", None):
            return dt
        return dt.replace(tzinfo=None)
    except Exception:
        return None