from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.evidence_service import get_minio_client
from app.core.config import settings


router = APIRouter(prefix="/reports/history", tags=["Histórico de Relatórios"])


@router.get("/{project_id}")
def list_generated_reports(
    project_id: str,
    report_family: str | None = Query(default=None),
    report_type: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        text("""
            SELECT
                id,
                project_id,
                report_family,
                report_type,
                title,
                filename,
                object_key,
                public_url,
                content_type,
                filters,
                file_size,
                generated_by,
                created_at
            FROM generated_reports
            WHERE project_id = CAST(:project_id AS uuid)
              AND (
                COALESCE(CAST(:report_family AS text), '') = ''
                OR report_family = CAST(:report_family AS text)
              )
              AND (
                COALESCE(CAST(:report_type AS text), '') = ''
                OR report_type = CAST(:report_type AS text)
              )
              AND (
                NULLIF(CAST(:date_from AS text), '') IS NULL
                OR created_at >= NULLIF(CAST(:date_from AS text), '')::date
              )
              AND (
                NULLIF(CAST(:date_to AS text), '') IS NULL
                OR created_at < (NULLIF(CAST(:date_to AS text), '')::date + INTERVAL '1 day')
              )
            ORDER BY created_at DESC
            LIMIT :limit
        """),
        {
            "project_id": project_id,
            "report_family": report_family or "",
            "report_type": report_type or "",
            "date_from": date_from or "",
            "date_to": date_to or "",
            "limit": limit,
        },
    ).mappings().all()

    return {"items": [dict(row) for row in rows]}


@router.get("/download/{report_id}")
def download_generated_report(report_id: str, db: Session = Depends(get_db)):
    row = db.execute(
        text("""
            SELECT
                id,
                filename,
                object_key,
                content_type
            FROM generated_reports
            WHERE id = CAST(:report_id AS uuid)
            LIMIT 1
        """),
        {"report_id": report_id},
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Relatório não encontrado.")

    client = get_minio_client()

    try:
        obj = client.get_object(Bucket=settings.MINIO_BUCKET, Key=row["object_key"])
        content = obj["Body"].read()
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Arquivo do relatório não encontrado no armazenamento: {exc}")

    filename = row["filename"] or f"relatorio_{report_id}.pdf"
    content_type = row["content_type"] or "application/pdf"

    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
