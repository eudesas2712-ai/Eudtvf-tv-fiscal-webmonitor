from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.admin_auth import require_admin_access
from app.db.session import get_db
from app.services.backup_scheduler import auto_backup_status, run_auto_backup_once
from app.services.maintenance_service import (
    cleanup_database_logs,
    cleanup_old_backups,
    create_backup,
    delete_backup,
    generate_security_export,
    get_backup_path,
    list_backups,
    archive_notification_errors,
    archive_homologation_notification_errors,
    backup_freshness,
    maintenance_status,
)

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


class BackupRequest(BaseModel):
    include_database: bool = True
    include_minio: bool = False
    include_manifest: bool = True
    minio_max_objects: int = Field(default=5000, ge=1, le=50000)
    label: str | None = None


class ArchiveErrorsRequest(BaseModel):
    hours: int = Field(default=24, ge=1, le=8760)
    dry_run: bool = True
    archived_by: str = "admin"
    reason: str = "Saneamento operacional V40"


class ArchiveHomologationErrorsRequest(BaseModel):
    hours: int = Field(default=24, ge=1, le=720)
    dry_run: bool = True
    archived_by: str = "admin"
    reason: str = "Arquivamento de erros de homologação V40.1"


class CleanupRequest(BaseModel):
    days: int = Field(default=90, ge=1, le=3650)
    dry_run: bool = True
    cleanup_dry_run_notifications: bool = True
    cleanup_resolved_notifications: bool = False
    cleanup_automation_runs: bool = True
    cleanup_old_backups: bool = True
    backup_retention_days: int = Field(default=15, ge=1, le=3650)


@router.get("/status")
def status(request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return maintenance_status(db)


@router.post("/backup")
def run_backup(payload: BackupRequest, request: Request):
    require_admin_access(request)
    result = create_backup(
        include_database=payload.include_database,
        include_minio=payload.include_minio,
        include_manifest=payload.include_manifest,
        minio_max_objects=payload.minio_max_objects,
        label=payload.label,
    )
    return result.__dict__


@router.get("/backups")
def backups(request: Request):
    require_admin_access(request)
    return list_backups()


@router.get("/backups/{filename}")
def download_backup(filename: str, request: Request):
    require_admin_access(request)
    try:
        path = get_backup_path(filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return FileResponse(path, filename=filename, media_type="application/zip")


@router.delete("/backups/{filename}")
def remove_backup(filename: str, request: Request):
    require_admin_access(request)
    try:
        delete_backup(filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"deleted": True, "filename": filename}


@router.post("/cleanup")
def cleanup(payload: CleanupRequest, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    result = cleanup_database_logs(
        db,
        days=payload.days,
        dry_run=payload.dry_run,
        cleanup_dry_run_notifications=payload.cleanup_dry_run_notifications,
        cleanup_resolved_notifications=payload.cleanup_resolved_notifications,
        cleanup_automation_runs=payload.cleanup_automation_runs,
    )
    if payload.cleanup_old_backups:
        if payload.dry_run:
            result["old_backups"] = {"dry_run": True, "retention_days": payload.backup_retention_days}
        else:
            result["old_backups"] = cleanup_old_backups(payload.backup_retention_days)
    return result


@router.get("/backup-freshness")
def backup_freshness_status(request: Request):
    require_admin_access(request)
    return backup_freshness()


@router.get("/auto-backup/status")
def auto_backup_status_route(request: Request):
    require_admin_access(request)
    return auto_backup_status()


@router.post("/auto-backup/run")
def run_auto_backup(request: Request):
    require_admin_access(request)
    return run_auto_backup_once(label="manual_auto")


@router.post("/archive-notification-errors")
def archive_errors(payload: ArchiveErrorsRequest, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return archive_notification_errors(
        db,
        hours=payload.hours,
        dry_run=payload.dry_run,
        archived_by=payload.archived_by,
        reason=payload.reason,
    )


@router.post("/archive-homologation-errors")
def archive_homologation_errors(payload: ArchiveHomologationErrorsRequest, request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    return archive_homologation_notification_errors(
        db,
        hours=payload.hours,
        dry_run=payload.dry_run,
        archived_by=payload.archived_by,
        reason=payload.reason,
    )


@router.get("/security-export.csv")
def security_export(request: Request, db: Session = Depends(get_db)):
    require_admin_access(request)
    content = generate_security_export(db)
    return PlainTextResponse(
        content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=tvfiscal_security_export.csv"},
    )
