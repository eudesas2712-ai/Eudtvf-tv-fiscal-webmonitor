from pydantic import BaseModel
from typing import Optional
import uuid

class ProjectOut(BaseModel):
    id: uuid.UUID
    name: str
    client_name: Optional[str] = None
    active: bool

    class Config:
        from_attributes = True