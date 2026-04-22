import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db, engine, Base
from app.db.models import Source, WatchTerm, Item
from app.ingest.news_collector import collect_links, collect_article

router = APIRouter()

@router.post("/run/{project_id}")
def run_ingest(project_id: str, db: Session = Depends(get_db)):
    Base.metadata.create_all(bind=engine)

    project_uuid = uuid.UUID(project_id)

    sources = db.query(Source).filter(Source.project_id == project_uuid).all()
    terms = db.query(WatchTerm).filter(WatchTerm.project_id == project_uuid).all()

    term_list = [t.term.lower() for t in terms]

    collected = 0
    matches = 0
    failed_sources = []

    for source in sources:
        try:
            links = collect_links(source.base_url)
        except Exception as e:
            failed_sources.append({
                "source": source.name,
                "error": str(e)
            })
            continue

        for link in links:
            article = collect_article(link)

            if not article:
                continue

            text = article["text"].lower()
            matched = [t for t in term_list if t in text]

            if matched:
                exists = db.query(Item).filter(
                    Item.url == link,
                    Item.project_id == project_uuid
                ).first()

                if exists:
                    continue

                exists_title = db.query(Item).filter(
                    Item.title == article["title"][:500],
                    Item.project_id == project_uuid
                ).first()

                if exists_title:
                    continue

                item = Item(
                    project_id=project_uuid,
                    source_id=source.id,
                    title=article["title"][:500],
                    url=link[:1024],
                    content_text=article["text"],
                    matched_terms={"terms": matched}
                )

                db.add(item)
                db.commit()
                matches += 1

            collected += 1

    return {
        "links_checked": collected,
        "matches_found": matches,
        "failed_sources": failed_sources
    }