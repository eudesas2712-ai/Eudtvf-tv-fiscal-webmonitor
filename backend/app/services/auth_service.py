import json
import os
import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import create_access_token, decode_access_token, get_bearer_token, hash_password, verify_password

ROLE_LABELS = {
    "admin": "Administrador",
    "gestor": "Gestor/Diretoria",
    "operador": "Operador de Monitoramento",
    "comercial": "Comercial/Atendimento",
    "cliente": "Cliente externo",
    "auditor": "Auditor/Fiscal",
}

ROLE_MODULES = {
    "admin": ["*"],
    "gestor": [
        "dashboard", "projects", "editorial", "banners", "evidences", "intel", "compare",
        "alerts", "reports", "notifications", "sla", "health",
    ],
    "operador": ["dashboard", "editorial", "banners", "evidences", "alerts", "inbox", "scheduler"],
    "comercial": ["dashboard", "intel", "compare", "reports", "projects", "alerts"],
    "cliente": ["dashboard", "editorial", "intel", "reports", "alerts"],
    "auditor": ["dashboard", "banners", "evidences", "alerts", "reports", "checking"],
}

ADMIN_ROLES = {"admin"}


def _now() -> datetime:
    return datetime.utcnow()


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def normalize_role(role: str | None) -> str:
    value = (role or "cliente").strip().lower()
    if value not in ROLE_LABELS:
        raise HTTPException(status_code=400, detail=f"Perfil inválido: {role}")
    return value


def _loads(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default


def user_to_dict(row: Any, include_sensitive: bool = False) -> dict[str, Any]:
    data = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
    result = {
        "id": str(data.get("id")),
        "name": data.get("name") or "",
        "email": data.get("email") or "",
        "role": data.get("role") or "cliente",
        "role_label": ROLE_LABELS.get(data.get("role") or "cliente", data.get("role") or "cliente"),
        "active": bool(data.get("active")),
        "project_ids": _loads(data.get("project_ids"), []),
        "allowed_modules": _loads(data.get("allowed_modules"), []),
        "last_login_at": data.get("last_login_at").isoformat() if data.get("last_login_at") else None,
        "created_at": data.get("created_at").isoformat() if data.get("created_at") else None,
        "updated_at": data.get("updated_at").isoformat() if data.get("updated_at") else None,
    }
    if not result["allowed_modules"]:
        result["allowed_modules"] = ROLE_MODULES.get(result["role"], [])
    if include_sensitive:
        result["password_hash"] = data.get("password_hash")
    return result


def audit_log(db: Session, *, user_id: str | None, action: str, status_value: str, request: Request | None = None, detail: str | None = None) -> None:
    try:
        db.execute(
            text(
                """
                INSERT INTO auth_audit_logs (id, user_id, action, status, ip_address, user_agent, detail, created_at)
                VALUES (:id, :user_id, :action, :status, :ip, :ua, :detail, NOW())
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "action": action,
                "status": status_value,
                "ip": request.client.host if request and request.client else None,
                "ua": request.headers.get("User-Agent") if request else None,
                "detail": detail,
            },
        )
        db.commit()
    except Exception:
        db.rollback()


def get_user_by_email(db: Session, email: str):
    return db.execute(text("SELECT * FROM app_users WHERE email = :email"), {"email": normalize_email(email)}).first()


def get_user_by_id(db: Session, user_id: str):
    return db.execute(text("SELECT * FROM app_users WHERE id = :id"), {"id": user_id}).first()


def ensure_default_admin(db: Session) -> dict[str, Any] | None:
    email = normalize_email(os.getenv("DEFAULT_ADMIN_EMAIL") or os.getenv("APP_ADMIN_EMAIL") or "admin@tvfiscal.local")
    password = os.getenv("DEFAULT_ADMIN_PASSWORD") or os.getenv("APP_ADMIN_PASSWORD") or os.getenv("ADMIN_PANEL_TOKEN") or "tvfiscal-admin-2026"
    name = os.getenv("DEFAULT_ADMIN_NAME") or "Administrador TV Fiscal"
    existing = get_user_by_email(db, email)
    if existing:
        return user_to_dict(existing)
    user_id = str(uuid.uuid4())
    modules = json.dumps(ROLE_MODULES["admin"])
    db.execute(
        text(
            """
            INSERT INTO app_users (id, name, email, password_hash, role, active, project_ids, allowed_modules, created_at, updated_at)
            VALUES (:id, :name, :email, :password_hash, 'admin', TRUE, '[]'::jsonb, CAST(:modules AS JSONB), NOW(), NOW())
            """
        ),
        {"id": user_id, "name": name, "email": email, "password_hash": hash_password(password), "modules": modules},
    )
    db.commit()
    return user_to_dict(get_user_by_id(db, user_id))


def login(db: Session, *, email: str, password: str, request: Request | None = None) -> dict[str, Any]:
    row = get_user_by_email(db, email)
    if not row:
        audit_log(db, user_id=None, action="login", status_value="error", request=request, detail=f"Usuário não encontrado: {normalize_email(email)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha inválidos.")
    user = user_to_dict(row, include_sensitive=True)
    if not user.get("active"):
        audit_log(db, user_id=user["id"], action="login", status_value="blocked", request=request, detail="Usuário inativo")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário inativo.")
    if not verify_password(password, user.get("password_hash")):
        audit_log(db, user_id=user["id"], action="login", status_value="error", request=request, detail="Senha inválida")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha inválidos.")
    db.execute(text("UPDATE app_users SET last_login_at = NOW(), updated_at = NOW() WHERE id = :id"), {"id": user["id"]})
    db.commit()
    row = get_user_by_id(db, user["id"])
    public_user = user_to_dict(row)
    token = create_access_token({"sub": public_user["id"], "email": public_user["email"], "role": public_user["role"]})
    audit_log(db, user_id=public_user["id"], action="login", status_value="success", request=request, detail="Login realizado")
    return {"access_token": token, "token_type": "bearer", "user": public_user}


def current_user(db: Session, request: Request) -> dict[str, Any]:
    token = get_bearer_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão não informada.")
    payload = decode_access_token(token)
    row = get_user_by_id(db, str(payload.get("sub") or ""))
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado.")
    user = user_to_dict(row)
    if not user.get("active"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário inativo.")
    return user


def require_roles(db: Session, request: Request, roles: set[str]) -> dict[str, Any]:
    user = current_user(db, request)
    if user["role"] not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Perfil sem permissão para esta ação.")
    return user


def list_users(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(text("SELECT * FROM app_users ORDER BY active DESC, role ASC, name ASC")).all()
    return [user_to_dict(row) for row in rows]


def create_user(db: Session, *, name: str, email: str, password: str, role: str, active: bool = True, project_ids: list[str] | None = None, allowed_modules: list[str] | None = None) -> dict[str, Any]:
    normalized_email = normalize_email(email)
    if not normalized_email:
        raise HTTPException(status_code=400, detail="E-mail é obrigatório.")
    if get_user_by_email(db, normalized_email):
        raise HTTPException(status_code=409, detail="Já existe usuário com este e-mail.")
    normalized_role = normalize_role(role)
    user_id = str(uuid.uuid4())
    modules = allowed_modules if allowed_modules is not None else ROLE_MODULES.get(normalized_role, [])
    db.execute(
        text(
            """
            INSERT INTO app_users (id, name, email, password_hash, role, active, project_ids, allowed_modules, created_at, updated_at)
            VALUES (:id, :name, :email, :password_hash, :role, :active, CAST(:project_ids AS JSONB), CAST(:modules AS JSONB), NOW(), NOW())
            """
        ),
        {
            "id": user_id,
            "name": name.strip() or normalized_email,
            "email": normalized_email,
            "password_hash": hash_password(password),
            "role": normalized_role,
            "active": active,
            "project_ids": json.dumps(project_ids or []),
            "modules": json.dumps(modules),
        },
    )
    db.commit()
    return user_to_dict(get_user_by_id(db, user_id))


def update_user(db: Session, user_id: str, *, name: str | None = None, email: str | None = None, role: str | None = None, active: bool | None = None, project_ids: list[str] | None = None, allowed_modules: list[str] | None = None) -> dict[str, Any]:
    if not get_user_by_id(db, user_id):
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    updates = []
    params: dict[str, Any] = {"id": user_id}
    if name is not None:
        updates.append("name = :name")
        params["name"] = name.strip()
    if email is not None:
        normalized_email = normalize_email(email)
        if not normalized_email:
            raise HTTPException(status_code=400, detail="E-mail é obrigatório.")
        existing = get_user_by_email(db, normalized_email)
        if existing and str(existing._mapping.get("id")) != user_id:
            raise HTTPException(status_code=409, detail="Já existe outro usuário com este e-mail.")
        updates.append("email = :email")
        params["email"] = normalized_email
    if role is not None:
        normalized_role = normalize_role(role)
        updates.append("role = :role")
        params["role"] = normalized_role
        if allowed_modules is None:
            allowed_modules = ROLE_MODULES.get(normalized_role, [])
    if active is not None:
        updates.append("active = :active")
        params["active"] = active
    if project_ids is not None:
        updates.append("project_ids = CAST(:project_ids AS JSONB)")
        params["project_ids"] = json.dumps(project_ids)
    if allowed_modules is not None:
        updates.append("allowed_modules = CAST(:modules AS JSONB)")
        params["modules"] = json.dumps(allowed_modules)
    if not updates:
        return user_to_dict(get_user_by_id(db, user_id))
    updates.append("updated_at = NOW()")
    db.execute(text(f"UPDATE app_users SET {', '.join(updates)} WHERE id = :id"), params)
    db.commit()
    return user_to_dict(get_user_by_id(db, user_id))


def reset_password(db: Session, user_id: str, new_password: str) -> dict[str, Any]:
    if not get_user_by_id(db, user_id):
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    db.execute(
        text("UPDATE app_users SET password_hash = :password_hash, updated_at = NOW() WHERE id = :id"),
        {"id": user_id, "password_hash": hash_password(new_password)},
    )
    db.commit()
    return user_to_dict(get_user_by_id(db, user_id))


def list_projects_summary(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(text("SELECT id, name, client_name, active FROM projects ORDER BY active DESC, name ASC")).all()
    return [
        {"id": str(row._mapping["id"]), "name": row._mapping["name"], "client_name": row._mapping.get("client_name"), "active": bool(row._mapping.get("active"))}
        for row in rows
    ]


def list_audit(db: Session, limit: int = 100) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            SELECT l.*, u.email AS user_email, u.name AS user_name
            FROM auth_audit_logs l
            LEFT JOIN app_users u ON u.id = l.user_id
            ORDER BY l.created_at DESC
            LIMIT :limit
            """
        ),
        {"limit": min(max(limit, 1), 500)},
    ).all()
    results = []
    for row in rows:
        data = dict(row._mapping)
        results.append({
            "id": str(data.get("id")),
            "user_id": str(data.get("user_id")) if data.get("user_id") else None,
            "user_email": data.get("user_email"),
            "user_name": data.get("user_name"),
            "action": data.get("action"),
            "status": data.get("status"),
            "ip_address": data.get("ip_address"),
            "detail": data.get("detail"),
            "created_at": data.get("created_at").isoformat() if data.get("created_at") else None,
        })
    return results


def delete_user_permanently(db: Session, user_id: str) -> dict[str, Any]:
    row = get_user_by_id(db, user_id)
    if not row:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    user = user_to_dict(row)
    db.execute(text("DELETE FROM app_users WHERE id = :id"), {"id": user_id})
    db.commit()
    return user
