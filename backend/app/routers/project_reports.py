from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.models import Advertiser, BannerItem, Item, Portal, Project, ProjectAdvertiser, ProjectPortal, Segment, Source
from app.db.session import get_db
from app.services.project_report_generator import build_project_pdf_response, build_project_pptx_response
from app.services.registry_matcher import resolve_advertiser_for_item
from app.services.identification_quality import is_unknown_advertiser, split_share_of_voice, identification_alerts, display_advertiser_name

router = APIRouter(prefix="/reports/project", tags=["Relatórios por Projeto"])


def _uuid(value: str, label: str = "id") -> UUID:
    try:
        return UUID(str(value))
    except Exception:
        raise HTTPException(status_code=400, detail=f"{label} inválido.")


def _parse_dt(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Data inválida: {value}")


def _safe_num(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


ANALYSIS_MODES = {
    "market_wide": "Mercado amplo",
    "preserved_evidence": "Somente com evidência preservada",
    "classified_ads": "Somente publicidade classificada",
    "checking_auditable": "Somente checking auditável",
}


def _normalize_analysis_mode(value: str | None) -> str:
    value = (value or "market_wide").strip().lower()
    return value if value in ANALYSIS_MODES else "market_wide"


def _row_matches_analysis_mode(row: BannerItem, mode: str) -> bool:
    if mode == "checking_auditable":
        return getattr(row, "checking_status", None) == "auditavel"
    if mode == "classified_ads":
        return getattr(row, "content_type", None) == "advertising" and getattr(row, "market_status", None) == "incluido"
    if mode == "preserved_evidence":
        return bool(getattr(row, "has_preserved_evidence", None)) and getattr(row, "market_status", None) == "incluido"
    return getattr(row, "market_status", None) == "incluido"


def _mode_payload(mode: str, total_rows: int, analyzed_rows: int, auditables_count: int, news_count: int) -> dict:
    label = ANALYSIS_MODES.get(mode, ANALYSIS_MODES["market_wide"])
    is_referential = analyzed_rows > 0 and auditables_count == 0 and mode != "checking_auditable"
    no_checking_data = mode == "checking_auditable" and analyzed_rows == 0
    warnings = []
    if is_referential:
        warnings.append(
            f"Leitura referencial: o relatório possui {analyzed_rows} item(ns) de mercado, "
            "mas nenhuma evidência auditável para checking no recorte. "
            "Use o modo 'Somente checking auditável' para prova documental."
        )
    if no_checking_data:
        warnings.append("Nenhuma evidência auditável foi encontrada para checking no recorte selecionado.")
    if news_count and mode != "checking_auditable":
        warnings.append(f"Há {news_count} item(ns) editorial(is) candidato(s) a monitoramento de notícias; eles não devem ser tratados como publicidade auditável.")
    return {
        "mode": mode,
        "label": label,
        "total_detected": total_rows,
        "analyzed_items": analyzed_rows,
        "auditables": auditables_count,
        "is_referential": is_referential,
        "no_checking_data": no_checking_data,
        "warnings": warnings,
    }


def _format(row: BannerItem) -> str:
    width = getattr(row, "width", None) or getattr(row, "normalized_width", None) or 0
    height = getattr(row, "height", None) or getattr(row, "normalized_height", None) or 0
    return f"{width} x {height}" if width and height else "Não identificado"


def _date(row: BannerItem) -> str:
    value = getattr(row, "created_at", None)
    if not value:
        return "—"
    return value.strftime("%d/%m/%Y %H:%M")


def _project_payload(db: Session, project: Project) -> dict:
    segment = db.query(Segment).filter(Segment.id == project.segment_id).first() if project.segment_id else None
    return {
        "id": str(project.id),
        "name": project.name,
        "client_name": project.client_name,
        "segment_id": str(project.segment_id) if project.segment_id else None,
        "segment_name": segment.name if segment else None,
        "description": project.description,
        "active": project.active,
        "monitor_publicity": project.monitor_publicity,
        "monitor_editorial": project.monitor_editorial,
        "monitor_market": project.monitor_market,
        "monitor_checking": project.monitor_checking,
        "created_at": project.created_at.isoformat() if project.created_at else None,
    }


def _load_linked_portals(db: Session, project_id: UUID) -> list[dict]:
    rows = (
        db.query(ProjectPortal, Portal)
        .join(Portal, Portal.id == ProjectPortal.portal_id)
        .filter(ProjectPortal.project_id == project_id, ProjectPortal.active.is_(True), Portal.active.is_(True))
        .order_by(Portal.name.asc())
        .all()
    )
    return [
        {
            "id": str(portal.id),
            "name": portal.name,
            "base_url": portal.base_url,
            "category": portal.category,
            "monitor_publicity": portal.monitor_publicity,
            "monitor_editorial": portal.monitor_editorial,
        }
        for _link, portal in rows
    ]


def _load_linked_advertisers(db: Session, project_id: UUID) -> list[dict]:
    rows = (
        db.query(ProjectAdvertiser, Advertiser)
        .join(Advertiser, Advertiser.id == ProjectAdvertiser.advertiser_id)
        .filter(ProjectAdvertiser.project_id == project_id, ProjectAdvertiser.active.is_(True), Advertiser.active.is_(True))
        .order_by(ProjectAdvertiser.role.asc(), Advertiser.name.asc())
        .all()
    )
    payload = []
    for link, advertiser in rows:
        segment = db.query(Segment).filter(Segment.id == advertiser.segment_id).first() if advertiser.segment_id else None
        payload.append(
            {
                "id": str(advertiser.id),
                "name": advertiser.name,
                "legal_name": advertiser.legal_name,
                "segment_id": str(advertiser.segment_id) if advertiser.segment_id else None,
                "segment_name": segment.name if segment else None,
                "role": link.role or "monitorado",
            }
        )
    return payload




def _item_date(item: Item) -> str:
    value = getattr(item, "published_at", None) or getattr(item, "created_at", None)
    if not value:
        return "—"
    return value.strftime("%d/%m/%Y %H:%M")


def _editorial_terms(item: Item) -> list[str]:
    matched = getattr(item, "matched_terms", None) or {}
    if isinstance(matched, dict):
        terms = matched.get("terms") or []
        return [str(term) for term in terms if str(term).strip()]
    return []


def _editorial_payload(item: Item, source_name: str | None = None) -> dict:
    terms = _editorial_terms(item)
    return {
        "id": str(item.id),
        "created_at": _item_date(item),
        "title": item.title or "Sem título",
        "source_name": source_name or item.source_name or "Fonte não identificada",
        "url": item.url,
        "summary": item.summary or (item.content_text or "")[:360],
        "sentiment": item.sentiment or "neutro",
        "sentiment_score": int(_safe_num(item.sentiment_score)),
        "topic": item.topic or "Geral",
        "editorial_score": int(_safe_num(item.editorial_score)),
        "matched_terms": terms,
        "terms_label": ", ".join(terms) if terms else "—",
    }


def _load_editorial_data(
    db: Session,
    project_id: UUID,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 80,
) -> dict:
    query = (
        db.query(Item, Source)
        .outerjoin(Source, Item.source_id == Source.id)
        .filter(Item.project_id == project_id)
    )
    if date_from:
        query = query.filter(Item.created_at >= date_from)
    if date_to:
        query = query.filter(Item.created_at <= date_to)

    rows = query.order_by(Item.created_at.desc()).all()
    items = [_editorial_payload(item, source.name if source else None) for item, source in rows]

    sources = Counter(item["source_name"] for item in items if item.get("source_name"))
    topics = Counter(item["topic"] for item in items if item.get("topic"))
    sentiments = Counter(item["sentiment"] for item in items if item.get("sentiment"))
    terms = Counter()
    matched_items = 0
    score_total = 0
    for item in items:
        score_total += int(item.get("editorial_score") or 0)
        if item.get("matched_terms"):
            matched_items += 1
        for term in item.get("matched_terms") or []:
            terms[term] += 1

    return {
        "total_items": len(items),
        "matched_items": matched_items,
        "sources_count": len(sources),
        "topics_count": len(topics),
        "sentiment_counts": dict(sentiments),
        "avg_editorial_score": round(score_total / len(items), 1) if items else 0,
        "top_sources": [{"source": key, "items": value} for key, value in sources.most_common(8)],
        "top_topics": [{"topic": key, "items": value} for key, value in topics.most_common(8)],
        "top_terms": [{"term": key, "items": value} for key, value in terms.most_common(12)],
        "latest_items": items[:limit],
    }

def _evidence_payload(row: BannerItem, advertiser_name: str | None = None) -> dict:
    title = (getattr(row, "alt_text", None) or getattr(row, "ocr_text", None) or getattr(row, "image_url", None) or "—")
    return {
        "id": str(row.id),
        "created_at": _date(row),
        "advertiser": advertiser_name or getattr(row, "advertiser_name", None) or "Não identificado",
        "portal": getattr(row, "source_name", None) or "Desconhecido",
        "format": _format(row),
        "estimated_value": int(_safe_num(getattr(row, "estimated_value", None))),
        "checking_status": getattr(row, "checking_status", None),
        "market_status": getattr(row, "market_status", None),
        "news_status": getattr(row, "news_status", None),
        "content_type": getattr(row, "content_type", None),
        "publicity_score": int(_safe_num(getattr(row, "publicity_score", None))),
        "market_score": int(_safe_num(getattr(row, "market_score", None))),
        "news_score": int(_safe_num(getattr(row, "news_score", None))),
        "evidence_type": getattr(row, "evidence_type", None),
        "screenshot_banner_url": getattr(row, "screenshot_banner_url", None),
        "screenshot_page_url": getattr(row, "screenshot_page_url", None),
        "evidence_html_url": getattr(row, "evidence_html_url", None),
        "image_url": getattr(row, "image_url", None),
        "page_url": getattr(row, "page_url", None),
        "title": title,
    }


def build_complete_project_report_data(
    project_id: str,
    db: Session,
    date_from: str | None = None,
    date_to: str | None = None,
    analysis_mode: str | None = None,
) -> dict:
    project_uuid = _uuid(project_id, "project_id")
    project = db.query(Project).filter(Project.id == project_uuid).first()
    if not project:
        # Compatibilidade com bases antigas: se houver banners para o project_id, gera relatório informativo.
        has_rows = db.query(BannerItem.id).filter(BannerItem.project_id == project_uuid).first()
        if not has_rows:
            raise HTTPException(status_code=404, detail="Projeto não encontrado.")
        project = Project(id=project_uuid, name=f"Projeto {str(project_uuid)[:8]}", client_name=None, segment_id=None, description=None)

    parsed_from = _parse_dt(date_from)
    parsed_to = _parse_dt(date_to)
    mode = _normalize_analysis_mode(analysis_mode)

    query = db.query(BannerItem).filter(BannerItem.project_id == project_uuid)
    if parsed_from:
        query = query.filter(BannerItem.created_at >= parsed_from)
    if parsed_to:
        query = query.filter(BannerItem.created_at <= parsed_to)
    rows = query.order_by(BannerItem.created_at.desc()).all()

    linked_portals = _load_linked_portals(db, project_uuid)
    linked_advertisers = _load_linked_advertisers(db, project_uuid)
    editorial = _load_editorial_data(db, project_uuid, parsed_from, parsed_to)
    roles_by_id = {item["id"]: item.get("role") for item in linked_advertisers}

    market_rows: list[tuple[BannerItem, dict | None]] = []
    advertiser_stats = defaultdict(lambda: {
        "name": "Não identificado",
        "role": "não vinculado",
        "items": 0,
        "auditables": 0,
        "investment": 0,
        "portals": set(),
    })
    portal_stats = defaultdict(lambda: {"items": 0, "auditables": 0, "investment": 0})
    auditables = []
    news_candidates = []

    for row in rows:
        match = resolve_advertiser_for_item(db, row)
        adv_name = (match or {}).get("advertiser_registry_name") or getattr(row, "advertiser_name", None) or "Não identificado"
        adv_id = (match or {}).get("advertiser_registry_id") or adv_name
        role = roles_by_id.get(str(adv_id), "não vinculado")
        portal = getattr(row, "source_name", None) or "Desconhecido"
        value = int(_safe_num(getattr(row, "estimated_value", None)))

        if _row_matches_analysis_mode(row, mode):
            market_rows.append((row, match))
            stat = advertiser_stats[adv_id]
            stat["name"] = adv_name
            stat["role"] = role
            stat["items"] += 1
            stat["investment"] += value
            stat["portals"].add(portal)
            if getattr(row, "checking_status", None) == "auditavel":
                stat["auditables"] += 1

            portal_stats[portal]["items"] += 1
            portal_stats[portal]["investment"] += value
            if getattr(row, "checking_status", None) == "auditavel":
                portal_stats[portal]["auditables"] += 1

        if getattr(row, "checking_status", None) == "auditavel":
            auditables.append(_evidence_payload(row, adv_name))

        if getattr(row, "news_status", None) == "candidato":
            news_candidates.append(_evidence_payload(row, adv_name))

    total_investment = sum(stat["investment"] for stat in advertiser_stats.values())
    top_advertisers = []
    for stat in advertiser_stats.values():
        top_advertisers.append({
            "name": stat["name"],
            "role": stat["role"],
            "items": stat["items"],
            "auditables": stat["auditables"],
            "investment": stat["investment"],
            "investment_label": _brl(stat["investment"]),
            "share": round((stat["investment"] / total_investment) * 100, 2) if total_investment else 0,
            "portals": len(stat["portals"]),
        })
    top_advertisers.sort(key=lambda item: (item["investment"], item["items"], item["auditables"]), reverse=True)
    identification_quality = split_share_of_voice(top_advertisers, total_items=len(market_rows), total_investment=total_investment)
    top_advertisers_identified = identification_quality.get("identified", [])

    top_portals = []
    for portal, stat in portal_stats.items():
        top_portals.append({
            "portal": portal,
            "items": stat["items"],
            "auditables": stat["auditables"],
            "investment": stat["investment"],
            "investment_label": _brl(stat["investment"]),
            "share": round((stat["investment"] / total_investment) * 100, 2) if total_investment else 0,
        })
    top_portals.sort(key=lambda item: (item["investment"], item["items"]), reverse=True)

    total_detected = len(rows)
    auditables_count = sum(1 for row in rows if getattr(row, "checking_status", None) == "auditavel")
    review_count = sum(1 for row in rows if getattr(row, "checking_status", None) in {"parcial", "revisao"})
    rejected_count = sum(1 for row in rows if getattr(row, "checking_status", None) == "rejeitado")
    news_count = sum(1 for row in rows if getattr(row, "news_status", None) == "candidato")
    preserved_count = sum(1 for row in rows if getattr(row, "has_preserved_evidence", None))

    quality = _mode_payload(mode, total_detected, len(market_rows), auditables_count, news_count)
    if editorial.get("total_items"):
        quality.setdefault("warnings", [])

    insights = []
    insights.append(f"Modo de análise aplicado: {quality['label']}.")
    for warning in quality["warnings"][:2]:
        insights.append(warning)
    insights.extend(identification_alerts(identification_quality)[:2])
    if top_advertisers_identified:
        leader = top_advertisers_identified[0]
        if quality["is_referential"]:
            insights.append(
                f"{leader['name']} lidera a leitura referencial entre anunciantes identificados com {leader['share']}% do investimento estimado, "
                "sem evidência auditável para checking no recorte."
            )
        elif mode == "checking_auditable":
            insights.append(f"{leader['name']} lidera o recorte de checking auditável com {leader['auditables']} evidência(s) preservada(s).")
        else:
            insights.append(f"{leader['name']} lidera a inteligência de mercado entre anunciantes identificados com {leader['share']}% do investimento estimado.")
        if leader.get("auditables", 0):
            insights.append(f"{leader['name']} possui {leader['auditables']} evidência(s) auditável(is) para checking.")
    elif top_advertisers:
        insights.append("Há inventário de mercado, mas nenhum anunciante identificado com segurança; revisar aliases, OCR e evidências antes de leitura competitiva.")
    if linked_portals:
        insights.append(f"O projeto possui {len(linked_portals)} portal(is) vinculado(s) para varredura operacional.")
    if auditables_count:
        insights.append(f"Foram encontradas {auditables_count} evidência(s) auditável(is), com prova preservada para conferência.")
    if news_count and not quality["is_referential"]:
        insights.append(f"Há {news_count} item(ns) editorial(is) candidato(s) ao futuro módulo de monitoramento de notícias.")
    if editorial.get("total_items"):
        insights.append(
            f"O módulo editorial registrou {editorial.get('total_items', 0)} matéria(s), "
            f"com {editorial.get('matched_items', 0)} menção(ões) a termos/marcas monitorados."
        )
        if editorial.get("top_topics"):
            insights.append(f"Tema editorial mais recorrente: {editorial['top_topics'][0]['topic']}.")
    if not market_rows:
        if mode == "checking_auditable":
            insights.append("Nenhuma evidência auditável foi encontrada no recorte; o relatório não deve ser usado como checking comprovado.")
        else:
            insights.append("Nenhum item de inteligência de mercado foi encontrado no recorte; execute a varredura dos portais cadastrados ou ajuste os aliases dos anunciantes.")

    return {
        "project": _project_payload(db, project),
        "filters": {"date_from": date_from, "date_to": date_to, "analysis_mode": mode},
        "data_quality": quality,
        "linked_portals": linked_portals,
        "competitors": linked_advertisers,
        "totals": {
            "detected": total_detected,
            "market_items": len(market_rows),
            "auditables": auditables_count,
            "checking_review": review_count,
            "checking_rejected": rejected_count,
            "news_candidates": news_count,
            "preserved_evidence": preserved_count,
            "investment": total_investment,
            "linked_portals": len(linked_portals),
            "linked_advertisers": len(linked_advertisers),
            "editorial_items": editorial.get("total_items", 0),
            "editorial_matched_items": editorial.get("matched_items", 0),
            "editorial_sources": editorial.get("sources_count", 0),
            "editorial_topics": editorial.get("topics_count", 0),
        },
        "editorial": editorial,
        "top_advertisers": top_advertisers_identified,
        "top_advertisers_all": top_advertisers,
        "identification_quality": identification_quality,
        "top_portals": top_portals,
        "auditables": auditables[:50],
        "news_candidates": news_candidates[:50],
        "insights": insights,
    }


@router.get("/summary/{project_id}")
def project_report_summary(
    project_id: str,
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    analysis_mode: str | None = Query(default="market_wide"),
    db: Session = Depends(get_db),
):
    return build_complete_project_report_data(project_id, db, date_from=date_from, date_to=date_to, analysis_mode=analysis_mode)


@router.get("/pdf/{project_id}")
def project_report_pdf(
    project_id: str,
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    analysis_mode: str | None = Query(default="market_wide"),
    db: Session = Depends(get_db),
):
    data = build_complete_project_report_data(project_id, db, date_from=date_from, date_to=date_to, analysis_mode=analysis_mode)
    return build_project_pdf_response(data)


@router.get("/pptx/{project_id}")
def project_report_pptx(
    project_id: str,
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    analysis_mode: str | None = Query(default="market_wide"),
    db: Session = Depends(get_db),
):
    data = build_complete_project_report_data(project_id, db, date_from=date_from, date_to=date_to, analysis_mode=analysis_mode)
    return build_project_pptx_response(data)
