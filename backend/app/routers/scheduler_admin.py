import csv
import io
from fastapi.responses import StreamingResponse

from fastapi import APIRouter, Depends, Query
from app.core.admin_auth import require_admin_access

from app.services.snapshot_scheduler import (
    get_snapshot_scheduler_status,
    run_snapshot_now,
    enable_snapshot_scheduler,
    disable_snapshot_scheduler,
    list_scheduler_runs,
    clear_scheduler_runs,
    run_registered_portal_scans_now,
)


router = APIRouter(
    prefix="/admin/scheduler",
    tags=["scheduler"],
    dependencies=[Depends(require_admin_access)],
)


@router.get("/status")
def scheduler_status():
    return get_snapshot_scheduler_status()


@router.post("/run-now")
def scheduler_run_now():
    return run_snapshot_now()


@router.post("/enable")
def scheduler_enable():
    return enable_snapshot_scheduler()


@router.post("/run-portal-scan-now")
def scheduler_run_portal_scan_now(
    project_id: str | None = Query(default=None),
    save_rejected: bool = Query(default=True),
):
    return run_registered_portal_scans_now(project_id=project_id, save_rejected=save_rejected)


@router.post("/disable")
def scheduler_disable():
    return disable_snapshot_scheduler()


@router.get("/history")
def scheduler_history(
    status: str | None = Query(default=None),
    project_id: str | None = Query(default=None),
    limit: int = Query(default=50),
):
    return {
        "items": list_scheduler_runs(
            limit=limit,
            status=status,
            project_id=project_id,
        )
    }


@router.delete("/history")
def scheduler_clear_history(
    status: str | None = Query(default=None),
    project_id: str | None = Query(default=None),
):
    return clear_scheduler_runs(
        status=status,
        project_id=project_id,
    )

@router.get("/history/export.csv")
def scheduler_history_export_csv(
    status: str | None = Query(default=None),
    project_id: str | None = Query(default=None),
    limit: int = Query(default=500),
):
    items = list_scheduler_runs(
        limit=limit,
        status=status,
        project_id=project_id,
    )

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    writer.writerow([
        "Data",
        "Projeto",
        "Status",
        "Mensagem",
    ])

    for item in items:
        writer.writerow([
            item.get("created_at", ""),
            item.get("project_id", ""),
            item.get("status", ""),
            item.get("message", ""),
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=scheduler_history.csv"
        },
    )