import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any

from fastapi import HTTPException, Request, status


def _secret() -> bytes:
    value = os.getenv("APP_AUTH_SECRET") or os.getenv("ADMIN_PANEL_TOKEN") or "tvfiscal-admin-2026"
    return value.encode("utf-8")


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def hash_password(password: str) -> str:
    if not password or len(password) < 6:
        raise ValueError("A senha deve ter pelo menos 6 caracteres.")
    iterations = int(os.getenv("PASSWORD_HASH_ITERATIONS", "210000"))
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str | None) -> bool:
    if not password or not stored_hash:
        return False
    try:
        algorithm, iterations_raw, salt, expected = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_raw)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations).hex()
        return hmac.compare_digest(digest, expected)
    except Exception:
        return False


def create_access_token(payload: dict[str, Any], expires_in_seconds: int | None = None) -> str:
    now = int(time.time())
    ttl = expires_in_seconds or int(os.getenv("APP_AUTH_TOKEN_TTL_SECONDS", str(60 * 60 * 12)))
    token_payload = {
        **payload,
        "iat": now,
        "exp": now + ttl,
        "jti": secrets.token_hex(12),
    }
    raw_payload = _b64url(json.dumps(token_payload, separators=(",", ":"), default=str).encode("utf-8"))
    signature = hmac.new(_secret(), raw_payload.encode("ascii"), hashlib.sha256).digest()
    return f"tvf.{raw_payload}.{_b64url(signature)}"


def decode_access_token(token: str) -> dict[str, Any]:
    if not token or not token.startswith("tvf."):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")
    try:
        _, raw_payload, raw_signature = token.split(".", 2)
        expected = _b64url(hmac.new(_secret(), raw_payload.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(raw_signature, expected):
            raise ValueError("assinatura inválida")
        payload = json.loads(_b64url_decode(raw_payload).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão expirada.")
        return payload
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.") from exc


def get_bearer_token(request: Request) -> str | None:
    header = request.headers.get("Authorization") or ""
    if header.lower().startswith("bearer "):
        return header.split(" ", 1)[1].strip()
    cookie_token = request.cookies.get("tvfiscal_auth_token")
    return cookie_token or None
