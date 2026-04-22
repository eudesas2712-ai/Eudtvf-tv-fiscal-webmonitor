import hashlib
import re

def normalize_text(s: str) -> str:
    s = s or ""
    s = s.lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s

def fingerprint_text(title: str, body: str) -> str:
    base = normalize_text((title or "") + "\n" + (body or ""))
    return hashlib.sha256(base.encode("utf-8")).hexdigest()