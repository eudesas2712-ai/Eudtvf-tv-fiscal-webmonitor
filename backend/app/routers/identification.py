from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.admin_auth import require_admin_access
from app.db.session import get_db
from app.services.identification_review import (
    apply_aliases_to_pending_items,
    ignore_group,
    identification_quality_summary,
    list_identification_groups,
    qualify_group,
    recent_identification_actions,
)

router = APIRouter(prefix="/identification", tags=["Identification"])


def _csv_response(filename: str, rows: list[list[str]]):
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    for row in rows:
        writer.writerow(row)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


class QualifyPayload(BaseModel):
    group_key: str
    advertiser_id: str
    create_alias: bool = True
    alias: str | None = None
    note: str | None = None
    apply_alias_to_pending: bool = False


class IgnorePayload(BaseModel):
    group_key: str
    note: str | None = None
    remove_from_market: bool = True


@router.get("/pending/{project_id}")
def pending_identification_groups(project_id: str, limit: int = Query(default=120, ge=1, le=500), db: Session = Depends(get_db)):
    return list_identification_groups(db, project_id, limit=limit)


@router.get("/pending/{project_id}/export.csv")
def export_pending_identification_groups(project_id: str, limit: int = Query(default=500, ge=1, le=2000), db: Session = Depends(get_db)):
    payload = list_identification_groups(db, project_id, limit=limit)
    rows = [[
        "Grupo",
        "Qtd",
        "Investimento",
        "Portais",
        "Formato",
        "Score publicidade",
        "Score mercado",
        "Sugestão de anunciante",
        "Alias sugerido",
        "Amostra OCR/ALT/URL",
        "Preview",
        "Página",
    ]]
    for group in payload.get("groups") or []:
        rows.append([
            str(group.get("group_key") or ""),
            str(group.get("count") or 0),
            str(group.get("estimated_investment") or 0),
            ", ".join(group.get("portals") or []),
            str(group.get("format") or ""),
            str(group.get("publicity_score") or 0),
            str(group.get("market_score") or 0),
            str(group.get("suggested_advertiser_name") or ""),
            str(group.get("suggested_alias") or ""),
            str(group.get("suggestion") or ""),
            str(group.get("sample_preview_url") or ""),
            str(group.get("sample_page_url") or ""),
        ])
    return _csv_response(f"identificacao_pendentes_{project_id}.csv", rows)


@router.get("/quality/{project_id}")
def identification_quality(project_id: str, db: Session = Depends(get_db)):
    return identification_quality_summary(db, project_id)


@router.get("/actions/{project_id}/export.csv")
def export_identification_actions(project_id: str, limit: int = Query(default=500, ge=1, le=2000), db: Session = Depends(get_db)):
    payload = recent_identification_actions(db, project_id, limit=limit)
    rows = [[
        "Data qualificação",
        "Status",
        "Anunciante",
        "Portal",
        "Valor",
        "Observação",
        "Preview",
        "Página",
    ]]
    for item in payload.get("actions") or []:
        rows.append([
            str(item.get("qualified_at") or item.get("created_at") or ""),
            str(item.get("status") or ""),
            str(item.get("advertiser_name") or ""),
            str(item.get("portal") or ""),
            str(item.get("value") or 0),
            str(item.get("note") or ""),
            str(item.get("preview_url") or ""),
            str(item.get("page_url") or ""),
        ])
    return _csv_response(f"identificacao_acoes_{project_id}.csv", rows)


@router.get("/actions/{project_id}")
def identification_actions(project_id: str, limit: int = Query(default=80, ge=1, le=300), db: Session = Depends(get_db)):
    return recent_identification_actions(db, project_id, limit=limit)


@router.post("/qualify/{project_id}")
def qualify_identification_group(project_id: str, payload: QualifyPayload, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    try:
        return qualify_group(
            db,
            project_id=project_id,
            group_key=payload.group_key,
            advertiser_id=payload.advertiser_id,
            create_alias=payload.create_alias,
            alias=payload.alias,
            note=payload.note,
            apply_alias_to_pending=payload.apply_alias_to_pending,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/ignore/{project_id}")
def ignore_identification_group(project_id: str, payload: IgnorePayload, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return ignore_group(
        db,
        project_id=project_id,
        group_key=payload.group_key,
        note=payload.note,
        remove_from_market=payload.remove_from_market,
    )


@router.post("/reprocess-aliases/{project_id}")
def reprocess_identification_aliases(
    project_id: str,
    request: Request,
    limit: int = Query(default=5000, ge=1, le=20000),
    db: Session = Depends(get_db),
):
    require_admin_access(request)
    return apply_aliases_to_pending_items(db, project_id=project_id, limit=limit)


@router.post("/auto-run/{project_id}")
def run_identification_auto(
    project_id: str,
    request: Request,
    limit: int = Query(default=20000, ge=1, le=50000),
    db: Session = Depends(get_db),
):
    require_admin_access(request)
    result = apply_aliases_to_pending_items(db, project_id=project_id, limit=limit)
    quality = identification_quality_summary(db, project_id)
    result["quality"] = quality
    return result
