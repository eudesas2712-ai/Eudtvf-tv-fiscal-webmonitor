from collections import defaultdict
import tempfile

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.services.ppt_generator import generate_ppt_report
from app.db.models import BannerItem
from app.db.session import get_db
from app.services.report_generator import generate_intel_pdf

from app.services.market_analyzer import generate_market_insights
from app.services.segment_classifier import classify_segment
from app.services.competitive_map import (
    build_competitive_map,
    build_portal_pressure_map,
    build_rival_summary,
)


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
            if score_num >= 12:
                confidence = "alta"
            elif score_num >= 8:
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
        top_adv = share_of_voice[0]
        if top_adv.get("share_percent", 0) >= 50:
            alerts.append(
                f"Alta dominância de anunciante: {top_adv.get('advertiser', 'Nao identificado')} concentra {top_adv.get('share_percent', 0)}% do share."
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

    nao_identificado = next(
        (
            item
            for item in share_of_voice
            if str(item.get("advertiser", "")).strip().lower() == "nao identificado"
        ),
        None,
    )
    if nao_identificado and nao_identificado.get("share_percent", 0) >= 20:
        alerts.append(
            f"Oportunidade de qualificação comercial: 'Nao identificado' ainda representa {nao_identificado.get('share_percent', 0)}% do share."
        )

    return alerts


def _dominance_score(share_percent: float, investment: float, avg_visibility: float) -> float:
    score = (share_percent * 0.5) + (min(investment / 1000, 100) * 0.2) + (avg_visibility * 0.3)
    return round(score, 2)


@router.get("/summary/{project_id}")
def get_market_summary(project_id: str, db: Session = Depends(get_db)):
    all_rows = db.query(BannerItem).filter(BannerItem.project_id == project_id).all()

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

    banners = []
    for item in all_rows:
        classification_raw = (getattr(item, "classification", None) or "").strip().lower()
        if classification_raw in editorial_labels:
            continue
        banners.append(item)

    total_banners = len(banners)

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
        advertiser = getattr(item, "advertiser_name", None) or "Nao identificado"
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

    share_of_voice.sort(key=lambda x: x["investment"], reverse=True)
    total_investment = sum(item["investment"] for item in share_of_voice)

    segment_totals = {}
    for item in share_of_voice:
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
                "advertiser": getattr(item, "advertiser_name", None) or "Nao identificado",
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
            "advertiser": getattr(item, "advertiser_name", None) or "Nao identificado",
            "portal": getattr(item, "source_name", None) or "Desconhecido",
            "investment": getattr(item, "estimated_value", None) or 0,
        }
        for item in banners
    ]

    competitive_map = build_competitive_map(
        portal_ranking_data=portal_ranking,
        banner_items_data=banner_items_data,
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
                for a in share_of_voice
            ],
            "segments": segment_ranking,
            "competitive_map": competitive_map,
            "portal_pressure_map": portal_pressure_map,
            "rival_summary": rival_summary,
            "banner_items": banner_items_data,
        }
    )

    return {
        "project_id": project_id,
        "total_banners": total_banners,
        "total_investment": total_investment,
        "share_of_voice": share_of_voice,
        "portal_ranking": portal_ranking,
        "confidence_summary": confidence_summary,
        "strategic_alerts": strategic_alerts,
        "top_visibility_items": top_visibility_items,
        "market_analysis": market_analysis,
        "segment_ranking": segment_ranking,
        "competitive_map": competitive_map,
        "portal_pressure_map": portal_pressure_map,
        "rival_summary": rival_summary,
    }


@router.get("/report/pdf/{project_id}")
def get_market_report_pdf(project_id: str, db: Session = Depends(get_db)):
    summary = get_market_summary(project_id, db)

    competitive_map = summary.get("competitive_map", []) or []
    portal_pressure_map = summary.get("portal_pressure_map", []) or []
    rival_summary = summary.get("rival_summary", {}) or {}
    segment_ranking = summary.get("segment_ranking", []) or []
    market_analysis = summary.get("market_analysis", {}) or {}

    share_of_voice = summary.get("share_of_voice", []) or []
    portal_ranking = summary.get("portal_ranking", []) or []
    strategic_alerts = summary.get("strategic_alerts", []) or []
    confidence_summary = summary.get("confidence_summary", []) or []

    total_banners = summary.get("total_banners", 0) or 0
    total_investment = summary.get("total_investment", 0) or 0

    top_advertiser = share_of_voice[0] if share_of_voice else {}
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
        for item in share_of_voice[:5]
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
                "name": "Sem dados",
                "share": 0,
                "value_fmt": _brl(0),
                "banners": 0,
                "confidence": "n/a",
            }
        ]

    if not top_publishers:
        top_publishers = [
            {
                "name": "Sem dados",
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
        "investment": _brl(total_investment),
        "advertisers": len(share_of_voice),
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
def get_market_report_pptx(project_id: str, db: Session = Depends(get_db)):
    summary = get_market_summary(project_id, db)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pptx")
    tmp.close()

    generate_ppt_report(summary, tmp.name)

    return FileResponse(
        tmp.name,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=f"intel_report_{project_id}.pptx",
    )