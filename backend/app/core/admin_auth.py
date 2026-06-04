import hmac
import os

from fastapi import HTTPException, Request, status

from app.core.security import decode_access_token, get_bearer_token


def auth_enforcement_mode() -> str:
    return (os.getenv("AUTH_ENFORCEMENT_MODE") or "compat").strip().lower()


def allow_admin_token_query() -> bool:
    raw = os.getenv("ALLOW_ADMIN_TOKEN_QUERY")
    if raw is not None:
        return raw.strip().lower() in {"1", "true", "yes", "on"}

    # Compatibilidade local: em strict/produção, query string não deve autenticar admin.
    return auth_enforcement_mode() != "strict"


def get_admin_token() -> str:
    # ADMIN_TOKEN é o nome oficial do token administrativo.
    return (os.getenv("ADMIN_TOKEN") or "").strip()


def admin_token_configured() -> bool:
    return bool(get_admin_token())


def _constant_time_equals(left: str, right: str) -> bool:
    if not left or not right:
        return False
    return hmac.compare_digest(left, right)


def admin_token_from_request(request: Request) -> str | None:
    header_token = request.headers.get("X-Admin-Token")
    if header_token:
        return header_token.strip()

    if allow_admin_token_query():
        query_token = request.query_params.get("admin_token")
        if query_token:
            return query_token.strip()

    return None


def admin_token_ok(request: Request) -> bool:
    expected_token = get_admin_token()
    received_token = admin_token_from_request(request)
    return _constant_time_equals(received_token or "", expected_token)


def require_admin_access(request: Request):
    if admin_token_ok(request):
        return True

    bearer = get_bearer_token(request)
    if bearer:
        try:
            payload = decode_access_token(bearer)
            if payload.get("role") == "admin":
                return True
        except HTTPException:
            pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Acesso administrativo não autorizado.",
    )
