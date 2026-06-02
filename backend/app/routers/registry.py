from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.admin_auth import require_admin_access
from app.db.models import (
    Advertiser,
    AdvertiserAlias,
    Portal,
    Project,
    ProjectAdvertiser,
    ProjectPortal,
    Segment,
)
from app.db.session import get_db

router = APIRouter(prefix="/registry", tags=["Registry"])


class SegmentIn(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None
    active: bool = True


class AdvertiserIn(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    legal_name: str | None = None
    segment_id: str | None = None
    advertiser_type: str = "anunciante"
    aliases: list[str] = []
    active: bool = True


class AliasIn(BaseModel):
    alias: str = Field(min_length=2, max_length=255)
    active: bool = True


class PortalIn(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    base_url: str = Field(min_length=8, max_length=1024)
    category: str | None = "Portal de notícias"
    active: bool = True
    monitor_publicity: bool = True
    monitor_editorial: bool = True
    interval_minutes: int = 60


class ProjectPortalIn(BaseModel):
    portal_id: str
    active: bool = True


class ProjectAdvertiserIn(BaseModel):
    advertiser_id: str
    role: str = "monitorado"
    active: bool = True


class ProjectIn(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    client_name: str | None = None
    segment_id: str | None = None
    description: str | None = None
    active: bool = True
    monitor_publicity: bool = True
    monitor_editorial: bool = True
    monitor_market: bool = True
    monitor_checking: bool = True


def _uuid(value: str, label: str = "id") -> UUID:
    try:
        return UUID(str(value))
    except Exception:
        raise HTTPException(status_code=400, detail=f"{label} inválido.")


def _require_admin(request: Request) -> bool:
    return require_admin_access(request)


DEFAULT_PORTALS = [
    ("ClickPB", "https://www.clickpb.com.br"),
    ("Jornal da Paraíba", "https://www.jornaldaparaiba.com.br"),
    ("WSCom", "https://www.wscom.com.br"),
    ("Portal Correio", "https://www.portalcorreio.com.br"),
    ("Polêmica Paraíba", "https://www.polemicaparaiba.com.br"),
]


def _upsert_default_portals(db: Session) -> tuple[list[Portal], dict]:
    created = {"portals": 0, "reactivated_portals": 0}
    rows: list[Portal] = []

    for name, url in DEFAULT_PORTALS:
        portal = db.query(Portal).filter(Portal.base_url == url).first()
        if portal:
            changed = False
            if portal.name != name:
                portal.name = name
                changed = True
            if not portal.active:
                portal.active = True
                changed = True
                created["reactivated_portals"] += 1
            if not portal.monitor_publicity:
                portal.monitor_publicity = True
                changed = True
            if not portal.monitor_editorial:
                portal.monitor_editorial = True
                changed = True
            if changed:
                db.flush()
        else:
            portal = Portal(
                name=name,
                base_url=url,
                category="Portal de notícias",
                active=True,
                monitor_publicity=True,
                monitor_editorial=True,
                interval_minutes=60,
            )
            db.add(portal)
            db.flush()
            created["portals"] += 1
        rows.append(portal)

    return rows, created


def _segment_payload(row: Segment) -> dict:
    return {
        "id": str(row.id),
        "name": row.name,
        "description": row.description,
        "active": row.active,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _advertiser_payload(row: Advertiser, db: Session) -> dict:
    segment = db.query(Segment).filter(Segment.id == row.segment_id).first() if row.segment_id else None
    aliases = (
        db.query(AdvertiserAlias)
        .filter(AdvertiserAlias.advertiser_id == row.id)
        .order_by(AdvertiserAlias.alias.asc())
        .all()
    )
    return {
        "id": str(row.id),
        "name": row.name,
        "legal_name": row.legal_name,
        "segment_id": str(row.segment_id) if row.segment_id else None,
        "segment_name": segment.name if segment else None,
        "advertiser_type": row.advertiser_type,
        "active": row.active,
        "aliases": [a.alias for a in aliases if a.active],
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _portal_payload(row: Portal) -> dict:
    return {
        "id": str(row.id),
        "name": row.name,
        "base_url": row.base_url,
        "category": row.category,
        "active": row.active,
        "monitor_publicity": row.monitor_publicity,
        "monitor_editorial": row.monitor_editorial,
        "interval_minutes": row.interval_minutes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _project_payload(row: Project, db: Session, include_counts: bool = True) -> dict:
    segment = db.query(Segment).filter(Segment.id == row.segment_id).first() if getattr(row, "segment_id", None) else None
    payload = {
        "id": str(row.id),
        "name": row.name,
        "client_name": getattr(row, "client_name", None),
        "segment_id": str(row.segment_id) if getattr(row, "segment_id", None) else None,
        "segment_name": segment.name if segment else None,
        "description": row.description,
        "active": getattr(row, "active", True) is not False,
        "monitor_publicity": getattr(row, "monitor_publicity", True),
        "monitor_editorial": getattr(row, "monitor_editorial", True),
        "monitor_market": getattr(row, "monitor_market", True),
        "monitor_checking": getattr(row, "monitor_checking", True),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if getattr(row, "updated_at", None) else None,
    }

    if include_counts:
        payload["portals_count"] = db.query(ProjectPortal).filter(
            ProjectPortal.project_id == row.id, ProjectPortal.active.is_(True)
        ).count()
        payload["advertisers_count"] = db.query(ProjectAdvertiser).filter(
            ProjectAdvertiser.project_id == row.id, ProjectAdvertiser.active.is_(True)
        ).count()
    return payload


def _apply_project_payload(row: Project, payload: ProjectIn) -> Project:
    row.name = payload.name.strip()
    row.client_name = (payload.client_name or "").strip() or None
    row.segment_id = _uuid(payload.segment_id, "segment_id") if payload.segment_id else None
    row.description = payload.description
    row.active = payload.active
    row.monitor_publicity = payload.monitor_publicity
    row.monitor_editorial = payload.monitor_editorial
    row.monitor_market = payload.monitor_market
    row.monitor_checking = payload.monitor_checking
    row.updated_at = datetime.utcnow()
    return row


@router.get("/segments")
def list_segments(active_only: bool = False, db: Session = Depends(get_db)):
    query = db.query(Segment)
    if active_only:
        query = query.filter(Segment.active.is_(True))
    return [_segment_payload(row) for row in query.order_by(Segment.name.asc()).all()]


@router.post("/segments")
def create_segment(payload: SegmentIn, request: Request, db: Session = Depends(get_db)):
    _require_admin(request)
    existing = db.query(Segment).filter(Segment.name.ilike(payload.name.strip())).first()
    if existing:
        existing.description = payload.description
        existing.active = payload.active
        db.commit()
        db.refresh(existing)
        return _segment_payload(existing)
    row = Segment(name=payload.name.strip(), description=payload.description, active=payload.active)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _segment_payload(row)


@router.get("/advertisers")
def list_advertisers(segment_id: str | None = None, active_only: bool = False, db: Session = Depends(get_db)):
    query = db.query(Advertiser)
    if segment_id:
        query = query.filter(Advertiser.segment_id == _uuid(segment_id, "segment_id"))
    if active_only:
        query = query.filter(Advertiser.active.is_(True))
    return [_advertiser_payload(row, db) for row in query.order_by(Advertiser.name.asc()).all()]


@router.post("/advertisers")
def create_advertiser(payload: AdvertiserIn, request: Request, db: Session = Depends(get_db)):
    _require_admin(request)
    segment_uuid = _uuid(payload.segment_id, "segment_id") if payload.segment_id else None
    row = Advertiser(
        name=payload.name.strip(),
        legal_name=(payload.legal_name or "").strip() or None,
        segment_id=segment_uuid,
        advertiser_type=payload.advertiser_type.strip() or "anunciante",
        active=payload.active,
    )
    db.add(row)
    db.flush()

    alias_values = {payload.name.strip(), *[a.strip() for a in payload.aliases if a.strip()]}
    for alias in sorted(alias_values):
        db.add(AdvertiserAlias(advertiser_id=row.id, alias=alias, active=True))

    db.commit()
    db.refresh(row)
    return _advertiser_payload(row, db)


@router.post("/advertisers/{advertiser_id}/aliases")
def add_advertiser_alias(advertiser_id: str, payload: AliasIn, request: Request, db: Session = Depends(get_db)):
    _require_admin(request)
    advertiser_uuid = _uuid(advertiser_id, "advertiser_id")
    advertiser = db.query(Advertiser).filter(Advertiser.id == advertiser_uuid).first()
    if not advertiser:
        raise HTTPException(status_code=404, detail="Anunciante não encontrado.")

    existing = (
        db.query(AdvertiserAlias)
        .filter(AdvertiserAlias.advertiser_id == advertiser_uuid, AdvertiserAlias.alias.ilike(payload.alias.strip()))
        .first()
    )
    if existing:
        existing.active = payload.active
    else:
        db.add(AdvertiserAlias(advertiser_id=advertiser_uuid, alias=payload.alias.strip(), active=payload.active))
    db.commit()
    return _advertiser_payload(advertiser, db)


@router.get("/portals")
def list_portals(active_only: bool = False, db: Session = Depends(get_db)):
    query = db.query(Portal)
    if active_only:
        query = query.filter(Portal.active.is_(True))
    return [_portal_payload(row) for row in query.order_by(Portal.name.asc()).all()]


@router.post("/portals")
def create_portal(payload: PortalIn, request: Request, db: Session = Depends(get_db)):
    _require_admin(request)
    existing = db.query(Portal).filter(Portal.base_url == payload.base_url.strip()).first()
    if existing:
        existing.name = payload.name.strip()
        existing.category = payload.category
        existing.active = payload.active
        existing.monitor_publicity = payload.monitor_publicity
        existing.monitor_editorial = payload.monitor_editorial
        existing.interval_minutes = payload.interval_minutes
        db.commit()
        db.refresh(existing)
        return _portal_payload(existing)

    row = Portal(
        name=payload.name.strip(),
        base_url=payload.base_url.strip(),
        category=payload.category,
        active=payload.active,
        monitor_publicity=payload.monitor_publicity,
        monitor_editorial=payload.monitor_editorial,
        interval_minutes=payload.interval_minutes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _portal_payload(row)


@router.get("/projects")
def list_registry_projects(active_only: bool = False, db: Session = Depends(get_db)):
    query = db.query(Project)
    if active_only:
        query = query.filter(Project.active.isnot(False))
    rows = query.order_by(Project.created_at.desc()).all()
    return [_project_payload(row, db) for row in rows]


@router.post("/projects")
def create_project(payload: ProjectIn, request: Request, db: Session = Depends(get_db)):
    _require_admin(request)
    row = Project(name=payload.name.strip())
    _apply_project_payload(row, payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _project_payload(row, db)


@router.put("/projects/{project_id}")
def update_project(project_id: str, payload: ProjectIn, request: Request, db: Session = Depends(get_db)):
    _require_admin(request)
    project_uuid = _uuid(project_id, "project_id")
    row = db.query(Project).filter(Project.id == project_uuid).first()
    if not row:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")
    _apply_project_payload(row, payload)
    db.commit()
    db.refresh(row)
    return _project_payload(row, db)


@router.post("/projects/{project_id}/active")
def set_project_active(project_id: str, active: bool, request: Request, db: Session = Depends(get_db)):
    _require_admin(request)
    project_uuid = _uuid(project_id, "project_id")
    row = db.query(Project).filter(Project.id == project_uuid).first()
    if not row:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")
    row.active = active
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _project_payload(row, db)


@router.post("/projects/{project_id}/portals")
def attach_project_portal(project_id: str, payload: ProjectPortalIn, request: Request, db: Session = Depends(get_db)):
    _require_admin(request)
    project_uuid = _uuid(project_id, "project_id")
    portal_uuid = _uuid(payload.portal_id, "portal_id")

    row = db.query(ProjectPortal).filter(ProjectPortal.project_id == project_uuid, ProjectPortal.portal_id == portal_uuid).first()
    if row:
        row.active = payload.active
    else:
        row = ProjectPortal(project_id=project_uuid, portal_id=portal_uuid, active=payload.active)
        db.add(row)
    db.commit()
    return get_project_config(project_id, db)


@router.post("/projects/{project_id}/advertisers")
def attach_project_advertiser(project_id: str, payload: ProjectAdvertiserIn, request: Request, db: Session = Depends(get_db)):
    _require_admin(request)
    project_uuid = _uuid(project_id, "project_id")
    advertiser_uuid = _uuid(payload.advertiser_id, "advertiser_id")

    row = db.query(ProjectAdvertiser).filter(ProjectAdvertiser.project_id == project_uuid, ProjectAdvertiser.advertiser_id == advertiser_uuid).first()
    if row:
        row.role = payload.role
        row.active = payload.active
    else:
        row = ProjectAdvertiser(project_id=project_uuid, advertiser_id=advertiser_uuid, role=payload.role, active=payload.active)
        db.add(row)
    db.commit()
    return get_project_config(project_id, db)


@router.get("/projects/{project_id}/config")
def get_project_config(project_id: str, db: Session = Depends(get_db)):
    project_uuid = _uuid(project_id, "project_id")
    project = db.query(Project).filter(Project.id == project_uuid).first()

    project_portals = db.query(ProjectPortal).filter(ProjectPortal.project_id == project_uuid, ProjectPortal.active.is_(True)).all()
    portal_ids = [row.portal_id for row in project_portals]
    portals = db.query(Portal).filter(Portal.id.in_(portal_ids)).all() if portal_ids else []

    project_advertisers = db.query(ProjectAdvertiser).filter(ProjectAdvertiser.project_id == project_uuid, ProjectAdvertiser.active.is_(True)).all()
    advertiser_roles = {row.advertiser_id: row.role for row in project_advertisers}
    advertiser_ids = [row.advertiser_id for row in project_advertisers]
    advertisers = db.query(Advertiser).filter(Advertiser.id.in_(advertiser_ids)).all() if advertiser_ids else []

    return {
        "project": _project_payload(project, db, include_counts=False) if project else {
            "id": str(project_uuid),
            "name": f"Projeto {str(project_uuid)[:8]}",
            "client_name": None,
            "segment_id": None,
            "segment_name": None,
            "description": None,
            "active": True,
            "monitor_publicity": True,
            "monitor_editorial": True,
            "monitor_market": True,
            "monitor_checking": True,
        },
        "portals": [_portal_payload(row) for row in portals],
        "advertisers": [
            {**_advertiser_payload(row, db), "role": advertiser_roles.get(row.id, "monitorado")}
            for row in advertisers
        ],
    }


@router.post("/bootstrap-defaults")
def bootstrap_defaults(request: Request, db: Session = Depends(get_db)):
    _require_admin(request)
    defaults = {
        "Saúde": ["Unimed", "Hapvida", "Amil", "Bradesco Saúde", "SulAmérica"],
        "Telecom": ["Claro", "Vivo", "TIM", "Oi"],
        "Varejo": ["Casas Bahia", "Magalu", "Americanas", "Amazon"],
        "Bancos": ["Caixa", "Banco do Brasil", "Bradesco", "Itaú", "Santander"],
        "Educação": ["UNIPÊ", "Cruzeiro do Sul", "UNINASSAU", "Estácio", "Unifacisa"],
    }

    created = {"segments": 0, "advertisers": 0, "aliases": 0}
    for segment_name, names in defaults.items():
        segment = db.query(Segment).filter(Segment.name.ilike(segment_name)).first()
        if not segment:
            segment = Segment(name=segment_name, active=True)
            db.add(segment)
            db.flush()
            created["segments"] += 1

        for name in names:
            advertiser = db.query(Advertiser).filter(Advertiser.name.ilike(name)).first()
            if not advertiser:
                advertiser = Advertiser(name=name, segment_id=segment.id, active=True)
                db.add(advertiser)
                db.flush()
                created["advertisers"] += 1
            existing_alias = db.query(AdvertiserAlias).filter(AdvertiserAlias.advertiser_id == advertiser.id, AdvertiserAlias.alias.ilike(name)).first()
            if not existing_alias:
                db.add(AdvertiserAlias(advertiser_id=advertiser.id, alias=name, active=True))
                created["aliases"] += 1

    portals, portal_created = _upsert_default_portals(db)
    created.update(portal_created)

    db.commit()
    return {"status": "ok", "created": created, "portals": [_portal_payload(row) for row in portals]}


@router.post("/projects/{project_id}/bootstrap-portals")
def bootstrap_project_portals(project_id: str, request: Request, db: Session = Depends(get_db)):
    _require_admin(request)
    project_uuid = _uuid(project_id, "project_id")

    project = db.query(Project).filter(Project.id == project_uuid).first()
    if not project:
        project = Project(
            id=project_uuid,
            name=f"Projeto {str(project_uuid)[:8]}",
            description="Projeto operacional criado automaticamente para vincular portais padrão.",
            active=True,
        )
        db.add(project)
        db.flush()

    portals, created = _upsert_default_portals(db)
    linked_count = 0
    reactivated_count = 0

    for portal in portals:
        link = (
            db.query(ProjectPortal)
            .filter(ProjectPortal.project_id == project_uuid, ProjectPortal.portal_id == portal.id)
            .first()
        )
        if link:
            if not link.active:
                link.active = True
                reactivated_count += 1
        else:
            db.add(ProjectPortal(project_id=project_uuid, portal_id=portal.id, active=True))
            linked_count += 1

    db.commit()

    return {
        "status": "ok",
        "project_id": str(project_uuid),
        "created": created,
        "linked_portals": linked_count,
        "reactivated_links": reactivated_count,
        "config": get_project_config(str(project_uuid), db),
    }
