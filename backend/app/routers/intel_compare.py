from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.models import Advertiser, AdvertiserAlias, BannerItem, Segment
from app.db.session import get_db
from app.services.registry_matcher import resolve_advertiser_for_item
from app.services.compare_report_generator import build_compare_pdf_response, build_compare_pptx_response

router = APIRouter(prefix="/intel/compare", tags=["Intel Comparativo"])


def _uuid(value: str | None, label: str = "id") -> UUID | None:
    if not value:
        return None
    try:
        return UUID(str(value))
    except Exception:
        raise HTTPException(status_code=400, detail=f"{label} inválido.")


def _parse_dt(value: str | None):
    if not value:
        return None
    try:
        normalized = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(normalized).replace(tzinfo=None)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Data inválida: {value}")


def _safe_num(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _banner_format(row: BannerItem) -> str:
    width = getattr(row, "width", None) or getattr(row, "normalized_width", None) or 0
    height = getattr(row, "height", None) or getattr(row, "normalized_height", None) or 0
    if not width or not height:
        return "Não identificado"
    return f"{width} x {height}"


def _advertiser_payload(db: Session, advertiser: Advertiser) -> dict:
    segment = db.query(Segment).filter(Segment.id == advertiser.segment_id).first() if advertiser.segment_id else None
    aliases = (
        db.query(AdvertiserAlias)
        .filter(AdvertiserAlias.advertiser_id == advertiser.id, AdvertiserAlias.active.is_(True))
        .order_by(AdvertiserAlias.alias.asc())
        .all()
    )
    return {
        "id": str(advertiser.id),
        "name": advertiser.name,
        "legal_name": advertiser.legal_name,
        "segment_id": str(advertiser.segment_id) if advertiser.segment_id else None,
        "segment_name": segment.name if segment else None,
        "advertiser_type": advertiser.advertiser_type,
        "aliases": [row.alias for row in aliases],
    }


def _empty_adv_stats(advertiser: dict) -> dict:
    return {
        "advertiser_id": advertiser.get("id"),
        "advertiser": advertiser.get("name"),
        "segment_id": advertiser.get("segment_id"),
        "segment_name": advertiser.get("segment_name"),
        "aliases": advertiser.get("aliases", []),
        "items": 0,
        "auditables": 0,
        "review_items": 0,
        "rejected_items": 0,
        "news_candidates": 0,
        "investment": 0,
        "share_count_percent": 0,
        "share_investment_percent": 0,
        "avg_publicity_score": 0,
        "avg_market_score": 0,
        "avg_visibility_score": 0,
        "portals": [],
        "formats": [],
        "latest_evidences": [],
        "daily_timeline": [],
        "strength_score": 0,
    }


def _visibility_score(row: BannerItem) -> float:
    stored = getattr(row, "visibility_score", None)
    if stored is not None:
        return _safe_num(stored)
    width = _safe_num(getattr(row, "normalized_width", None) or getattr(row, "width", None))
    height = _safe_num(getattr(row, "normalized_height", None) or getattr(row, "height", None))
    value = _safe_num(getattr(row, "estimated_value", None))
    area = (width * height) / 10000 if width and height else 0
    return round(area * (1 + min(value / 1000, 1.5)), 2)


def _evidence_payload(row: BannerItem) -> dict:
    return {
        "id": str(row.id),
        "advertiser_name": getattr(row, "advertiser_name", None),
        "source_name": getattr(row, "source_name", None) or "Desconhecido",
        "format": _banner_format(row),
        "estimated_value": int(_safe_num(getattr(row, "estimated_value", None))),
        "checking_status": getattr(row, "checking_status", None),
        "market_status": getattr(row, "market_status", None),
        "news_status": getattr(row, "news_status", None),
        "publicity_score": int(_safe_num(getattr(row, "publicity_score", None))),
        "market_score": int(_safe_num(getattr(row, "market_score", None))),
        "screenshot_banner_url": getattr(row, "screenshot_banner_url", None),
        "screenshot_page_url": getattr(row, "screenshot_page_url", None),
        "evidence_html_url": getattr(row, "evidence_html_url", None),
        "image_url": getattr(row, "image_url", None),
        "page_url": getattr(row, "page_url", None),
        "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else None,
    }


def _load_requested_advertisers(
    db: Session,
    segment_id: str | None,
    advertiser_ids: str | None,
    max_advertisers: int,
) -> list[dict]:
    ids = [item.strip() for item in str(advertiser_ids or "").split(",") if item.strip()]

    query = db.query(Advertiser).filter(Advertiser.active.is_(True))

    if ids:
        uuid_ids = [_uuid(item, "advertiser_id") for item in ids]
        query = query.filter(Advertiser.id.in_(uuid_ids))
    elif segment_id:
        query = query.filter(Advertiser.segment_id == _uuid(segment_id, "segment_id"))

    rows = query.order_by(Advertiser.name.asc()).limit(max_advertisers).all()
    return [_advertiser_payload(db, row) for row in rows]


def _build_pairwise(advertisers: list[dict], include_zero_pairs: bool = False) -> list[dict]:
    pairs = []
    for i, left in enumerate(advertisers):
        for right in advertisers[i + 1 :]:
            left_score = _safe_num(left.get("strength_score"))
            right_score = _safe_num(right.get("strength_score"))
            if not include_zero_pairs and left_score <= 0 and right_score <= 0:
                continue

            delta = abs(left_score - right_score)
            total = max(left_score + right_score, 1)
            balance = round(100 - (delta / total) * 100, 2)
            leader = left if left_score >= right_score else right
            if left_score <= 0 and right_score <= 0:
                relation = "sem dados"
            elif left_score <= 0 or right_score <= 0:
                # Apenas um anunciante possui dados no recorte. Isso não é uma disputa
                # competitiva comprovada; é presença unilateral no universo analisado.
                relation = "presença unilateral"
            else:
                relation = "equilibrado" if balance >= 85 else "vantagem competitiva" if balance >= 60 else "domínio competitivo"
            pairs.append(
                {
                    "left": left.get("advertiser"),
                    "right": right.get("advertiser"),
                    "leader": leader.get("advertiser"),
                    "balance_score": balance,
                    "relation": relation,
                    "left_strength": round(left_score, 2),
                    "right_strength": round(right_score, 2),
                    "investment_delta": int(_safe_num(left.get("investment")) - _safe_num(right.get("investment"))),
                    "items_delta": int(_safe_num(left.get("items")) - _safe_num(right.get("items"))),
                }
            )
    return sorted(pairs, key=lambda x: x["balance_score"], reverse=True)



def _row_has_preserved_evidence(row: BannerItem) -> bool:
    if bool(getattr(row, "has_preserved_evidence", False)):
        return True
    return bool(
        getattr(row, "screenshot_banner_url", None)
        or getattr(row, "screenshot_page_url", None)
        or getattr(row, "evidence_html_url", None)
    )


def _row_passes_evidence_scope(row: BannerItem, evidence_scope: str) -> bool:
    """Controla a qualidade do dado usado no comparativo.

    market: visão ampla de inteligência de mercado, incluindo evidências referenciais.
    preserved: somente itens com prova preservada (screenshot/html), ainda como mercado.
    auditavel: somente publicidade auditável para checking.
    advertising: somente itens classificados como publicidade, mesmo não auditáveis.
    """
    scope = (evidence_scope or "market").strip().lower()
    market_status = str(getattr(row, "market_status", "") or "").lower()
    checking_status = str(getattr(row, "checking_status", "") or "").lower()
    content_type = str(getattr(row, "content_type", "") or "").lower()

    if scope == "auditavel":
        return checking_status == "auditavel"

    if scope == "preserved":
        return market_status == "incluido" and _row_has_preserved_evidence(row)

    if scope == "advertising":
        return market_status == "incluido" and content_type == "advertising"

    return market_status == "incluido"

def _scope_label(evidence_scope: str | None) -> str:
    scope = (evidence_scope or "market").strip().lower()
    return {
        "market": "Mercado amplo",
        "preserved": "Somente com evidência preservada",
        "advertising": "Somente publicidade classificada",
        "auditavel": "Somente checking auditável",
    }.get(scope, "Mercado amplo")


def _quality_notice(totals: dict, evidence_scope: str | None) -> str | None:
    scope = (evidence_scope or "market").strip().lower()
    items = int(_safe_num(totals.get("items")))
    auditables = int(_safe_num(totals.get("auditables")))
    if items > 0 and auditables == 0 and scope != "auditavel":
        return (
            f"Leitura referencial: o recorte possui {items} evidência(s) de mercado, "
            "mas nenhuma evidência auditável para checking. Use o modo 'Somente checking auditável' "
            "para relatório de prova documental."
        )
    if scope == "auditavel" and items == 0:
        return "Nenhuma evidência auditável foi encontrada para checking no recorte selecionado."
    return None


def _build_insights(
    stats: list[dict],
    pairs: list[dict],
    segment_name: str | None,
    evidence_scope: str | None = "market",
    totals: dict | None = None,
) -> list[str]:
    totals = totals or {}
    scope = (evidence_scope or "market").strip().lower()
    scope_label = _scope_label(scope)
    notice = _quality_notice(totals, scope)

    if not stats:
        base = ["Nenhum anunciante com evidência foi encontrado para os filtros selecionados."]
        if notice:
            base.insert(0, notice)
        return base

    insights = []
    if notice:
        insights.append(notice)

    insights.append(f"Modo de análise aplicado: {scope_label}.")

    active_stats = [row for row in stats if _safe_num(row.get("items")) > 0]
    if not active_stats:
        insights.append("Os anunciantes selecionados estão cadastrados, mas não possuem evidências no recorte atual.")
        return insights

    leader = active_stats[0]
    context = f" no segmento {segment_name}" if segment_name else ""

    if scope == "auditavel":
        insights.append(
            f"{leader.get('advertiser')} lidera{context} no recorte de checking auditável com {leader.get('auditables', 0)} evidência(s) comprovada(s)."
        )
    elif int(_safe_num(totals.get("auditables"))) == 0:
        insights.append(
            f"{leader.get('advertiser')} lidera{context} na leitura referencial de mercado com {leader.get('share_investment_percent')}% do investimento estimado, sem evidência auditável no recorte."
        )
    else:
        insights.append(
            f"{leader.get('advertiser')} lidera{context} com {leader.get('share_investment_percent')}% do investimento estimado."
        )

    if leader.get("auditables", 0) > 0:
        insights.append(
            f"{leader.get('advertiser')} possui {leader.get('auditables')} evidência(s) auditável(is) para checking."
        )

    if len(active_stats) >= 2:
        runner = active_stats[1]
        gap = round(_safe_num(leader.get("share_investment_percent")) - _safe_num(runner.get("share_investment_percent")), 2)
        if gap <= 10:
            insights.append(
                f"Disputa equilibrada: diferença de {gap} p.p. entre {leader.get('advertiser')} e {runner.get('advertiser')}."
            )
        else:
            insights.append(
                f"{leader.get('advertiser')} abre vantagem de {gap} p.p. sobre {runner.get('advertiser')}."
            )
    elif len(stats) > 1:
        insights.append("Os demais anunciantes selecionados não apresentam evidências no recorte atual.")

    balanced_pairs = [row for row in pairs if _safe_num(row.get("balance_score")) >= 60]
    if balanced_pairs:
        pair = balanced_pairs[0]
        insights.append(
            f"O par mais equilibrado é {pair.get('left')} x {pair.get('right')}, com equilíbrio competitivo de {pair.get('balance_score')}."
        )
    elif pairs:
        unilateral_count = sum(1 for row in pairs if str(row.get("relation") or "") == "presença unilateral")
        if unilateral_count == len(pairs):
            insights.append("Não há confronto competitivo direto no recorte; os pares ativos indicam presença unilateral de um anunciante.")
        else:
            insights.append("Não há confronto equilibrado no recorte; os pares ativos indicam vantagem, domínio competitivo ou presença unilateral.")

    broad = [row for row in active_stats if len(row.get("portals", [])) >= 3]
    if broad:
        insights.append(
            f"{broad[0].get('advertiser')} apresenta maior capilaridade, com presença em {len(broad[0].get('portals', []))} portal(is)."
        )

    return insights


@router.get("/{project_id}")
def compare_advertisers(
    project_id: str,
    segment_id: str | None = Query(default=None, description="ID do segmento cadastrado"),
    advertiser_ids: str | None = Query(default=None, description="IDs de anunciantes separados por vírgula"),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    max_advertisers: int = Query(default=12, ge=2, le=30),
    evidence_scope: str = Query(default="market", description="market, preserved, auditavel ou advertising"),
    include_zero_pairs: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    project_uuid = _uuid(project_id, "project_id")
    selected_advertisers = _load_requested_advertisers(db, segment_id, advertiser_ids, max_advertisers)
    selected_ids = {row["id"] for row in selected_advertisers}

    query = db.query(BannerItem).filter(BannerItem.project_id == project_uuid)
    parsed_from = _parse_dt(date_from)
    parsed_to = _parse_dt(date_to)
    if parsed_from:
        query = query.filter(BannerItem.created_at >= parsed_from)
    if parsed_to:
        query = query.filter(BannerItem.created_at <= parsed_to)

    rows = query.order_by(BannerItem.created_at.desc()).all()

    # Quando nenhum anunciante específico é escolhido, descobrimos os principais pela base.
    discovered: dict[str, dict] = {row["id"]: row for row in selected_advertisers}
    row_matches: list[tuple[BannerItem, dict]] = []

    for row in rows:
        if not _row_passes_evidence_scope(row, evidence_scope):
            continue

        match = resolve_advertiser_for_item(db, row)
        if not match:
            continue

        if segment_id and match.get("segment_id") != segment_id:
            continue

        adv_id = match.get("advertiser_registry_id")
        if selected_ids and adv_id not in selected_ids:
            continue

        if adv_id not in discovered:
            advertiser = db.query(Advertiser).filter(Advertiser.id == _uuid(adv_id, "advertiser_id")).first()
            if advertiser:
                discovered[adv_id] = _advertiser_payload(db, advertiser)

        row_matches.append((row, match))

    if not selected_advertisers:
        # Seleciona automaticamente os principais anunciantes encontrados.
        counts = defaultdict(int)
        for _row, match in row_matches:
            counts[match.get("advertiser_registry_id")] += 1
        top_ids = [adv_id for adv_id, _count in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:max_advertisers]]
        selected_ids = set(top_ids)
    else:
        selected_ids = {row["id"] for row in selected_advertisers}

    stats = {adv_id: _empty_adv_stats(discovered[adv_id]) for adv_id in selected_ids if adv_id in discovered}

    portal_counter: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    format_counter: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    daily_counter: dict[str, dict[str, dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: {"items": 0, "investment": 0}))
    score_acc = defaultdict(lambda: {"publicity": 0.0, "market": 0.0, "visibility": 0.0})

    for row, match in row_matches:
        adv_id = match.get("advertiser_registry_id")
        if adv_id not in stats:
            continue

        item_value = int(_safe_num(getattr(row, "estimated_value", None)))
        stats[adv_id]["items"] += 1
        stats[adv_id]["investment"] += item_value

        checking = str(getattr(row, "checking_status", "") or "").lower()
        if checking == "auditavel":
            stats[adv_id]["auditables"] += 1
        elif checking in {"parcial", "revisao"}:
            stats[adv_id]["review_items"] += 1
        elif checking == "rejeitado":
            stats[adv_id]["rejected_items"] += 1

        if str(getattr(row, "news_status", "") or "").lower() == "candidato":
            stats[adv_id]["news_candidates"] += 1

        portal = getattr(row, "source_name", None) or "Desconhecido"
        fmt = _banner_format(row)
        portal_counter[adv_id][portal] += 1
        format_counter[adv_id][fmt] += 1

        day = row.created_at.date().isoformat() if getattr(row, "created_at", None) else "sem-data"
        daily_counter[adv_id][day]["items"] += 1
        daily_counter[adv_id][day]["investment"] += item_value

        score_acc[adv_id]["publicity"] += _safe_num(getattr(row, "publicity_score", None))
        score_acc[adv_id]["market"] += _safe_num(getattr(row, "market_score", None))
        score_acc[adv_id]["visibility"] += _visibility_score(row)

        if len(stats[adv_id]["latest_evidences"]) < 8:
            stats[adv_id]["latest_evidences"].append(_evidence_payload(row))

    total_items = sum(row["items"] for row in stats.values())
    total_investment = sum(row["investment"] for row in stats.values())

    for adv_id, item in stats.items():
        count = max(item["items"], 1)
        item["share_count_percent"] = round((item["items"] / total_items) * 100, 2) if total_items else 0
        item["share_investment_percent"] = round((item["investment"] / total_investment) * 100, 2) if total_investment else 0
        item["avg_publicity_score"] = round(score_acc[adv_id]["publicity"] / count, 2) if item["items"] else 0
        item["avg_market_score"] = round(score_acc[adv_id]["market"] / count, 2) if item["items"] else 0
        item["avg_visibility_score"] = round(score_acc[adv_id]["visibility"] / count, 2) if item["items"] else 0
        item["portals"] = [
            {"portal": portal, "items": qty}
            for portal, qty in sorted(portal_counter[adv_id].items(), key=lambda kv: kv[1], reverse=True)
        ]
        item["formats"] = [
            {"format": fmt, "items": qty}
            for fmt, qty in sorted(format_counter[adv_id].items(), key=lambda kv: kv[1], reverse=True)
        ]
        item["daily_timeline"] = [
            {"date": day, **payload}
            for day, payload in sorted(daily_counter[adv_id].items(), key=lambda kv: kv[0])
        ]
        item["strength_score"] = round(
            (item["share_investment_percent"] * 0.45)
            + (item["share_count_percent"] * 0.25)
            + (min(item["auditables"] * 8, 40) * 0.15)
            + (min(len(item["portals"]) * 10, 40) * 0.15),
            2,
        )

    advertisers = sorted(stats.values(), key=lambda x: (x["investment"], x["items"], x["auditables"]), reverse=True)
    pairs = _build_pairwise(advertisers, include_zero_pairs=include_zero_pairs)

    segment_name = None
    if segment_id:
        seg = db.query(Segment).filter(Segment.id == _uuid(segment_id, "segment_id")).first()
        segment_name = seg.name if seg else None

    portal_overlap = []
    if len(advertisers) >= 2:
        portal_sets = {a["advertiser"]: {p["portal"] for p in a.get("portals", [])} for a in advertisers}
        names = list(portal_sets.keys())
        for i, left in enumerate(names):
            for right in names[i + 1 :]:
                common = sorted(portal_sets[left].intersection(portal_sets[right]))
                if common:
                    portal_overlap.append({"left": left, "right": right, "common_portals": common, "count": len(common)})

    totals_payload = {
        "advertisers": len(advertisers),
        "items": total_items,
        "investment": total_investment,
        "auditables": sum(row["auditables"] for row in advertisers),
        "portals": len({p["portal"] for row in advertisers for p in row.get("portals", [])}),
        "zero_advertisers": len([row for row in advertisers if not row.get("items")]),
        "auditability_rate_percent": round((sum(row["auditables"] for row in advertisers) / total_items) * 100, 2) if total_items else 0,
    }
    quality_notice = _quality_notice(totals_payload, evidence_scope)

    return {
        "project_id": project_id,
        "filters": {
            "segment_id": segment_id,
            "segment_name": segment_name,
            "advertiser_ids": sorted(list(selected_ids)),
            "date_from": date_from,
            "date_to": date_to,
            "evidence_scope": evidence_scope,
            "evidence_scope_label": _scope_label(evidence_scope),
            "include_zero_pairs": include_zero_pairs,
        },
        "totals": totals_payload,
        "quality_notice": quality_notice,
        "advertisers": advertisers,
        "pairs": pairs,
        "portal_overlap": sorted(portal_overlap, key=lambda x: x["count"], reverse=True),
        "insights": _build_insights(advertisers, pairs, segment_name, evidence_scope, totals_payload),
    }

@router.get("/report/pdf/{project_id}")
def compare_report_pdf(
    project_id: str,
    segment_id: str | None = Query(default=None),
    advertiser_ids: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    max_advertisers: int = Query(default=12, ge=2, le=30),
    evidence_scope: str = Query(default="market", description="market, preserved, auditavel ou advertising"),
    include_zero_pairs: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    data = compare_advertisers(
        project_id=project_id,
        segment_id=segment_id,
        advertiser_ids=advertiser_ids,
        date_from=date_from,
        date_to=date_to,
        max_advertisers=max_advertisers,
        evidence_scope=evidence_scope,
        include_zero_pairs=include_zero_pairs,
        db=db,
    )
    return build_compare_pdf_response(data)


@router.get("/report/pptx/{project_id}")
def compare_report_pptx(
    project_id: str,
    segment_id: str | None = Query(default=None),
    advertiser_ids: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    max_advertisers: int = Query(default=12, ge=2, le=30),
    evidence_scope: str = Query(default="market", description="market, preserved, auditavel ou advertising"),
    include_zero_pairs: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    data = compare_advertisers(
        project_id=project_id,
        segment_id=segment_id,
        advertiser_ids=advertiser_ids,
        date_from=date_from,
        date_to=date_to,
        max_advertisers=max_advertisers,
        evidence_scope=evidence_scope,
        include_zero_pairs=include_zero_pairs,
        db=db,
    )
    return build_compare_pptx_response(data)

