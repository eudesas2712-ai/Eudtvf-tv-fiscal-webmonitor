from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db, engine, Base
from app.db.models import WatchTerm

router = APIRouter(prefix="/terms", tags=["Terms"])


@router.post("/bootstrap/{project_id}")
def bootstrap_terms(project_id: str, db: Session = Depends(get_db)):
    Base.metadata.create_all(bind=engine)

    existing = db.query(WatchTerm).filter(WatchTerm.project_id == project_id).count()
    if existing > 0:
        return {"message": "Termos já cadastrados"}

    terms = [
        WatchTerm(project_id=project_id, term="Walber Virgulino"),
        WatchTerm(project_id=project_id, term="Prefeitura de Cabedelo"),
        WatchTerm(project_id=project_id, term="Eleições Cabedelo"),
        WatchTerm(project_id=project_id, term="Governo da Paraíba"),
        WatchTerm(project_id=project_id, term="Intermares"),
        WatchTerm(project_id=project_id, term="poço"),
        WatchTerm(project_id=project_id, term="camboinha"),
        WatchTerm(project_id=project_id, term="jacaré"),
        WatchTerm(project_id=project_id, term="porto de cabedelo"),
        WatchTerm(project_id=project_id, term="Unimed"),
        WatchTerm(project_id=project_id, term="Prefeitura Municipal de João Pessoa"),
        WatchTerm(project_id=project_id, term="Câmara Municipal de João Pessoa"),
        WatchTerm(project_id=project_id, term="Assembleia Legislativa da Paraíba"),
    ]

    db.add_all(terms)
    db.commit()
    return {"message": "Termos cadastrados com sucesso"}


@router.get("/{project_id}")
def list_terms(project_id: str, db: Session = Depends(get_db)):
    rows = db.query(WatchTerm).filter(WatchTerm.project_id == project_id).all()

    return [
        {
            "id": str(row.id),
            "project_id": str(row.project_id),
            "term": row.term,
            "active": row.active,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]