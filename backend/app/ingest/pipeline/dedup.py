from sqlalchemy.orm import Session
from app.db.models import Item

def is_duplicate(db: Session, project_id, fingerprint: str) -> bool:
    exists = db.query(Item).filter(Item.project_id == project_id, Item.fingerprint == fingerprint).first()
    return exists is not None