from collections import defaultdict
import tempfile

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.services.ppt_generator import generate_ppt_report
from app.db.models import BannerItem
from app.db.session import get_db
from app.services.report_generator import generate_intel_pdf


from app.services.alert_engine import generate_comparative_alerts
from app.services.snapshot_service import (
    get_previous_market_snapshot, 
    save_market_snapshot, 
    get_market_timeline,
)

from app.services.timeline_analyzer import analyze_timeline
from app.services.segment_classifier import classify_segment
from app.services.competitive_map import (
    build_competitive_map,
    build_portal_pressure_map,
    build_rival_summary,
)

from app.services.market_analyzer import generate_market_insights
from app.services.trend_analyzer import analyze_market_trends
from app.services.content_classifier import classify_detected_item
from app.services.registry_matcher import resolve_advertiser_for_item
from app.services.identification_quality import is_unknown_advertiser, display_advertiser_name, split_share_of_voice, identification_alerts

router = APIRouter(prefix="/intel", tags=["Intel"])


def _normalize_confidence(value: str | None) -> str:
    raw = (value or "").strip().lower()

    mapping = {
        "alta": "alta",
        "high": "alta",
        "media": "media",
        "média": "media",
        "medium": "media",
        "baixa": "baixa",
        "low": "baixa",
    }

    return mapping.get(raw, "baixa")


def detect_confidence_and_evidence(item: BannerItem) -> tuple[str, str | None]:
    confidence = None

    for attr in (
        "detection_confidence",
        "confidence",
        "identification_confidence",
        "match_confidence",
        "recognition_confidence",
        "quality",
    ):
        value = getattr(item, attr, None)
        if isinstance(value, str) and value.strip():
            confidence = value
            break

    if not confidence:
        score = getattr(item, "classification_score", None)

        try:
            score_num = float(score) if score is not None else None
        except (TypeError, ValueError):
            score_num = None

        if score_num is not None:
            if score_num >= 75:
                confidence = "alta"
            elif score_num >= 55:
                confidence = "media"
            else:
                confidence = "baixa"
        else:
            advertiser = (getattr(item, "advertiser_name", None) or "").strip().lower()
            if advertiser and advertiser not in {"nao identificado", "não identificado"}:
                confidence = "media"
            else:
                confidence = "baixa"

    evidence = None
    for attr in (
        "screenshot_banner_url",
        "screenshot_page_url",
        "evidence_html_url",
        "evidence_url",
        "screenshot_url",
        "image_url",
        "preview_url",
        "source_url",
        "url",
        "link",
        "page_url",
    ):
        value = getattr(item, attr, None)
        if isinstance(value, str) and value.strip():
            evidence = value
            break

    return _normalize_confidence(confidence), evidence


def _brl(value: int | float) -> str:
    return f"R$ {float(value or 0):,.0f}".replace(",", ".")


def _safe_num(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _classification_payload(item: BannerItem) -> dict:
    data = {
        "page_url": getattr(item, "page_url", None),
        "image_url": getattr(item, "image_url", None),
        "alt_text": getattr(item, "alt_text", None),
        "ocr_text": getattr(item, "ocr_text", None),
        "width": getattr(item, "width", None),
        "height": getattr(item, "height", None),
        "normalized_width": getattr(item, "normalized_width", None),
        "normalized_height": getattr(item, "normalized_height", None),
        "source_name": getattr(item, "source_name", None),
        "advertiser_name": getattr(item, "advertiser_name", None),
        "classification_reason": getattr(item, "classification_reason", None),
        "screenshot_banner_url": getattr(item, "screenshot_banner_url", None),
        "screenshot_page_url": getattr(item, "screenshot_page_url", None),
        "evidence_html_url": getattr(item, "evidence_html_url", None),
    }

    classified = classify_detected_item(data)

    # Preferir campos salvos quando já existirem; completar com fallback para registros antigos.
    for key in (
        "content_type",
        "checking_status",
        "market_status",
        "news_status",
        "publicity_score",
        "news_score",
        "market_score",
        "has_preserved_evidence",
        "evidence_type",
    ):
        stored = getattr(item, key, None)
        if stored is not None:
            classified[key] = stored

    return classified


def _visibility_score(item: BannerItem) -> float:
    stored_score = getattr(item, "visibility_score", None)
    if stored_score is not None:
        try:
            return round(float(stored_score), 2)
        except (TypeError, ValueError):
            pass

    width = _safe_num(getattr(item, "normalized_width", None) or getattr(item, "width", None))
    height = _safe_num(getattr(item, "normalized_height", None) or getattr(item, "height", None))
    value = _safe_num(getattr(item, "estimated_value", None))
    confidence, _ = detect_confidence_and_evidence(item)

    area_score = (width * height) / 10000 if width > 0 and height > 0 else 0

    confidence_factor = {
        "alta": 1.15,
        "media": 1.0,
        "baixa": 0.85,
    }.get(confidence, 1.0)

    value_factor = 1 + min(value / 1000, 1.5)

    score = area_score * confidence_factor * value_factor
    return round(score, 2)


def _advanced_alerts(
    total_banners: int,
    share_of_voice: list[dict],
    portal_ranking: list[dict],
    confidence_summary: list[dict],
) -> list[str]:
    alerts: list[str] = []

    if share_of_voice:
        identified_share = [item for item in share_of_voice if not is_unknown_advertiser(item.get("advertiser"))]
        top_adv = identified_share[0] if identified_share else share_of_voice[0]
        if top_adv.get("share_percent", 0) >= 50 and not is_unknown_advertiser(top_adv.get("advertiser")):
            alerts.append(
                f"Alta dominância de anunciante identificado: {top_adv.get('advertiser', 'Sem dados')} concentra {top_adv.get('share_percent', 0)}% do share."
            )

    if portal_ranking:
        top_portal = portal_ranking[0]
        if top_portal.get("share_percent", 0) >= 25:
            alerts.append(
                f"Concentração relevante em portal: {top_portal.get('portal', 'Nao informado')} responde por {top_portal.get('share_percent', 0)}% do investimento."
            )

    confidence_map = {item["confidence"]: item for item in confidence_summary}
    baixa = confidence_map.get("baixa", {"banners": 0})
    if total_banners > 0:
        baixa_pct = round((baixa.get("banners", 0) / total_banners) * 100, 2)
        if baixa_pct >= 20:
            alerts.append(
                f"Volume expressivo de baixa confiança: {baixa_pct}% das peças exigem revisão prioritária."
            )

    id_quality = split_share_of_voice(share_of_voice, total_items=total_banners)
    alerts.extend(identification_alerts(id_quality))

    return alerts


def _dominance_score(share_percent: float, investment: float, avg_visibility: float) -> float:
    score = (share_percent * 0.5) + (min(investment / 1000, 100) * 0.2) + (avg_visibility * 0.3)
    return round(score, 2)




def _is_market_sql_clause(alias: str = "b") -> str:
    return f"""
        (
            COALESCE({alias}.market_status, '') = 'incluido'
            OR (
                {alias}.market_status IS NULL
                AND lower(COALESCE({alias}.classification, '')) NOT IN (
                    'editorial','noticia','notícia','materia','matéria',
                    'conteudo editorial','conteúdo editorial','jornalismo','post editorial'
                )
            )
        )
    """


def _fast_market_summary(
    project_id: str,
    db: Session,
    segment_id: str | None = None,
    advertiser_id: str | None = None,
) -> dict:
    """Resumo Intel otimizado por SQL agregada.

    Evita carregar milhares de BannerItem em memória e evita resolver aliases item a item.
    O endpoint antigo fazia N+1 em aliases e ainda salvava snapshot a cada acesso; em bases
    maiores isso podia deixar /intel/summary sem resposta. Esta versão prioriza o painel
    executivo e os relatórios, mantendo os campos esperados pelo frontend.
    """
    from sqlalchemy import text

    market_clause = _is_market_sql_clause("b")
    params = {"project_id": project_id}
    extra_where = ""
    join_adv = "LEFT JOIN advertisers adv ON b.qualified_advertiser_id = adv.id"

    if advertiser_id:
        extra_where += " AND b.qualified_advertiser_id = CAST(:advertiser_id AS UUID)"
        params["advertiser_id"] = advertiser_id

    if segment_id:
        extra_where += " AND adv.segment_id = CAST(:segment_id AS UUID)"
        params["segment_id"] = segment_id

    counts = db.execute(text(f"""
        SELECT
            COUNT(*)::int AS total_detected_items,
            COUNT(*) FILTER (WHERE {market_clause})::int AS total_market_items,
            COALESCE(SUM(COALESCE(b.estimated_value,0)) FILTER (WHERE {market_clause}),0)::bigint AS total_investment,
            COUNT(*) FILTER (WHERE b.checking_status = 'auditavel')::int AS auditavel,
            COUNT(*) FILTER (WHERE b.checking_status = 'parcial')::int AS parcial,
            COUNT(*) FILTER (WHERE b.checking_status = 'revisao')::int AS revisao,
            COUNT(*) FILTER (WHERE b.checking_status = 'rejeitado')::int AS rejeitado,
            COUNT(*) FILTER (WHERE b.market_status = 'incluido')::int AS market_included,
            COUNT(*) FILTER (WHERE b.news_status = 'candidato')::int AS news_candidates,
            COUNT(*) FILTER (WHERE COALESCE(b.has_preserved_evidence,false) = true)::int AS preserved_evidence
        FROM banner_items b
        {join_adv}
        WHERE b.project_id = CAST(:project_id AS UUID)
        {extra_where}
    """), params).mappings().first() or {}

    total_detected_items = int(counts.get("total_detected_items") or 0)
    total_market_items = int(counts.get("total_market_items") or 0)
    total_banners = total_market_items
    total_investment = int(counts.get("total_investment") or 0)

    evidence_summary = {
        "auditavel": int(counts.get("auditavel") or 0),
        "parcial": int(counts.get("parcial") or 0),
        "revisao": int(counts.get("revisao") or 0),
        "rejeitado": int(counts.get("rejeitado") or 0),
        "market_included": int(counts.get("market_included") or 0),
        "news_candidates": int(counts.get("news_candidates") or 0),
        "preserved_evidence": int(counts.get("preserved_evidence") or 0),
    }

    adv_rows = db.execute(text(f"""
        SELECT
            COALESCE(NULLIF(TRIM(adv.name), ''), NULLIF(TRIM(b.advertiser_name), ''), 'Nao identificado') AS advertiser,
            COUNT(*)::int AS banners,
            COALESCE(SUM(COALESCE(b.estimated_value,0)),0)::bigint AS investment,
            AVG(COALESCE(b.visibility_score, ((COALESCE(b.normalized_width,b.width,0) * COALESCE(b.normalized_height,b.height,0)) / 10000.0), 0)) AS avg_visibility_score,
            AVG(CASE
                WHEN COALESCE(b.classification_score, 0) >= 75 THEN 3
                WHEN COALESCE(b.classification_score, 0) >= 55 THEN 2
                ELSE 1
            END) AS avg_confidence_points
        FROM banner_items b
        {join_adv}
        WHERE b.project_id = CAST(:project_id AS UUID)
          AND {market_clause}
          {extra_where}
        GROUP BY 1
        ORDER BY investment DESC, banners DESC
        LIMIT 80
    """), params).mappings().all()

    share_of_voice = []
    for r in adv_rows:
        banners = int(r.get("banners") or 0)
        investment = int(r.get("investment") or 0)
        percent = round((banners / total_banners) * 100, 2) if total_banners else 0
        avg_points = float(r.get("avg_confidence_points") or 1)
        confidence = "alta" if avg_points >= 2.5 else "media" if avg_points >= 1.5 else "baixa"
        avg_visibility = round(float(r.get("avg_visibility_score") or 0), 2)
        share_of_voice.append({
            "advertiser": display_advertiser_name(r.get("advertiser") or "Nao identificado"),
            "banners": banners,
            "share_percent": percent,
            "investment": investment,
            "confidence": confidence,
            "avg_visibility_score": avg_visibility,
            "dominance_score": _dominance_score(percent, investment, avg_visibility),
        })

    share_of_voice.sort(key=lambda x: (x["investment"], x["banners"]), reverse=True)
    identification_quality = split_share_of_voice(
        share_of_voice,
        total_items=total_banners,
        total_investment=total_investment,
    )
    share_of_voice_identified = identification_quality.get("identified", [])

    portal_rows = db.execute(text(f"""
        SELECT
            COALESCE(NULLIF(TRIM(b.source_name), ''), 'Desconhecido') AS portal,
            COUNT(*)::int AS banners,
            COALESCE(SUM(COALESCE(b.estimated_value,0)),0)::bigint AS investment,
            AVG(COALESCE(b.visibility_score, ((COALESCE(b.normalized_width,b.width,0) * COALESCE(b.normalized_height,b.height,0)) / 10000.0), 0)) AS avg_visibility_score
        FROM banner_items b
        {join_adv}
        WHERE b.project_id = CAST(:project_id AS UUID)
          AND {market_clause}
          {extra_where}
        GROUP BY 1
        ORDER BY investment DESC, banners DESC
        LIMIT 40
    """), params).mappings().all()

    portal_ranking = []
    for r in portal_rows:
        investment = int(r.get("investment") or 0)
        portal_ranking.append({
            "portal": r.get("portal") or "Desconhecido",
            "banners": int(r.get("banners") or 0),
            "investment": investment,
            "share_percent": round((investment / total_investment) * 100, 2) if total_investment else 0,
            "avg_visibility_score": round(float(r.get("avg_visibility_score") or 0), 2),
        })

    conf_rows = db.execute(text(f"""
        SELECT
            CASE
                WHEN COALESCE(b.classification_score, 0) >= 75 THEN 'alta'
                WHEN COALESCE(b.classification_score, 0) >= 55 THEN 'media'
                ELSE 'baixa'
            END AS confidence,
            COUNT(*)::int AS banners,
            COALESCE(SUM(COALESCE(b.estimated_value,0)),0)::bigint AS investment
        FROM banner_items b
        {join_adv}
        WHERE b.project_id = CAST(:project_id AS UUID)
          AND {market_clause}
          {extra_where}
        GROUP BY 1
    """), params).mappings().all()
    conf_map = {r["confidence"]: r for r in conf_rows}
    confidence_summary = [
        {"confidence": level, "banners": int((conf_map.get(level) or {}).get("banners") or 0), "investment": int((conf_map.get(level) or {}).get("investment") or 0)}
        for level in ["alta", "media", "baixa"]
    ]

    segment_totals = {}
    for item in share_of_voice_identified:
        segment = classify_segment(item.get("advertiser"))
        segment_totals.setdefault(segment, {"segment": segment, "investment": 0, "banners": 0})
        segment_totals[segment]["investment"] += item.get("investment", 0)
        segment_totals[segment]["banners"] += item.get("banners", 0)
    total_segment_investment = sum(v["investment"] for v in segment_totals.values()) or 1
    segment_ranking = sorted([
        {
            **seg,
            "share_percent": round((seg["investment"] / total_segment_investment) * 100, 2),
        }
        for seg in segment_totals.values()
    ], key=lambda x: x["investment"], reverse=True)

    top_items = db.execute(text(f"""
        SELECT
            b.id,
            COALESCE(NULLIF(TRIM(adv.name), ''), NULLIF(TRIM(b.advertiser_name), ''), 'Nao identificado') AS advertiser,
            COALESCE(NULLIF(TRIM(b.source_name), ''), 'Desconhecido') AS portal,
            COALESCE(b.estimated_value,0)::bigint AS investment,
            COALESCE(b.visibility_score, ((COALESCE(b.normalized_width,b.width,0) * COALESCE(b.normalized_height,b.height,0)) / 10000.0), 0) AS visibility_score
        FROM banner_items b
        {join_adv}
        WHERE b.project_id = CAST(:project_id AS UUID)
          AND {market_clause}
          {extra_where}
        ORDER BY visibility_score DESC NULLS LAST, investment DESC
        LIMIT 10
    """), params).mappings().all()
    top_visibility_items = [
        {
            "id": str(r.get("id") or ""),
            "advertiser": display_advertiser_name(r.get("advertiser") or "Nao identificado"),
            "portal": r.get("portal") or "Desconhecido",
            "investment": int(r.get("investment") or 0),
            "visibility_score": round(float(r.get("visibility_score") or 0), 2),
        }
        for r in top_items
    ]

    strategic_alerts = _advanced_alerts(
        total_banners=total_banners,
        share_of_voice=share_of_voice,
        portal_ranking=portal_ranking,
        confidence_summary=confidence_summary,
    )

    advertisers_for_analysis = [
        {"name": a["advertiser"], "share": (a.get("share_percent", 0) or 0) / 100.0}
        for a in share_of_voice_identified
    ]
    portal_pressure_map = [
        {
            "portal": p["portal"],
            "advertisers": 0,
            "banners": p["banners"],
            "investment": p["investment"],
            "pressure_label": "Alta" if p.get("share_percent", 0) >= 20 else "Média",
            "pressure_score": round(float(p.get("share_percent", 0)), 2),
        }
        for p in portal_ranking
    ]
    market_analysis = generate_market_insights({
        "advertisers": advertisers_for_analysis,
        "segments": segment_ranking,
        "competitive_map": [],
        "portal_pressure_map": portal_pressure_map,
        "rival_summary": {},
        "banner_items": [],
    })

    timeline_points = get_market_timeline(db, project_id, limit=30).get("points", [])
    analysis = {"24h": {}, "7d": {}, "30d": {}}

    return {
        "project_id": project_id,
        "filters": {"segment_id": segment_id, "advertiser_id": advertiser_id},
        "fast_mode": True,
        "total_banners": total_banners,
        "total_detected_items": total_detected_items,
        "total_market_items": total_market_items,
        "total_checking_ready": evidence_summary.get("auditavel", 0),
        "total_checking_review": evidence_summary.get("parcial", 0) + evidence_summary.get("revisao", 0),
        "total_checking_rejected": evidence_summary.get("rejeitado", 0),
        "total_news_candidates": evidence_summary.get("news_candidates", 0),
        "total_preserved_evidence": evidence_summary.get("preserved_evidence", 0),
        "total_investment": total_investment,
        "share_of_voice": share_of_voice,
        "share_of_voice_identified": share_of_voice_identified,
        "identification_quality": identification_quality,
        "portal_ranking": portal_ranking,
        "confidence_summary": confidence_summary,
        "evidence_summary": evidence_summary,
        "strategic_alerts": strategic_alerts,
        "top_visibility_items": top_visibility_items,
        "market_analysis": market_analysis,
        "segment_ranking": segment_ranking,
        "competitive_map": [],
        "portal_pressure_map": portal_pressure_map,
        "rival_summary": {},
        "temporal_analysis": analysis,
        "comparative_alerts": [],
        "timeline": timeline_points,
    }

@router.get("/summary/{project_id}")
def get_market_summary(
    project_id: str,
    db: Session = Depends(get_db),
    segment_id: str | None = Query(default=None),
    advertiser_id: str | None = Query(default=None),
):
    # V42.3: resposta otimizada. O cálculo antigo permanece abaixo no arquivo apenas
    # como referência histórica, mas não é executado. Isso elimina travamentos do
    # painel Intel em bases maiores após a ativação das permissões finas.
    return _fast_market_summary(project_id, db, segment_id=segment_id, advertiser_id=advertiser_id)

    all_rows = db.query(BannerItem).filter(BannerItem.project_id == project_id).all()

    if segment_id or advertiser_id:
        filtered_by_registry = []
        for row in all_rows:
            match = resolve_advertiser_for_item(db, row)
            if advertiser_id and (not match or match.get("advertiser_registry_id") != advertiser_id):
                continue
            if segment_id and (not match or match.get("segment_id") != segment_id):
                continue
            filtered_by_registry.append(row)
        all_rows = filtered_by_registry

    editorial_labels = {
        "editorial",
        "noticia",
        "notícia",
        "materia",
        "matéria",
        "conteudo editorial",
        "conteúdo editorial",
        "jornalismo",
        "post editorial",
    }

    evidence_summary = {
        "auditavel": 0,
        "parcial": 0,
        "revisao": 0,
        "rejeitado": 0,
        "market_included": 0,
        "news_candidates": 0,
        "preserved_evidence": 0,
    }

    banners = []
    for item in all_rows:
        payload = _classification_payload(item)
        checking_status = payload.get("checking_status")
        market_status = payload.get("market_status")
        news_status = payload.get("news_status")

        if checking_status in evidence_summary:
            evidence_summary[checking_status] += 1
        if market_status == "incluido":
            evidence_summary["market_included"] += 1
        if news_status == "candidato":
            evidence_summary["news_candidates"] += 1
        if payload.get("has_preserved_evidence"):
            evidence_summary["preserved_evidence"] += 1

        classification_raw = (getattr(item, "classification", None) or "").strip().lower()

        # Inteligência de mercado usa tudo que tenha valor comercial/referencial.
        # Conteúdo editorial puro fica reservado ao módulo de notícias.
        if market_status == "incluido" or (market_status is None and classification_raw not in editorial_labels):
            banners.append(item)

    total_detected_items = len(all_rows)
    total_market_items = len(banners)
    total_banners = total_market_items

    advertiser_counts = defaultdict(int)
    advertiser_value = defaultdict(int)
    advertiser_confidence_points = defaultdict(int)
    advertiser_visibility_sum = defaultdict(float)

    portal_counts = defaultdict(int)
    portal_value = defaultdict(int)
    portal_visibility_sum = defaultdict(float)

    confidence_counts = defaultdict(int)
    confidence_value = defaultdict(int)

    confidence_weight = {
        "alta": 3,
        "media": 2,
        "baixa": 1,
    }

    for item in banners:
        registry_match = resolve_advertiser_for_item(db, item)
        advertiser = (registry_match or {}).get("advertiser_registry_name") or getattr(item, "advertiser_name", None) or "Nao identificado"
        portal = getattr(item, "source_name", None) or "Desconhecido"
        value = getattr(item, "estimated_value", None) or 0

        confidence, _evidence = detect_confidence_and_evidence(item)
        visibility = _visibility_score(item)

        advertiser_counts[advertiser] += 1
        advertiser_value[advertiser] += value
        advertiser_confidence_points[advertiser] += confidence_weight.get(confidence, 1)
        advertiser_visibility_sum[advertiser] += visibility

        portal_counts[portal] += 1
        portal_value[portal] += value
        portal_visibility_sum[portal] += visibility

        confidence_counts[confidence] += 1
        confidence_value[confidence] += value


    share_of_voice = []
    for advertiser, count in advertiser_counts.items():
        percent = round((count / total_banners) * 100, 2) if total_banners else 0

        avg_points = advertiser_confidence_points[advertiser] / max(count, 1)
        if avg_points >= 2.5:
            advertiser_confidence = "alta"
        elif avg_points >= 1.5:
            advertiser_confidence = "media"
        else:
            advertiser_confidence = "baixa"

        avg_visibility = round(advertiser_visibility_sum[advertiser] / max(count, 1), 2)
        dominance_score = _dominance_score(
            share_percent=percent,
            investment=advertiser_value[advertiser],
            avg_visibility=avg_visibility,
        )

        share_of_voice.append(
            {
                "advertiser": advertiser,
                "banners": count,
                "share_percent": percent,
                "investment": advertiser_value[advertiser],
                "confidence": advertiser_confidence,
                "avg_visibility_score": avg_visibility,
                "dominance_score": dominance_score,
            }
        )

    share_of_voice.sort(key=lambda x: (x["share_percent"], x["investment"]), reverse=True)
    total_investment = sum(item["investment"] for item in share_of_voice)
    identification_quality = split_share_of_voice(share_of_voice, total_items=total_banners, total_investment=total_investment)
    share_of_voice_identified = identification_quality.get("identified", [])

    segment_totals = {}
    for item in share_of_voice_identified:
        segment = classify_segment(item.get("advertiser"))
        if segment not in segment_totals:
            segment_totals[segment] = {
                "segment": segment,
                "investment": 0,
                "banners": 0,
            }

        segment_totals[segment]["investment"] += item.get("investment", 0)
        segment_totals[segment]["banners"] += item.get("banners", 0)

    total_segment_investment = sum(v["investment"] for v in segment_totals.values()) or 1

    segment_ranking = []
    for seg in segment_totals.values():
        segment_ranking.append(
            {
                "segment": seg["segment"],
                "investment": seg["investment"],
                "banners": seg["banners"],
                "share_percent": round((seg["investment"] / total_segment_investment) * 100, 2),
            }
        )

    segment_ranking.sort(key=lambda x: x["investment"], reverse=True)

    portal_ranking = []
    for portal, count in portal_counts.items():
        investment = portal_value[portal]
        investment_share = round((investment / total_investment) * 100, 2) if total_investment else 0
        avg_visibility = round(portal_visibility_sum[portal] / max(count, 1), 2)

        portal_ranking.append(
            {
                "portal": portal,
                "banners": count,
                "investment": investment,
                "share_percent": investment_share,
                "avg_visibility_score": avg_visibility,
            }
        )

    portal_ranking.sort(key=lambda x: x["investment"], reverse=True)


    confidence_summary = [
        {
            "confidence": level,
            "banners": confidence_counts[level],
            "investment": confidence_value[level],
        }
        for level in ["alta", "media", "baixa"]
    ]

    strategic_alerts = _advanced_alerts(
        total_banners=total_banners,
        share_of_voice=share_of_voice,
        portal_ranking=portal_ranking,
        confidence_summary=confidence_summary,
    )

    top_visibility_items = sorted(
        [
            {
                "id": str(getattr(item, "id", "") or ""),
                "advertiser": display_advertiser_name(getattr(item, "advertiser_name", None) or "Nao identificado"),
                "portal": getattr(item, "source_name", None) or "Desconhecido",
                "investment": getattr(item, "estimated_value", None) or 0,
                "visibility_score": _visibility_score(item),
            }
            for item in banners
        ],
        key=lambda x: x["visibility_score"],
        reverse=True,
    )[:10]

    banner_items_data = [
        {
            "advertiser": (resolve_advertiser_for_item(db, item) or {}).get("advertiser_registry_name") or getattr(item, "advertiser_name", None) or "Nao identificado",
            "portal": getattr(item, "source_name", None) or "Desconhecido",
            "investment": getattr(item, "estimated_value", None) or 0,
        }
        for item in banners
    ]
    identified_banner_items_data = [item for item in banner_items_data if not is_unknown_advertiser(item.get("advertiser"))]

    competitive_map = build_competitive_map(
        portal_ranking_data=portal_ranking,
        banner_items_data=identified_banner_items_data,
    )

    portal_pressure_map = build_portal_pressure_map(banner_items_data)
    rival_summary = build_rival_summary(competitive_map)

    market_analysis = generate_market_insights(
        {
            "advertisers": [
                {
                    "name": a["advertiser"],
                    "share": a["share_percent"] / 100.0,
                }
                for a in share_of_voice_identified
            ],
            "segments": segment_ranking,
            "competitive_map": competitive_map,
            "portal_pressure_map": portal_pressure_map,
            "rival_summary": rival_summary,
            "banner_items": identified_banner_items_data,
        }
    )

    timeline_points = get_market_timeline(db, project_id, limit=200).get("points", [])

    now_point = timeline_points[-1] if timeline_points else {}
    analysis = {
        "24h": {},
        "7d": {},
        "30d": {},
    }

    def build_period_delta(points, days):
        if not points:
            return {}

        current = points[-1]

        if len(points) < 2:
            return {
                "has_data": False,
                "summary": "Histórico insuficiente."
            }

        previous = points[0]

        current_inv = current.get("total_investment", 0) or 0
        previous_inv = previous.get("total_investment", 0) or 0

        delta = current_inv - previous_inv
        pct = ((delta / previous_inv) * 100) if previous_inv else 0

        return {
            "has_data": True,
            "investment_delta": delta,
            "investment_pct": round(pct, 2),
            "leader_now": current.get("top_advertiser"),
            "leader_before": previous.get("top_advertiser"),
        }

    analysis["24h"] = build_period_delta(timeline_points, 1)
    analysis["7d"] = build_period_delta(timeline_points, 7)
    analysis["30d"] = build_period_delta(timeline_points, 30)

    response_data = {
        "project_id": project_id,
        "filters": {"segment_id": segment_id, "advertiser_id": advertiser_id},
        # Compatibilidade: total_banners segue representando o universo usado na inteligência de mercado.
        "total_banners": total_banners,
        "total_detected_items": total_detected_items,
        "total_market_items": total_market_items,
        "total_checking_ready": evidence_summary.get("auditavel", 0),
        "total_checking_review": evidence_summary.get("parcial", 0) + evidence_summary.get("revisao", 0),
        "total_checking_rejected": evidence_summary.get("rejeitado", 0),
        "total_news_candidates": evidence_summary.get("news_candidates", 0),
        "total_preserved_evidence": evidence_summary.get("preserved_evidence", 0),
        "total_investment": total_investment,
        "share_of_voice": share_of_voice,
        "share_of_voice_identified": share_of_voice_identified,
        "identification_quality": identification_quality,
        "portal_ranking": portal_ranking,
        "confidence_summary": confidence_summary,
        "evidence_summary": evidence_summary,
        "strategic_alerts": strategic_alerts,
        "top_visibility_items": top_visibility_items,
        "market_analysis": market_analysis,
        "segment_ranking": segment_ranking,
        "competitive_map": competitive_map,
        "portal_pressure_map": portal_pressure_map,
        "rival_summary": rival_summary,
        "temporal_analysis": analysis,
    }

    previous_snapshot = get_previous_market_snapshot(db, project_id)

    response_data["comparative_alerts"] = generate_comparative_alerts(
        response_data,
        previous_snapshot,
    )

    save_market_snapshot(db, project_id, response_data)

    return response_data

       
@router.get("/report/pdf/{project_id}")
def get_market_report_pdf(
    project_id: str,
    db: Session = Depends(get_db),
    segment_id: str | None = Query(default=None),
    advertiser_id: str | None = Query(default=None),
):
    summary = get_market_summary(project_id, db, segment_id=segment_id, advertiser_id=advertiser_id)

    competitive_map = summary.get("competitive_map", []) or []
    portal_pressure_map = summary.get("portal_pressure_map", []) or []
    rival_summary = summary.get("rival_summary", {}) or {}
    segment_ranking = summary.get("segment_ranking", []) or []
    market_analysis = summary.get("market_analysis", {}) or {}

    share_of_voice = summary.get("share_of_voice", []) or []
    share_of_voice_identified = summary.get("share_of_voice_identified", []) or []
    identification_quality = summary.get("identification_quality", {}) or {}
    portal_ranking = summary.get("portal_ranking", []) or []
    strategic_alerts = summary.get("strategic_alerts", []) or []
    confidence_summary = summary.get("confidence_summary", []) or []

    total_banners = summary.get("total_banners", 0) or 0
    total_investment = summary.get("total_investment", 0) or 0

    top_advertiser = share_of_voice_identified[0] if share_of_voice_identified else {}
    top_portal = portal_ranking[0] if portal_ranking else {}

    has_data = total_banners > 0 and (len(share_of_voice) > 0 or len(portal_ranking) > 0)


    insights = strategic_alerts[:] if strategic_alerts else []
    if not insights:
        if has_data:
            insights = [
                "O projeto apresenta dados suficientes para leitura executiva de presença publicitária."
            ]
        else:
            insights = [
                "Não há evidências publicitárias registradas para o projeto informado nesta base.",
                "O relatório foi gerado em modo informativo, sem ranking de anunciantes ou portais.",
                "Recomendação: validar a ingestão dos banners ou restaurar a base histórica antes da análise executiva.",
            ]

    top_advertisers = [
        {
            "name": item.get("advertiser", "Nao identificado"),
            "share": item.get("share_percent", 0),
            "value_fmt": _brl(item.get("investment", 0)),
            "banners": item.get("banners", 0),
            "confidence": item.get("confidence", "n/a"),
        }
        for item in share_of_voice_identified[:5]
    ]

    top_publishers = [
        {
            "name": item.get("portal", "Desconhecido"),
            "share": item.get("share_percent", 0),
            "value_fmt": _brl(item.get("investment", 0)),
            "banners": item.get("banners", 0),
        }
        for item in portal_ranking[:5]
    ]

    if not top_advertisers:
        top_advertisers = [
            {
                "name": "Sem anunciantes identificados",
                "share": 0,
                "value_fmt": _brl(0),
                "banners": 0,
                "confidence": "n/a",
            }
        ]

    if not top_publishers:
        top_publishers = [
            {
                "name": "Sem anunciantes identificados",
                "share": 0,
                "value_fmt": _brl(0),
                "banners": 0,
            }
        ]

    highest_confidence = next(
        (item for item in confidence_summary if item.get("confidence") == "alta"),
        {"confidence": "alta", "banners": 0, "investment": 0},
    )
    medium_confidence = next(
        (item for item in confidence_summary if item.get("confidence") == "media"),
        {"confidence": "media", "banners": 0, "investment": 0},
    )
    low_confidence = next(
        (item for item in confidence_summary if item.get("confidence") == "baixa"),
        {"confidence": "baixa", "banners": 0, "investment": 0},
    )

    data = {
        "project_id": project_id,
        "has_data": has_data,
        "insights": insights,
        "strategic_alerts": strategic_alerts,
        "market_analysis": market_analysis,
        "segment_ranking": segment_ranking,
        "competitive_map": competitive_map,
        "total_ads": total_banners,
        "total_detected_items": summary.get("total_detected_items", 0),
        "total_market_items": summary.get("total_market_items", 0),
        "total_checking_ready": summary.get("total_checking_ready", 0),
        "total_checking_review": summary.get("total_checking_review", 0),
        "total_checking_rejected": summary.get("total_checking_rejected", 0),
        "total_news_candidates": summary.get("total_news_candidates", 0),
        "total_preserved_evidence": summary.get("total_preserved_evidence", 0),
        "evidence_summary": summary.get("evidence_summary", {}) or {},
        "filters": summary.get("filters", {}) or {},
        "investment": _brl(total_investment),
        "advertisers": len(share_of_voice_identified),
        "identified_advertisers": len(share_of_voice_identified),
        "unknown_advertiser_items": identification_quality.get("unknown_items", 0),
        "unknown_advertiser_share": identification_quality.get("unknown_share_items", 0),
        "unknown_advertiser_investment": _brl(identification_quality.get("unknown_investment", 0)),
        "identified_items": identification_quality.get("identified_items", 0),
        "identified_share": identification_quality.get("identified_share_items", 0),
        "publishers": len(portal_ranking),
        "top_advertiser_name": top_advertiser.get("advertiser", "Sem dados"),
        "top_advertiser_share": top_advertiser.get("share_percent", 0),
        "top_advertiser_confidence": top_advertiser.get("confidence", "n/a"),
        "top_portal_name": top_portal.get("portal", "Sem dados"),
        "top_portal_value": _brl(top_portal.get("investment", 0)),
        "top_advertisers": top_advertisers,
        "top_publishers": top_publishers,
        "confidence_high_banners": highest_confidence.get("banners", 0),
        "confidence_high_value": _brl(highest_confidence.get("investment", 0)),
        "confidence_medium_banners": medium_confidence.get("banners", 0),
        "confidence_medium_value": _brl(medium_confidence.get("investment", 0)),
        "confidence_low_banners": low_confidence.get("banners", 0),
        "confidence_low_value": _brl(low_confidence.get("investment", 0)),
        "portal_pressure_map": portal_pressure_map,
        "rival_summary": rival_summary,
    }

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.close()

    generate_intel_pdf(data, tmp.name)

    return FileResponse(
        tmp.name,
        media_type="application/pdf",
        filename=f"intel_report_{project_id}.pdf",
    )

from app.services.ppt_generator import generate_ppt_report
from fastapi.responses import FileResponse
import tempfile

@router.get("/report/pptx/{project_id}")
def get_market_report_pptx(
    project_id: str,
    db: Session = Depends(get_db),
    segment_id: str | None = Query(default=None),
    advertiser_id: str | None = Query(default=None),
):
    summary = get_market_summary(project_id, db, segment_id=segment_id, advertiser_id=advertiser_id)

    timeline_data = get_market_timeline(db, project_id, limit=8)
    summary["timeline"] = timeline_data.get("points", [])
    summary["timeline_analysis"] = analyze_timeline(summary["timeline"])

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pptx")
    tmp.close()

    generate_ppt_report(summary, tmp.name)

    return FileResponse(
        tmp.name,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=f"intel_report_{project_id}.pptx",
    )

@router.get("/timeline/{project_id}")
def get_intel_timeline(project_id: str, db: Session = Depends(get_db)):
    timeline_data = get_market_timeline(db, project_id, limit=30)
    points = timeline_data.get("points", [])

    analysis = analyze_timeline(points)

    return {
        "project_id": project_id,
        "points": points,
        "analysis": analysis,
    }
    
@router.get("/trends/{project_id}")
def get_intel_trends(project_id: str, db: Session = Depends(get_db)):
    timeline_data = get_market_timeline(db, project_id, limit=30)
    points = timeline_data.get("points", [])

    return analyze_market_trends(points)
