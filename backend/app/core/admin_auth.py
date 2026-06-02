import os

from fastapi import HTTPException, Request, status

from app.core.security import decode_access_token, get_bearer_token


def get_admin_token():
    return os.getenv("ADMIN_PANEL_TOKEN", "tvfiscal-admin-2026")


def require_admin_access(request: Request):
    expected_token = get_admin_token()

    header_token = request.headers.get("X-Admin-Token")
    query_token = request.query_params.get("admin_token")
    received_token = header_token or query_token

    if received_token and received_token == expected_token:
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
