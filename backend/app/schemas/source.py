from pydantic import BaseModel
import uuid

class SourceOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    base_url: str
    rss_url: str | None = None
    enabled: bool
    interval_minutes: int

    class Config:
        from_attributes = True