from pydantic import BaseModel
import uuid

class TermOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    term: str
    aliases: dict
    match_mode: str
    priority: int

    class Config:
        from_attributes = True