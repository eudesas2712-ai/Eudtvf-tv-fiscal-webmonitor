from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.executive_dashboard_service import build_executive_dashboard

router = APIRouter(prefix="/executive", tags=["Executive Dashboard"])


@router.get("/dashboard")
def executive_dashboard(
    project_id: str | None = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    return build_executive_dashboard(db, project_id=project_id, days=days)
