from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable

UNKNOWN_ALIASES = {
    "",
    "nao identificado",
    "não identificado",
    "nao-identificado",
    "não-identificado",
    "n/a",
    "na",
    "none",
    "null",
    "sem dados",
    "desconhecido",
    "indefinido",
}

UNKNOWN_DISPLAY = "Pendente de identificação"


def _norm(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def is_unknown_advertiser(value: Any) -> bool:
    normalized = _norm(value)
    if normalized in UNKNOWN_ALIASES:
        return True
    return normalized in {"nao identificado", "nao identificada", "nao identificados", "nao identificadas"}


def display_advertiser_name(value: Any) -> str:
    return UNKNOWN_DISPLAY if is_unknown_advertiser(value) else str(value or "").strip()


def split_share_of_voice(items: Iterable[dict], total_items: int | None = None, total_investment: int | float | None = None) -> dict:
    rows = list(items or [])
    identified: list[dict] = []
    unknown_rows: list[dict] = []

    for row in rows:
        name = row.get("advertiser") or row.get("name")
        if is_unknown_advertiser(name):
            unknown_rows.append(row)
        else:
            identified.append(row)

    unknown_items = sum(int(r.get("banners", r.get("items", 0)) or 0) for r in unknown_rows)
    unknown_investment = sum(float(r.get("investment", 0) or 0) for r in unknown_rows)
    identified_items = sum(int(r.get("banners", r.get("items", 0)) or 0) for r in identified)
    identified_investment = sum(float(r.get("investment", 0) or 0) for r in identified)

    denominator_items = int(total_items if total_items is not None else (unknown_items + identified_items)) or 0
    denominator_investment = float(total_investment if total_investment is not None else (unknown_investment + identified_investment)) or 0.0

    return {
        "identified": identified,
        "unknown_rows": unknown_rows,
        "unknown_items": unknown_items,
        "unknown_investment": unknown_investment,
        "unknown_share_items": round((unknown_items / denominator_items) * 100, 2) if denominator_items else 0,
        "unknown_share_investment": round((unknown_investment / denominator_investment) * 100, 2) if denominator_investment else 0,
        "identified_items": identified_items,
        "identified_investment": identified_investment,
        "identified_share_items": round((identified_items / denominator_items) * 100, 2) if denominator_items else 0,
        "identified_share_investment": round((identified_investment / denominator_investment) * 100, 2) if denominator_investment else 0,
        "identified_advertisers": len(identified),
    }


def identification_alerts(quality: dict) -> list[str]:
    alerts: list[str] = []
    unknown_share = float(quality.get("unknown_share_items", 0) or 0)
    unknown_items = int(quality.get("unknown_items", 0) or 0)
    unknown_investment = float(quality.get("unknown_investment", 0) or 0)
    if unknown_items <= 0:
        return alerts
    if unknown_share >= 30:
        alerts.append(
            f"Inventário pendente de identificação representa {unknown_share:.2f}% dos itens de mercado; tratar como fila de auditoria comercial, não como anunciante líder."
        )
    else:
        alerts.append(
            f"Há {unknown_items} item(ns) pendente(s) de identificação comercial para revisão de marca/anunciante."
        )
    if unknown_investment > 0:
        alerts.append(
            f"Investimento estimado pendente de identificação: R$ {unknown_investment:,.0f}".replace(",", ".")
        )
    return alerts
