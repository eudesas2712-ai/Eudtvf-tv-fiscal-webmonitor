import json
import re
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.evidence_service import save_binary_evidence


def _safe_filename(filename: str) -> str:
    name = (filename or "relatorio.pdf").strip()
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", name)
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    return name[:500]


def _clean_filters(filters: dict[str, Any] | None) -> dict[str, Any]:
    if not filters:
        return {}
    return {k: v for k, v in filters.items() if v not in (None, "", [])}


def save_generated_pdf_report(
    db: Session,
    *,
    project_id: str,
    report_family: str,
    report_type: str,
    title: str,
    filename: str,
    pdf_bytes: bytes,
    filters: dict[str, Any] | None = None,
    generated_by: str | None = None,
) -> dict[str, Any]:
    safe_name = _safe_filename(filename)
    now = datetime.utcnow()
    report_id = str(uuid.uuid4())
    object_key = f"generated_reports/{project_id}/{now:%Y/%m/%d}/{report_id}_{safe_name}"

    stored_key, public_url = save_binary_evidence(
        key=object_key,
        content=pdf_bytes,
        content_type="application/pdf",
    )

    params = {
        "id": report_id,
        "project_id": project_id,
        "report_family": report_family,
        "report_type": report_type,
        "title": title,
        "filename": safe_name,
        "object_key": stored_key,
        "public_url": public_url,
        "content_type": "application/pdf",
        "filters": json.dumps(_clean_filters(filters), ensure_ascii=False),
        "file_size": len(pdf_bytes or b""),
        "generated_by": generated_by,
    }

    row = db.execute(
        text("""
            INSERT INTO generated_reports (
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
                generated_by
            )
            VALUES (
                CAST(:id AS uuid),
                CAST(:project_id AS uuid),
                :report_family,
                :report_type,
                :title,
                :filename,
                :object_key,
                :public_url,
                :content_type,
                CAST(:filters AS jsonb),
                :file_size,
                :generated_by
            )
            RETURNING
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
        """),
        params,
    ).mappings().first()

    db.commit()
    return dict(row) if row else params
