from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.auth_service import (
    ROLE_LABELS,
    ROLE_MODULES,
    create_user,
    current_user,
    ensure_default_admin,
    list_audit,
    list_projects_summary,
    list_users,
    login,
    require_roles,
    reset_password,
    update_user,
    delete_user_permanently,
    audit_log,
)
from app.services.permissions_service import permissions_matrix, modules_for_user

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=6)


class UserCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    email: str
    password: str = Field(min_length=6, max_length=255)
    role: str = "cliente"
    active: bool = True
    project_ids: list[str] = []
    allowed_modules: list[str] | None = None


class UserUpdateRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    role: str | None = None
    active: bool | None = None
    project_ids: list[str] | None = None
    allowed_modules: list[str] | None = None


class PasswordResetRequest(BaseModel):
    password: str = Field(min_length=6, max_length=255)


@router.post("/login")
def login_route(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    return login(db, email=payload.email, password=payload.password, request=request)


@router.get("/me")
def me_route(request: Request, db: Session = Depends(get_db)):
    return current_user(db, request)


@router.post("/bootstrap-admin")
def bootstrap_admin_route(request: Request, db: Session = Depends(get_db)):
    # Permite criar o admin padrão quando a tabela existir e ainda não houver usuário.
    user = ensure_default_admin(db)
    audit_log(db, user_id=user["id"] if user else None, action="bootstrap_admin", status_value="success", request=request, detail="Admin padrão verificado/criado")
    return {"ok": True, "user": user}


@router.get("/roles")
def roles_route():
    return {
        "roles": [
            {"id": role, "label": label, "modules": ROLE_MODULES.get(role, [])}
            for role, label in ROLE_LABELS.items()
        ]
    }




@router.get("/permissions-matrix")
def permissions_matrix_route(request: Request, db: Session = Depends(get_db)):
    require_roles(db, request, {"admin"})
    return permissions_matrix()


@router.get("/my-access")
def my_access_route(request: Request, db: Session = Depends(get_db)):
    user = current_user(db, request)
    return {
        "user": user,
        "modules": modules_for_user(user),
        "project_ids": user.get("project_ids") or [],
    }


@router.get("/users")
def users_route(request: Request, db: Session = Depends(get_db)):
    require_roles(db, request, {"admin"})
    return {"items": list_users(db)}


@router.post("/users")
def create_user_route(payload: UserCreateRequest, request: Request, db: Session = Depends(get_db)):
    actor = require_roles(db, request, {"admin"})
    user = create_user(
        db,
        name=payload.name,
        email=payload.email,
        password=payload.password,
        role=payload.role,
        active=payload.active,
        project_ids=payload.project_ids,
        allowed_modules=payload.allowed_modules,
    )
    audit_log(db, user_id=actor["id"], action="create_user", status_value="success", request=request, detail=f"Criou usuário {user['email']}")
    return user


@router.put("/users/{user_id}")
def update_user_route(user_id: str, payload: UserUpdateRequest, request: Request, db: Session = Depends(get_db)):
    actor = require_roles(db, request, {"admin"})
    user = update_user(
        db,
        user_id,
        name=payload.name,
        email=payload.email,
        role=payload.role,
        active=payload.active,
        project_ids=payload.project_ids,
        allowed_modules=payload.allowed_modules,
    )
    audit_log(db, user_id=actor["id"], action="update_user", status_value="success", request=request, detail=f"Atualizou usuário {user['email']}")
    return user


@router.post("/users/{user_id}/reset-password")
def reset_password_route(user_id: str, payload: PasswordResetRequest, request: Request, db: Session = Depends(get_db)):
    actor = require_roles(db, request, {"admin"})
    user = reset_password(db, user_id, payload.password)
    audit_log(db, user_id=actor["id"], action="reset_password", status_value="success", request=request, detail=f"Redefiniu senha de {user['email']}")
    return user


@router.delete("/users/{user_id}")
def deactivate_user_route(user_id: str, request: Request, db: Session = Depends(get_db)):
    actor = require_roles(db, request, {"admin"})
    user = update_user(db, user_id, active=False)
    audit_log(db, user_id=actor["id"], action="deactivate_user", status_value="success", request=request, detail=f"Desativou usuário {user['email']}")
    return {"ok": True, "user": user}


@router.delete("/users/{user_id}/purge")
def delete_user_permanently_route(user_id: str, request: Request, db: Session = Depends(get_db)):
    actor = require_roles(db, request, {"admin"})
    if str(actor.get("id")) == str(user_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Não é permitido excluir definitivamente o próprio usuário logado.")
    user = delete_user_permanently(db, user_id)
    audit_log(db, user_id=actor["id"], action="delete_user_permanently", status_value="success", request=request, detail=f"Excluiu definitivamente usuário {user['email']}")
    return {"ok": True, "user": user}


@router.get("/projects-summary")
def projects_summary_route(request: Request, db: Session = Depends(get_db)):
    require_roles(db, request, {"admin", "gestor"})
    return {"items": list_projects_summary(db)}


@router.get("/audit")
def audit_route(request: Request, limit: int = 100, db: Session = Depends(get_db)):
    require_roles(db, request, {"admin"})
    return {"items": list_audit(db, limit=limit)}
