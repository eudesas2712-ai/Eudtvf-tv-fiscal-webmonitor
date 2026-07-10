import re
import uuid
import unicodedata
from collections import Counter
from datetime import datetime
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.db.models import (
    Advertiser,
    AdvertiserAlias,
    Item,
    Portal,
    ProjectAdvertiser,
    ProjectPortal,
    Source,
    WatchTerm,
)
from app.ingest.news_collector import collect_article, collect_links


POSITIVE_WORDS = {
    "aprova", "aprovado", "cresce", "crescimento", "avanço", "avanca", "melhora",
    "benefício", "beneficio", "lança", "lanca", "inaugura", "expansão", "expansao",
    "recorde", "positivo", "vitória", "vitoria", "investimento", "entrega", "premio", "prêmio",
}

NEGATIVE_WORDS = {
    "crise", "queda", "denúncia", "denuncia", "investigação", "investigacao", "prisão",
    "prisao", "morte", "morre", "condenado", "condenação", "condenacao", "fraude",
    "escândalo", "escandalo", "protesto", "acidente", "crime", "suspeito", "irregular",
}

TOPIC_KEYWORDS = {
    "Política": ["governo", "prefeitura", "vereador", "deputado", "assembleia", "eleição", "eleicao", "política", "politica"],
    "Saúde": ["saúde", "saude", "hospital", "vacina", "sus", "médico", "medico", "unimed", "hapvida"],
    "Economia": ["economia", "preço", "preco", "imposto", "licitação", "licitacao", "investimento", "empresa", "comércio", "comercio"],
    "Segurança": ["polícia", "policia", "prisão", "prisao", "crime", "prf", "tráfico", "trafico", "homicídio", "homicidio"],
    "Educação": ["educação", "educacao", "universidade", "faculdade", "escola", "enem", "curso"],
    "Cultura": ["show", "cultura", "música", "musica", "festival", "cinema", "filme"],
    "Esporte": ["esporte", "futebol", "jogo", "neymar", "copa", "time"],
}


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


def _lexical_norm(value: str | None) -> str:
    """Normaliza texto para casamento lexical auditável de termos/marcas.

    Diferente do método anterior por substring, esta versão transforma acentos
    e pontuação em espaços para permitir casamento por fronteira de palavra.
    Assim, a marca "Amil" não é detectada dentro de "família".
    """
    text = (value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


BOILERPLATE_PATTERNS = [
    r"@?\d{4}\s*-\s*All Right Reserved\.\s*Designed and Developed by WSCOM",
    r"Siga o canal do WSCOM no Whatsapp\.?",
    r"Siga o canal do WSCOM no WhatsApp\.?",
    r"Siga o canal do Polêmica Paraíba no Whatsapp\.?",
    r"Siga o canal do Polêmica Paraíba no WhatsApp\.?",
]


LISTING_TITLE_PATTERNS = [
    "tudo sobre ",
    "ultimas noticias",
    "últimas notícias",
    "midias e entretenimento",
    "mídias e entretenimento",
    "opiniao - artigos",
    "opinião - artigos",
    "politica - analises",
    "política - análises",
    "esporte - noticias",
    "esporte - notícias",
    "noticias resultados e analises",
    "notícias resultados e análises",
]


def _clean_editorial_text(text: str | None) -> str:
    clean = text or ""
    for pattern in BOILERPLATE_PATTERNS:
        clean = re.sub(pattern, " ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def _is_listing_or_section_page(title: str | None, url: str | None, text: str | None = None) -> bool:
    title_norm = _lexical_norm(title)
    url_lower = (url or "").lower()

    if any(pattern in title_norm for pattern in LISTING_TITLE_PATTERNS):
        return True

    # Páginas de listagem costumam ter URL curta de seção/tag ou agregados por município.
    listing_url_tokens = ["/tag/", "/tags/", "/category/", "/categoria/", "/page/", "/editoria/", "/assunto/"]
    if any(token in url_lower for token in listing_url_tokens):
        return True

    # Rejeita títulos muito genéricos de seção que passaram pelo coletor.
    generic_exact = {
        "politica", "economia", "esporte", "cultura", "saude", "seguranca",
        "ultimas noticias", "opiniao", "entretenimento",
    }
    if title_norm in generic_exact:
        return True

    return False


def _summary(text: str, limit: int = 360) -> str:
    clean = _clean_editorial_text(text)
    if len(clean) <= limit:
        return clean
    return clean[:limit].rsplit(" ", 1)[0] + "..."


def _sentiment(text: str) -> tuple[str, int]:
    lower = _norm(text)
    positive = sum(1 for word in POSITIVE_WORDS if word in lower)
    negative = sum(1 for word in NEGATIVE_WORDS if word in lower)
    score = max(-100, min(100, (positive - negative) * 20))
    if score >= 25:
        return "positivo", score
    if score <= -25:
        return "negativo", score
    return "neutro", score


def _topic(text: str) -> str:
    lower = _norm(text)
    scores = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        scores.append((topic, sum(1 for k in keywords if k in lower)))
    scores.sort(key=lambda row: row[1], reverse=True)
    if scores and scores[0][1] > 0:
        return scores[0][0]
    return "Geral"


def _editorial_score(text: str, matched_terms: list[str]) -> int:
    clean_len = len(text or "")
    score = 35
    if clean_len >= 600:
        score += 20
    if clean_len >= 1200:
        score += 15
    if matched_terms:
        score += min(25, 8 * len(matched_terms))
    return max(0, min(100, score))


def _registered_terms(db: Session, project_uuid: uuid.UUID) -> list[str]:
    terms = [
        row.term.strip()
        for row in db.query(WatchTerm).filter(WatchTerm.project_id == project_uuid, WatchTerm.active.is_(True)).all()
        if row.term and row.term.strip()
    ]

    linked = (
        db.query(ProjectAdvertiser, Advertiser)
        .join(Advertiser, Advertiser.id == ProjectAdvertiser.advertiser_id)
        .filter(ProjectAdvertiser.project_id == project_uuid, ProjectAdvertiser.active.is_(True), Advertiser.active.is_(True))
        .all()
    )
    advertiser_ids = []
    for _, advertiser in linked:
        if advertiser.name:
            terms.append(advertiser.name.strip())
        advertiser_ids.append(advertiser.id)

    if advertiser_ids:
        aliases = (
            db.query(AdvertiserAlias)
            .filter(AdvertiserAlias.advertiser_id.in_(advertiser_ids), AdvertiserAlias.active.is_(True))
            .all()
        )
        for alias in aliases:
            if alias.alias:
                terms.append(alias.alias.strip())

    deduped = []
    seen = set()
    for term in terms:
        key = _norm(term)
        if key and key not in seen:
            seen.add(key)
            deduped.append(term)
    return deduped


def _match_terms(text: str, terms: list[str]) -> list[str]:
    """Casa termos/marcas por palavra/frase completa, evitando falso positivo.

    Exemplo corrigido: "Amil" não deve aparecer em matérias que só contenham
    "família". Para termos de uma palavra, exige fronteira lexical; para frases,
    exige a frase normalizada completa com fronteiras.
    """
    haystack = f" {_lexical_norm(text)} "
    matches: list[str] = []
    seen: set[str] = set()
    for term in terms:
        key = _lexical_norm(term)
        if not key or key in seen:
            continue
        # Ignora aliases curtos demais, exceto quando são siglas fortes com 3+ chars.
        if len(key.replace(" ", "")) < 3:
            continue
        pattern = rf"(?<![a-z0-9]){re.escape(key)}(?![a-z0-9])"
        if re.search(pattern, haystack):
            matches.append(term)
            seen.add(key)
    return matches


def _source_for_portal(db: Session, project_uuid: uuid.UUID, portal: Portal) -> Source:
    source = (
        db.query(Source)
        .filter(Source.project_id == project_uuid, Source.base_url == portal.base_url)
        .first()
    )
    if source:
        if not source.enabled:
            source.enabled = True
            db.commit()
        return source

    source = Source(
        project_id=project_uuid,
        name=portal.name,
        base_url=portal.base_url,
        rss_url=None,
        enabled=True,
        interval_minutes=portal.interval_minutes or 60,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def get_editorial_sources(db: Session, project_uuid: uuid.UUID) -> list[Source]:
    sources_by_url: dict[str, Source] = {}

    for source in db.query(Source).filter(Source.project_id == project_uuid, Source.enabled.is_(True)).all():
        sources_by_url[source.base_url.rstrip("/")] = source

    linked_portals = (
        db.query(Portal)
        .join(ProjectPortal, ProjectPortal.portal_id == Portal.id)
        .filter(
            ProjectPortal.project_id == project_uuid,
            ProjectPortal.active.is_(True),
            Portal.active.is_(True),
            Portal.monitor_editorial.is_(True),
        )
        .order_by(Portal.name.asc())
        .all()
    )
    for portal in linked_portals:
        source = _source_for_portal(db, project_uuid, portal)
        sources_by_url[source.base_url.rstrip("/")] = source

    return list(sources_by_url.values())


def run_editorial_collection(
    db: Session,
    project_id: str,
    collect_all: bool = False,
    limit_per_source: int = 30,
) -> dict:
    project_uuid = uuid.UUID(project_id)
    sources = get_editorial_sources(db, project_uuid)
    terms = _registered_terms(db, project_uuid)

    checked = 0
    inserted = 0
    matched_count = 0
    duplicates = 0
    failed_sources: list[dict] = []
    source_summaries: list[dict] = []

    for source in sources:
        source_checked = 0
        source_inserted = 0
        try:
            links = collect_links(source.base_url)[: max(1, min(limit_per_source, 80))]
        except Exception as exc:
            failed_sources.append({"source": source.name, "error": str(exc)})
            continue

        for link in links:
            checked += 1
            source_checked += 1
            exists = db.query(Item).filter(Item.project_id == project_uuid, Item.url == link).first()
            if exists:
                duplicates += 1
                continue

            article = collect_article(link)
            if not article:
                continue

            article_title = article.get("title") or "Sem título"
            article_text = _clean_editorial_text(article.get("text") or "")
            if _is_listing_or_section_page(article_title, link, article_text):
                continue
            if len(article_text) < 400:
                continue

            combined = f"{article_title} {article_text}"
            matched_terms = _match_terms(combined, terms)
            if matched_terms:
                matched_count += 1
            if not collect_all and not matched_terms:
                continue

            sentiment, sentiment_score = _sentiment(combined)
            topic = _topic(combined)
            score = _editorial_score(article_text, matched_terms)
            parsed_domain = urlparse(source.base_url).netloc.replace("www.", "")
            item = Item(
                project_id=project_uuid,
                source_id=source.id,
                title=article_title[:500],
                url=link[:1024],
                content_text=article_text,
                matched_terms={"terms": matched_terms},
                source_name=source.name or parsed_domain,
                summary=_summary(article_text),
                sentiment=sentiment,
                sentiment_score=sentiment_score,
                topic=topic,
                editorial_score=score,
                published_at=None,
            )
            db.add(item)
            db.commit()
            inserted += 1
            source_inserted += 1

        source_summaries.append({"source": source.name, "checked": source_checked, "inserted": source_inserted})

    return {
        "project_id": project_id,
        "sources": len(sources),
        "links_checked": checked,
        "inserted": inserted,
        "matched_articles": matched_count,
        "duplicates": duplicates,
        "collect_all": collect_all,
        "terms_available": len(terms),
        "failed_sources": failed_sources,
        "source_summaries": source_summaries,
    }


def reclassify_editorial_items(db: Session, project_id: str, delete_listing_pages: bool = True) -> dict:
    """Reprocessa matérias já coletadas após ajustes de qualidade editorial.

    - remove falsos positivos de termos/marcas por substring;
    - limpa boilerplate;
    - recalcula tema, sentimento e score;
    - remove páginas de categoria/listagem se solicitado.
    """
    project_uuid = uuid.UUID(project_id)
    terms = _registered_terms(db, project_uuid)
    items = db.query(Item).filter(Item.project_id == project_uuid).all()

    processed = 0
    deleted = 0
    matched_count = 0
    cleaned_count = 0

    for item in list(items):
        original_text = item.content_text or ""
        clean_text = _clean_editorial_text(original_text)
        title = item.title or "Sem título"

        if delete_listing_pages and _is_listing_or_section_page(title, item.url, clean_text):
            db.delete(item)
            deleted += 1
            continue

        combined = f"{title} {clean_text}"
        matched_terms = _match_terms(combined, terms)
        sentiment, sentiment_score = _sentiment(combined)
        topic = _topic(combined)
        score = _editorial_score(clean_text, matched_terms)

        if clean_text != original_text:
            cleaned_count += 1

        item.content_text = clean_text
        item.summary = _summary(clean_text)
        item.matched_terms = {"terms": matched_terms, "match_mode": "strict_word_boundary"}
        item.sentiment = sentiment
        item.sentiment_score = sentiment_score
        item.topic = topic
        item.editorial_score = score
        if matched_terms:
            matched_count += 1
        processed += 1

    db.commit()
    return {
        "project_id": project_id,
        "processed": processed,
        "deleted_listing_pages": deleted,
        "matched_articles": matched_count,
        "cleaned_articles": cleaned_count,
        "terms_available": len(terms),
        "match_mode": "strict_word_boundary",
    }

def editorial_rows(
    db: Session,
    project_id: str,
    q: str | None = None,
    source_name: str | None = None,
    term: str | None = None,
    sentiment: str | None = None,
    topic: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 300,
) -> list[dict]:
    project_uuid = uuid.UUID(project_id)
    query = (
        db.query(Item, Source)
        .join(Source, Item.source_id == Source.id)
        .filter(Item.project_id == project_uuid)
    )
    if source_name:
        query = query.filter(Source.name == source_name)
    if sentiment:
        query = query.filter(Item.sentiment == sentiment)
    if topic:
        query = query.filter(Item.topic == topic)
    if date_from:
        try:
            query = query.filter(Item.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            query = query.filter(Item.created_at <= datetime.fromisoformat(date_to))
        except ValueError:
            pass

    rows = query.order_by(Item.created_at.desc()).limit(max(1, min(limit, 1000))).all()
    results = []
    q_norm = _norm(q)
    term_norm = _norm(term)
    for item, source in rows:
        matched_terms = item.matched_terms or {"terms": []}
        terms = matched_terms.get("terms", []) if isinstance(matched_terms, dict) else []
        haystack = f"{item.title} {item.content_text} {source.name} {' '.join(terms)}".lower()
        if q_norm and q_norm not in haystack:
            continue
        if term_norm and term_norm not in [str(t).lower() for t in terms]:
            continue
        results.append({
            "id": str(item.id),
            "project_id": str(item.project_id),
            "title": item.title,
            "url": item.url,
            "summary": item.summary or _summary(item.content_text),
            "content_text": item.content_text,
            "matched_terms": matched_terms,
            "source_name": item.source_name or source.name,
            "source_url": source.base_url,
            "sentiment": item.sentiment or "neutro",
            "sentiment_score": item.sentiment_score or 0,
            "topic": item.topic or "Geral",
            "editorial_score": item.editorial_score or 0,
            "evidence_html_url": item.evidence_html_url,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "published_at": item.published_at.isoformat() if item.published_at else None,
        })
    return results


def editorial_summary(
    db: Session,
    project_id: str,
    q: str | None = None,
    source_name: str | None = None,
    term: str | None = None,
    sentiment: str | None = None,
    topic: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    rows = editorial_rows(
        db=db,
        project_id=project_id,
        q=q,
        source_name=source_name,
        term=term,
        sentiment=sentiment,
        topic=topic,
        date_from=date_from,
        date_to=date_to,
        limit=1000,
    )
    sources = Counter(row["source_name"] or "Desconhecido" for row in rows)
    terms = Counter()
    sentiments = Counter(row["sentiment"] for row in rows)
    topics = Counter(row["topic"] for row in rows)
    for row in rows:
        for term in (row.get("matched_terms") or {}).get("terms", []):
            terms[str(term)] += 1
    return {
        "project_id": project_id,
        "total_items": len(rows),
        "total_terms": sum(terms.values()),
        "sources_count": len(sources),
        "topics_count": len(topics),
        "sentiment": dict(sentiments),
        "top_sources": [{"name": k, "count": v} for k, v in sources.most_common(10)],
        "top_terms": [{"term": k, "count": v} for k, v in terms.most_common(10)],
        "top_topics": [{"topic": k, "count": v} for k, v in topics.most_common(10)],
        "latest": rows[:8],
    }
