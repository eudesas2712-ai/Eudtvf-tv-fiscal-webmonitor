from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.orm import Session

from app.core.admin_auth import require_admin_access
from app.db.session import get_db
from app.services.system_health_service import advanced_health, history, history_csv, quick_ready, technical_report_pdf

router = APIRouter(prefix="/system/health", tags=["system-health"])


@router.get("/advanced")
def advanced(request: Request, persist: bool = Query(default=False), db: Session = Depends(get_db)):
    require_admin_access(request)
    return advanced_health(db, persist=persist, trigger_source="manual_get")


@router.post("/check")
def run_check(request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return advanced_health(db, persist=True, trigger_source="manual")


@router.get("/history")
def check_history(
    request: Request,
    limit: int = Query(default=100),
    service: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    require_admin_access(request)
    return {"items": history(db, limit=limit, service=service, status=status)}


@router.get("/history/export.csv")
def check_history_export(request: Request, limit: int = Query(default=1000), db: Session = Depends(get_db)):
    require_admin_access(request)
    return PlainTextResponse(
        history_csv(db, limit=limit),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=tvfiscal_system_health_history.csv"},
    )


@router.get("/report.pdf")
def report_pdf(request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    content = technical_report_pdf(db)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=tvfiscal_relatorio_tecnico_saude.pdf"},
    )


@router.get("/uptime")
def uptime_endpoint(db: Session = Depends(get_db)):
    data = advanced_health(db, persist=False, trigger_source="uptime")
    overall = (data.get("summary") or {}).get("overall_status")
    if overall == "error":
        raise HTTPException(status_code=503, detail=data)
    return {"status": overall, "summary": data.get("summary"), "checked_at": data.get("generated_at_display")}


@router.get("/ready")
def ready_alias(db: Session = Depends(get_db)):
    data = quick_ready(db)
    if data.get("status") != "ok":
        raise HTTPException(status_code=503, detail=data)
    return data


@router.get("/live")
def live_alias():
    return {"status": "ok", "app": "TV Fiscal WebMonitor"}


# Endpoints curtos para UptimeRobot / healthchecks externos.
public_router = APIRouter(tags=["public-health"])


@public_router.get("/health/live")
def public_live():
    return {"status": "ok", "app": "TV Fiscal WebMonitor"}


@public_router.get("/health/ready")
def public_ready(db: Session = Depends(get_db)):
    data = quick_ready(db)
    if data.get("status") != "ok":
        raise HTTPException(status_code=503, detail=data)
    return data
