from app.workers.celery_app import celery
from app.db.session import SessionLocal
from app.db.models import Source
from app.services.ingest_service import ingest_source

@celery.task(name="ingest.project_source")
def ingest_project_source(project_id: str, source_id: str, mode: str = "auto"):
    db = SessionLocal()
    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            return {"ok": False, "error": "source not found"}
        res = ingest_source(db, project_id, source, mode=mode)
        return {"ok": True, "result": res}
    finally:
        db.close()