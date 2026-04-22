from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db, engine, Base
from app.db.models import Source
from app.schemas.source import SourceOut

router = APIRouter()

@router.post("/bootstrap/{project_id}")
def bootstrap_sources(project_id: str, db: Session = Depends(get_db)):
    Base.metadata.create_all(bind=engine)

    existing = db.query(Source).filter(Source.project_id == project_id).count()
    if existing > 0:
        return {"message": "Fontes já cadastradas"}

    sources = [
        Source(
            project_id=project_id,
            name="Portal Correio",
            base_url="https://portalcorreio.com.br/",
            rss_url=None,
            enabled=True,
            interval_minutes=15
        ),
        Source(
            project_id=project_id,
            name="PB Agora",
            base_url="https://www.pbagora.com.br/",
            rss_url=None,
            enabled=True,
            interval_minutes=15
        ),
        Source(
            project_id=project_id,
            name="Polêmica Paraíba",
            base_url="https://www.polemicaparaiba.com.br/",
            rss_url=None,
            enabled=True,
            interval_minutes=15
        ),
    ]

    db.add_all(sources)
    db.commit()
    return {"message": "Fontes cadastradas com sucesso"}

@router.get("/{project_id}", response_model=list[SourceOut])
def list_sources(project_id: str, db: Session = Depends(get_db)):
    return db.query(Source).filter(Source.project_id == project_id).all()