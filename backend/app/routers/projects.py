from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models import BannerItem
from app.db.session import get_db

router = APIRouter(prefix="/projects", tags=["Projects"])


def _clean_project_label(label: str | None, project_id: str | None) -> str:
    raw_label = str(label or "").strip()
    raw_id = str(project_id or "").strip()

    base_label = raw_label.split("·")[0].strip()

    if base_label:
        return base_label
    if raw_label:
        return raw_label
    if raw_id:
        return raw_id

    return "Projeto sem identificação"


@router.get("/intel-options/")
def get_intel_options(db: Session = Depends(get_db)):
    rows = (
        db.query(BannerItem.project_id)
        .distinct()
        .all()
    )

    results = []

    for row in rows:
        project_id = str(getattr(row, "project_id", "") or "").strip()
        if not project_id:
            continue

        label = f"Projeto {project_id[:8]}"

        results.append(
            {
                "project_id": project_id,
                "label": _clean_project_label(label, project_id),
            }
        )

    results.sort(key=lambda item: item["label"].lower())
    return results