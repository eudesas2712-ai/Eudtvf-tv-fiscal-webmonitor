from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import uuid

class ProjectOut(BaseModel):
    id: uuid.UUID
    name: str
    client_name: Optional[str] = None
    active: bool

class BootstrapResult(BaseModel):
    project_id: uuid.UUID
    sources: List[Dict[str, Any]]
    terms: List[str]
    rules: List[str]

class IngestRunResult(BaseModel):
    project_id: uuid.UUID
    enqueued_sources: int
    mode: str

class ItemOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    source_id: uuid.UUID
    url: str
    canonical_url: str
    title: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    fetched_at: datetime
    status: str
    score: Optional[float] = None
    severity: Optional[str] = None
    matched_terms: Optional[Dict[str, Any]] = None

class ItemDetail(BaseModel):
    item: ItemOut
    content_text: Optional[str] = None
    evidence_html_url: Optional[str] = None
    match: Optional[Dict[str, Any]] = None

class SearchResult(BaseModel):
    total: int
    items: list[ItemOut]