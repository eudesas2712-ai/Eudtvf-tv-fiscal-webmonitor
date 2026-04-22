from urllib.parse import urlparse
from sqlalchemy.orm import Session
from app.db.models import Source, Item, Match, WatchTerm, Rule
from app.ingest.fetchers.rss import fetch_rss_links
from app.ingest.fetchers.http import fetch_html
from app.ingest.parsers.generic_news import parse_news_article, extract_links_from_list
from app.ingest.pipeline.normalize import normalize_article
from app.ingest.pipeline.dedup import is_duplicate
from app.services.evidence_service import put_html
from app.services.match_service import compute_matches
from app.services.opensearch_service import index_item
from app.utils.url_canonical import canonicalize_url
from app.utils.text_fingerprint import fingerprint_text

def ingest_source(db: Session, project_id, source: Source, mode: str = "auto", max_links: int = 30) -> dict:
    if not source.enabled:
        return {"source": source.name, "skipped": True, "reason": "disabled"}

    links = []

    if mode in ("auto","rss") and source.rss_url:
        links.extend(fetch_rss_links(source.rss_url, limit=max_links))

    if (mode in ("auto","html")) and (not links):
        # tenta base_url como página de lista
        list_html = fetch_html(source.base_url)
        links.extend(extract_links_from_list(source.base_url, list_html, limit=max_links))

    # dedup links
    seen = set()
    clean_links = []
    for u in links:
        cu = canonicalize_url(u)
        if cu in seen:
            continue
        seen.add(cu)
        clean_links.append(cu)

    # carregar termos/regras do projeto
    terms = db.query(WatchTerm).filter(WatchTerm.project_id == project_id).all()
    rules = db.query(Rule).filter(Rule.project_id == project_id, Rule.enabled == True).all()
    terms_dict = [{"term": t.term, "aliases": t.aliases, "priority": t.priority, "match_mode": t.match_mode} for t in terms]
    rules_dict = [{"name": r.name, "severity": r.severity, "enabled": r.enabled, "query_dsl": r.query_dsl} for r in rules]

    created = 0
    for url in clean_links:
        # evita reprocessar se já existe no DB
        exists = db.query(Item).filter(Item.project_id == project_id, Item.canonical_url == url).first()
        if exists:
            continue

        html = fetch_html(url)
        parsed = parse_news_article(url, html)
        art = normalize_article(parsed)

        # fingerprint para dedup
        fp = fingerprint_text(art.get("title",""), art.get("content_text",""))
        if is_duplicate(db, project_id, fp):
            continue

        # salvar evidência HTML no MinIO
        domain = urlparse(url).netloc.replace(":", "_")
        key = f"{project_id}/{domain}/{fp}.html"
        evidence_key, evidence_hash = put_html(key, html.encode("utf-8", errors="ignore"))

        item = Item(
            project_id=project_id,
            source_id=source.id,
            url=url,
            canonical_url=url,
            title=art.get("title"),
            author=art.get("author"),
            published_at=art.get("published_at"),
            content_text=art.get("content_text"),
            evidence_html_key=evidence_key,
            evidence_hash=evidence_hash,
            fingerprint=fp,
            lang="pt-BR",
            status="new",
        )
        db.add(item)
        db.flush()

        # matching
        m = compute_matches(item.title or "", item.content_text or "", terms_dict, rules_dict)
        match_row = Match(
            item_id=item.id,
            project_id=project_id,
            matched_terms={"terms": m["matched_terms"]},
            matched_rules={"rules": m["matched_rules"]},
            score=m["score"],
            reasons=m["reasons"],
        )
        db.add(match_row)

        # index OpenSearch
        index_item({
            "project_id": str(project_id),
            "item_id": str(item.id),
            "source_name": source.name,
            "url": item.url,
            "canonical_url": item.canonical_url,
            "title": item.title or "",
            "body": (item.content_text or "")[:20000],
            "published_at": (item.published_at.isoformat() if item.published_at else None),
            "fetched_at": item.fetched_at.isoformat(),
            "severity": m["severity"],
            "score": m["score"],
            "matched_terms": m["matched_terms"],
        })

        created += 1

    db.commit()
    return {"source": source.name, "links": len(clean_links), "created": created}