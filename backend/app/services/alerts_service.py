from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import BannerItem, Item
from app.services.identification_quality import is_unknown_advertiser, display_advertiser_name


def _num(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _brl(value: Any) -> str:
    return f"R$ {_num(value):,.0f}".replace(",", ".")


def _pct(numerator: float, denominator: float) -> float:
    return round((numerator / denominator) * 100, 2) if denominator else 0.0


def _severity(score: int) -> str:
    if score >= 85:
        return "critico"
    if score >= 65:
        return "alto"
    if score >= 40:
        return "medio"
    return "informativo"


def _publicity_market_items(rows: list[BannerItem]) -> list[BannerItem]:
    result = []
    for item in rows:
        if getattr(item, "market_status", None) == "incluido":
            result.append(item)
        elif getattr(item, "content_type", None) == "advertising" and getattr(item, "checking_status", None) != "rejeitado":
            result.append(item)
    return result


def _alert(alert_id: str, title: str, message: str, category: str, score: int, action: str, metric: str | None = None, route: str | None = None) -> dict:
    return {
        "id": alert_id,
        "title": title,
        "message": message,
        "category": category,
        "severity": _severity(score),
        "score": score,
        "metric": metric,
        "recommended_action": action,
        "route": route,
    }


def build_executive_alerts(db: Session, project_id: str) -> dict:
    banners = db.query(BannerItem).filter(BannerItem.project_id == project_id).all()
    editorial_items = db.query(Item).filter(Item.project_id == project_id).all()

    market_items = _publicity_market_items(banners)
    detected_total = len(banners)
    market_total = len(market_items)
    auditables = [b for b in banners if getattr(b, "checking_status", None) == "auditavel"]
    review_items = [b for b in banners if getattr(b, "checking_status", None) in {"revisao", "parcial"}]
    news_candidates = [b for b in banners if getattr(b, "news_status", None) == "candidato"]
    preserved = [b for b in banners if bool(getattr(b, "has_preserved_evidence", False))]

    unknown_items = [b for b in market_items if is_unknown_advertiser(getattr(b, "advertiser_name", None))]
    unknown_investment = sum(_num(getattr(b, "estimated_value", 0)) for b in unknown_items)
    market_investment = sum(_num(getattr(b, "estimated_value", 0)) for b in market_items)
    unknown_rate = _pct(len(unknown_items), market_total)
    unknown_investment_rate = _pct(unknown_investment, market_investment)

    confidence_counts = Counter()
    low_confidence_value = 0.0
    for item in market_items:
        score = _num(getattr(item, "classification_score", None) or getattr(item, "publicity_score", None))
        if score >= 75:
            confidence_counts["alta"] += 1
        elif score >= 55:
            confidence_counts["media"] += 1
        else:
            confidence_counts["baixa"] += 1
            low_confidence_value += _num(getattr(item, "estimated_value", 0))
    low_conf_rate = _pct(confidence_counts["baixa"], market_total)

    portal_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"items": 0, "investment": 0.0, "auditables": 0, "unknown": 0})
    advertiser_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"items": 0, "investment": 0.0, "auditables": 0})
    for item in market_items:
        portal = getattr(item, "source_name", None) or "Portal não informado"
        advertiser = display_advertiser_name(getattr(item, "advertiser_name", None)) or "Pendente de identificação"
        value = _num(getattr(item, "estimated_value", 0))
        portal_stats[portal]["items"] += 1
        portal_stats[portal]["investment"] += value
        portal_stats[portal]["auditables"] += 1 if getattr(item, "checking_status", None) == "auditavel" else 0
        portal_stats[portal]["unknown"] += 1 if is_unknown_advertiser(getattr(item, "advertiser_name", None)) else 0
        advertiser_stats[advertiser]["items"] += 1
        advertiser_stats[advertiser]["investment"] += value
        advertiser_stats[advertiser]["auditables"] += 1 if getattr(item, "checking_status", None) == "auditavel" else 0

    portal_ranking = sorted(
        [
            {"portal": k, **v, "share": _pct(v["investment"], market_investment)}
            for k, v in portal_stats.items()
        ],
        key=lambda x: x["investment"],
        reverse=True,
    )
    advertiser_ranking = sorted(
        [
            {"advertiser": k, **v, "share": _pct(v["investment"], market_investment)}
            for k, v in advertiser_stats.items() if k != "Pendente de identificação"
        ],
        key=lambda x: x["investment"],
        reverse=True,
    )

    negative_editorial = [i for i in editorial_items if (getattr(i, "sentiment", "") or "").lower() == "negativo" or _num(getattr(i, "sentiment_score", 0)) <= -40]
    high_risk_editorial = [i for i in negative_editorial if _num(getattr(i, "sentiment_score", 0)) <= -60 or (getattr(i, "topic", "") or "").lower() in {"segurança", "politica", "política"}]
    matched_editorial = [i for i in editorial_items if getattr(i, "matched_terms", None)]
    topic_counts = Counter((getattr(i, "topic", None) or "Sem tema") for i in editorial_items)
    source_counts = Counter((getattr(i, "source_name", None) or "Fonte não informada") for i in editorial_items)

    alerts: list[dict] = []

    if unknown_items:
        score = min(98, 45 + int(unknown_rate))
        alerts.append(_alert(
            "identificacao_pendente",
            "Fila de identificação comercial elevada",
            f"Há {len(unknown_items)} item(ns) pendente(s) de identificação, equivalentes a {unknown_rate:.2f}% dos itens de mercado e {_brl(unknown_investment)} em investimento estimado.",
            "identificacao",
            score,
            "Priorizar /admin/identificacao para transformar pendentes em anunciantes reais ou remover ruído do mercado.",
            f"{unknown_rate:.2f}% pendente",
            "/admin/identificacao",
        ))

    if auditables:
        alerts.append(_alert(
            "checking_auditavel",
            "Evidências auditáveis disponíveis para checking",
            f"Existem {len(auditables)} peça(s) auditável(is) com prova preservada. Essas evidências estão prontas para conferência documental.",
            "checking",
            55 if len(auditables) < 50 else 70,
            "Validar amostras em /evidencias e gerar relatório em modo checking auditável quando necessário.",
            f"{len(auditables)} auditáveis",
            "/evidencias",
        ))

    if review_items:
        alerts.append(_alert(
            "revisao_checking",
            "Itens em revisão/parcial exigem curadoria",
            f"Há {len(review_items)} item(ns) em revisão ou parcial. Eles não devem ser tratados como checking comprovado sem validação.",
            "checking",
            min(90, 35 + int(_pct(len(review_items), max(detected_total, 1)))),
            "Filtrar status revisão/parcial em /evidencias e decidir se serão aprovados, rebaixados ou mantidos como mercado referencial.",
            f"{len(review_items)} em revisão/parcial",
            "/evidencias",
        ))

    if low_conf_rate >= 20:
        alerts.append(_alert(
            "baixa_confianca",
            "Volume relevante de baixa confiança",
            f"{low_conf_rate:.2f}% dos itens de mercado estão em baixa confiança, somando {_brl(low_confidence_value)} estimados.",
            "qualidade",
            min(88, 40 + int(low_conf_rate)),
            "Revisar OCR, aliases, screenshots e regras de classificação para reduzir ruído no Intel.",
            f"{low_conf_rate:.2f}% baixa confiança",
            "/admin/identificacao",
        ))

    if portal_ranking and portal_ranking[0]["share"] >= 25:
        top = portal_ranking[0]
        alerts.append(_alert(
            "concentracao_portal",
            "Concentração relevante em portal",
            f"{top['portal']} concentra {top['share']:.2f}% do investimento estimado em mercado.",
            "mercado",
            min(84, 40 + int(top["share"])),
            "Avaliar dependência de canal, pressão competitiva e oportunidade de expansão em portais com menor saturação.",
            f"{top['share']:.2f}% no portal líder",
            "/intel",
        ))

    if news_candidates:
        alerts.append(_alert(
            "noticias_candidatas",
            "Conteúdo editorial separado da publicidade",
            f"Foram preservados {len(news_candidates)} item(ns) candidato(s) a notícia. Eles não devem entrar como publicidade auditável.",
            "editorial",
            50 if len(news_candidates) < detected_total * 0.6 else 72,
            "Manter a separação entre clipping editorial e checking publicitário; revisar em /editorial e no relatório unificado.",
            f"{len(news_candidates)} candidatos a notícia",
            "/editorial",
        ))

    if negative_editorial:
        alerts.append(_alert(
            "editorial_negativo",
            "Matérias negativas no clipping editorial",
            f"O monitoramento editorial possui {len(negative_editorial)} matéria(s) negativa(s), sendo {len(high_risk_editorial)} de maior atenção reputacional.",
            "editorial",
            65 if len(high_risk_editorial) else 48,
            "Revisar matérias negativas, fonte, tema e termos monitorados. Gerar relatório analítico expandido quando houver risco de repercussão.",
            f"{len(negative_editorial)} negativas",
            "/editorial",
        ))

    if matched_editorial:
        alerts.append(_alert(
            "termos_editoriais",
            "Termos/marcas monitorados detectados em notícias",
            f"Há {len(matched_editorial)} matéria(s) com termos ou marcas monitoradas no clipping editorial.",
            "editorial",
            58,
            "Filtrar por termos no /editorial e avaliar necessidade de resposta, clipping específico ou relatório ao cliente.",
            f"{len(matched_editorial)} com termos",
            "/editorial",
        ))

    alerts = sorted(alerts, key=lambda x: x["score"], reverse=True)

    summary = {
        "project_id": project_id,
        "generated_at": datetime.utcnow().isoformat(),
        "total_alerts": len(alerts),
        "critical_alerts": len([a for a in alerts if a["severity"] == "critico"]),
        "high_alerts": len([a for a in alerts if a["severity"] == "alto"]),
        "medium_alerts": len([a for a in alerts if a["severity"] == "medio"]),
        "info_alerts": len([a for a in alerts if a["severity"] == "informativo"]),
        "market_items": market_total,
        "auditables": len(auditables),
        "pending_identification": len(unknown_items),
        "pending_identification_rate": unknown_rate,
        "pending_identification_investment": int(unknown_investment),
        "low_confidence_rate": low_conf_rate,
        "editorial_items": len(editorial_items),
        "negative_editorial": len(negative_editorial),
        "news_candidates": len(news_candidates),
    }

    return {
        "summary": summary,
        "alerts": alerts,
        "market": {
            "top_advertisers": advertiser_ranking[:8],
            "top_portals": portal_ranking[:8],
            "confidence": dict(confidence_counts),
        },
        "editorial": {
            "top_topics": [{"topic": k, "count": v} for k, v in topic_counts.most_common(8)],
            "top_sources": [{"source": k, "count": v} for k, v in source_counts.most_common(8)],
            "latest_negative": [
                {
                    "title": getattr(i, "title", ""),
                    "source": getattr(i, "source_name", None),
                    "topic": getattr(i, "topic", None),
                    "sentiment_score": getattr(i, "sentiment_score", None),
                    "url": getattr(i, "url", None),
                    "created_at": getattr(i, "created_at", None).isoformat() if getattr(i, "created_at", None) else None,
                }
                for i in sorted(negative_editorial, key=lambda x: getattr(x, "created_at", datetime.min), reverse=True)[:10]
            ],
        },
    }
