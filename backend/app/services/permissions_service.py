import json
import os
import re
from typing import Any

from fastapi import HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.admin_auth import admin_token_ok
from app.core.security import decode_access_token, get_bearer_token
from app.services.auth_service import ROLE_MODULES, ROLE_LABELS, user_to_dict

PUBLIC_PREFIXES = (
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
)
PUBLIC_EXACT = {
    "/auth/login",
    "/auth/bootstrap-admin",
    "/auth/roles",
}
UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")

MODULE_LABELS = {
    "dashboard": "Dashboard Executivo",
    "projects": "Projetos e cadastros",
    "editorial": "Monitoramento editorial",
    "banners": "Banners capturados",
    "evidences": "Evidências/checking",
    "intel": "Inteligência de Mercado",
    "compare": "Intel Comparativo",
    "reports": "Relatórios",
    "alerts": "Central de Alertas",
    "inbox": "Caixa de Alertas",
    "sla": "SLA e Escalonamento",
    "notifications": "Motor de Notificações",
    "scheduler": "Scheduler/coletas",
    "health": "Saúde, manutenção e backup",
    "users": "Usuários e perfis",
    "checking": "Auditoria fiscal/checking",
}

# Regras de alto nível. A finalidade é bloquear no backend por perfil/módulo,
# sem depender apenas da ocultação do menu no frontend.
PATH_MODULE_RULES: list[tuple[str, str]] = [
    ("/auth/users", "users"),
    ("/auth/audit", "users"),
    ("/auth/projects-summary", "users"),
    ("/maintenance", "health"),
    ("/system/health", "health"),
    ("/admin/scheduler", "scheduler"),
    ("/notifications/reports", "reports"),
    ("/notifications/sla", "sla"),
    ("/notifications/inbox", "inbox"),
    ("/notifications", "notifications"),
    ("/alerts", "alerts"),
    ("/identification", "intel"),
    ("/intel/compare", "compare"),
    ("/intel", "intel"),
    ("/reports", "reports"),
    ("/editorial", "editorial"),
    ("/items", "editorial"),
    ("/banners/item", "evidences"),
    ("/banners", "banners"),
    ("/registry", "projects"),
    ("/projects", "projects"),
    ("/sources", "projects"),
    ("/terms", "projects"),
    ("/executive/dashboard", "dashboard"),
]

# Permissões mínimas por método para endpoints sensíveis.
# Leitura costuma ser liberada pelo módulo; alterações pedem perfil operacional/admin.
# Regra de segurança: toda mutação sem regra explícita cai em DEFAULT_MUTATION_ROLES.
READ_ONLY_METHODS = {"GET", "HEAD", "OPTIONS"}
DEFAULT_MUTATION_ROLES = {"admin"}

MUTATION_ROLE_RULES: list[tuple[str, set[str]]] = [
    # Administração de usuários e permissões
    ("/auth/users", {"admin"}),
    ("/auth/audit", {"admin"}),
    ("/auth/permissions-matrix", {"admin"}),

    # Manutenção, backup e saúde operacional
    ("/maintenance", {"admin"}),
    ("/system/health", {"admin"}),

    # Scheduler/coletas administrativas
    ("/admin/scheduler", {"admin", "operador"}),

    # Motor de notificações e SLA
    ("/notifications/provider-settings", {"admin"}),
    ("/notifications/contacts", {"admin", "gestor"}),
    ("/notifications/rules", {"admin", "gestor"}),
    ("/notifications/bootstrap", {"admin"}),
    ("/notifications/cleanup", {"admin"}),
    ("/notifications/evaluate", {"admin", "gestor", "operador"}),
    ("/notifications/test", {"admin", "gestor"}),
    ("/notifications/sla/evaluate", {"admin", "gestor"}),
    ("/notifications/logs", {"admin", "gestor"}),
    ("/notifications", {"admin", "gestor"}),

    # Qualificação e inteligência operacional
    ("/identification", {"admin", "operador"}),
    ("/intel/compare", {"admin", "gestor", "operador"}),
    ("/intel", {"admin", "gestor", "operador"}),

    # Cadastros e projetos
    ("/registry", {"admin", "operador"}),
    ("/projects", {"admin", "gestor"}),
    ("/sources", {"admin", "operador"}),
    ("/terms", {"admin", "operador"}),

    # Editorial/checking
    ("/editorial/run", {"admin", "operador"}),
    ("/editorial/reclassify", {"admin", "operador"}),
    ("/editorial/clear", {"admin"}),
    ("/items/clear", {"admin"}),

    # Banners/evidências
    ("/banners/scan", {"admin", "operador"}),
]


def enforcement_mode() -> str:
    return (os.getenv("AUTH_ENFORCEMENT_MODE") or "compat").strip().lower()


def is_public_path(path: str) -> bool:
    if path in PUBLIC_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES)


def module_for_path(path: str) -> str | None:
    for prefix, module in PATH_MODULE_RULES:
        if path.startswith(prefix):
            return module
    return None


def mutation_roles_for_path(path: str) -> set[str] | None:
    for prefix, roles in MUTATION_ROLE_RULES:
        if path.startswith(prefix):
            return roles
    return None


def _loads(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default


def extract_project_id(request: Request) -> str | None:
    # Prioridade para query param explícito.
    for key in ("project_id", "projectId"):
        val = request.query_params.get(key)
        if val and UUID_RE.fullmatch(val):
            return val
    # Depois tenta encontrar UUID em qualquer segmento do path.
    match = UUID_RE.search(request.url.path)
    return match.group(0) if match else None


def _admin_token_ok(request: Request) -> bool:
    return admin_token_ok(request)


def user_from_request(db: Session, request: Request) -> dict[str, Any] | None:
    token = get_bearer_token(request)
    if not token:
        return None
    payload = decode_access_token(token)
    user_id = str(payload.get("sub") or "")
    row = db.execute(text("SELECT * FROM app_users WHERE id = :id"), {"id": user_id}).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado.")
    user = user_to_dict(row)
    if not user.get("active"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário inativo.")
    return user


def modules_for_user(user: dict[str, Any]) -> list[str]:
    modules = _loads(user.get("allowed_modules"), [])
    if not modules:
        modules = ROLE_MODULES.get(user.get("role") or "cliente", [])
    return list(modules or [])


def user_has_module(user: dict[str, Any], module: str | None) -> bool:
    if not module:
        return True
    if user.get("role") == "admin":
        return True
    modules = modules_for_user(user)
    return "*" in modules or module in modules


def user_can_access_project(user: dict[str, Any], project_id: str | None) -> bool:
    if not project_id:
        return True
    if user.get("role") == "admin":
        return True
    project_ids = _loads(user.get("project_ids"), [])
    # Sem restrição explícita: mantém compatibilidade para gestor/operador internos.
    if not project_ids:
        return True
    return str(project_id) in {str(p) for p in project_ids}


def validate_request_permission(db: Session, request: Request) -> dict[str, Any] | None:
    path = request.url.path
    method = request.method.upper()
    if method == "OPTIONS" or is_public_path(path):
        return None

    # Compatibilidade com rotinas/admin token legado.
    if _admin_token_ok(request):
        return {"auth_mode": "admin_token", "role": "admin", "allowed": True}

    user = user_from_request(db, request)
    mode = enforcement_mode()

    if not user:
        if mode == "strict":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Autenticação obrigatória.")
        return None

    module = module_for_path(path)
    if not user_has_module(user, module):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Sem permissão para o módulo: {MODULE_LABELS.get(module or '', module or 'desconhecido')}.")

    if method not in READ_ONLY_METHODS:
        roles = mutation_roles_for_path(path) or DEFAULT_MUTATION_ROLES
        if user.get("role") not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Perfil sem permissão para alterar este recurso.")

    project_id = extract_project_id(request)
    if not user_can_access_project(user, project_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário sem acesso a este projeto.")

    return {"auth_mode": "bearer", "role": user.get("role"), "user_id": user.get("id"), "module": module, "project_id": project_id}


def permissions_matrix() -> dict[str, Any]:
    return {
        "modules": [{"id": key, "label": label} for key, label in MODULE_LABELS.items()],
        "roles": [
            {
                "id": role,
                "label": ROLE_LABELS.get(role, role),
                "modules": ROLE_MODULES.get(role, []),
            }
            for role in ROLE_LABELS.keys()
        ],
        "enforcement_mode": enforcement_mode(),
        "strict_hint": "AUTH_ENFORCEMENT_MODE=strict bloqueia chamadas sem sessão/autorização. Em compat, o token de usuário é fiscalizado quando enviado e X-Admin-Token segue compatível.",
    }
