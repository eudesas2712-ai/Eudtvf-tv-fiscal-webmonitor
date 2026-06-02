from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.alerts_service import build_executive_alerts

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("/summary/{project_id}")
def alerts_summary(project_id: str, db: Session = Depends(get_db)):
    return build_executive_alerts(db, project_id)


@router.get("/summary/{project_id}/export.csv")
def alerts_export_csv(project_id: str, db: Session = Depends(get_db)):
    payload = build_executive_alerts(db, project_id)
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "Severidade",
        "Categoria",
        "Título",
        "Métrica",
        "Mensagem",
        "Ação recomendada",
        "Rota",
    ])
    for alert in payload.get("alerts") or []:
        writer.writerow([
            alert.get("severity", ""),
            alert.get("category", ""),
            alert.get("title", ""),
            alert.get("metric", ""),
            alert.get("message", ""),
            alert.get("recommended_action", ""),
            alert.get("route", ""),
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=alertas_executivos_{project_id}.csv"},
    )
