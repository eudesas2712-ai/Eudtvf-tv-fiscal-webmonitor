from fastapi import APIRouter, Query
from app.services.opensearch_service import search_items
from app.schemas.dtos import SearchResult, ItemOut

router = APIRouter()

@router.get("", response_model=SearchResult)
def search(
    project_id: str = Query(...),
    q: str | None = Query(None),
    source_name: str | None = Query(None),
    severity: str | None = Query(None),
    size: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    total, hits = search_items(
        project_id=project_id,
        q=q,
        filters={"source_name": source_name, "severity": severity},
        size=size,
        offset=offset,
    )
    items = []
    for h in hits:
        items.append(ItemOut(
            id=h["item_id"],
            project_id=project_id,
            source_id="",
            url=h["url"],
            canonical_url=h["canonical_url"],
            title=h.get("title"),
            author=None,
            published_at=None,
            fetched_at=None,  # UI usa title/url/score/severity
            status="new",
            score=h.get("score"),
            severity=h.get("severity"),
            matched_terms={"terms": h.get("matched_terms", [])},
        ))
    return SearchResult(total=total, items=items)