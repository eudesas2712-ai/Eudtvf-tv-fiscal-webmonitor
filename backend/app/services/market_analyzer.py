from collections import defaultdict


def classify_market_roles(advertisers: list[dict]) -> dict:
    roles = {
        "leader": None,
        "challengers": [],
        "followers": [],
        "niche": [],
    }

    if not advertisers:
        return roles

    sorted_adv = sorted(advertisers, key=lambda x: x.get("share", 0), reverse=True)
    roles["leader"] = sorted_adv[0].get("name")

    for adv in sorted_adv[1:]:
        name = adv.get("name")
        share = adv.get("share", 0)

        if share >= 0.10:
            roles["challengers"].append(name)
        elif share >= 0.05:
            roles["followers"].append(name)
        else:
            roles["niche"].append(name)

    return roles


def classify_competition_level(balance_score: float) -> str:
    if balance_score >= 90:
        return "Conflito direto"
    if balance_score >= 70:
        return "Competição moderada"
    return "Domínio"


def analyze_portal_dependency(banner_items: list[dict]) -> list[dict]:
    adv_portal = defaultdict(lambda: defaultdict(float))
    adv_total = defaultdict(float)

    for item in banner_items or []:
        adv = item.get("advertiser") or "Nao identificado"
        portal = item.get("portal") or "Desconhecido"
        inv = float(item.get("investment", 0) or 0)

        if adv == "Nao identificado":
            continue

        adv_portal[adv][portal] += inv
        adv_total[adv] += inv

    results = []

    for adv, portals in adv_portal.items():
        total = adv_total[adv]
        if total <= 0:
            continue

        main_portal = max(portals, key=portals.get)
        dependency = portals[main_portal] / total

        if dependency >= 0.60:
            risk = "Alta"
        elif dependency >= 0.40:
            risk = "Média"
        else:
            risk = "Baixa"

        results.append({
            "advertiser": adv,
            "main_portal": main_portal,
            "dependency": round(dependency * 100, 2),
            "risk": risk,
        })

    return sorted(results, key=lambda x: x["dependency"], reverse=True)


def generate_strategic_recommendations(
    advertisers,
    competitive_map,
    portal_pressure_map,
    portal_dependency,
):
    recommendations = []

    if competitive_map:
        top_pair = competitive_map[0]
        balance = float(top_pair.get("balance_score", 0) or 0)

        if balance >= 90:
            recommendations.append(
                f"{top_pair.get('advertiser_a')} e {top_pair.get('advertiser_b')} disputam fortemente os mesmos portais. Recomenda-se explorar diferenciação de canais, criativos e frequência para ganho de share."
            )

    if portal_pressure_map:
        low_pressure = sorted(
            portal_pressure_map,
            key=lambda x: x.get("pressure_score", 0),
        )[0]

        recommendations.append(
            f"O portal {low_pressure.get('portal')} apresenta menor pressão competitiva relativa, indicando oportunidade para ganho incremental de share com menor custo de disputa."
        )

    high_dependency = [d for d in portal_dependency if d.get("risk") == "Alta"]
    if high_dependency:
        dep = high_dependency[0]
        recommendations.append(
            f"{dep.get('advertiser')} apresenta alta dependência do portal {dep.get('main_portal')} ({dep.get('dependency')}%). Recomenda-se diversificar canais para reduzir risco de exposição concentrada."
        )

    if advertisers:
        top_share = advertisers[0].get("share", 0)
        if top_share < 0.20:
            recommendations.append(
                "O mercado apresenta baixa concentração, indicando oportunidade para entrada ou expansão agressiva de share."
            )

    if len(advertisers) < 12:
        recommendations.append(
            "Baixa diversidade de anunciantes sugere espaço para prospecção comercial e ampliação de inventário competitivo."
        )

    return recommendations


def generate_market_insights(data: dict) -> dict:
    advertisers = data.get("advertisers", []) or []
    segments = data.get("segments", []) or []
    competitive_map = data.get("competitive_map", []) or []
    portal_pressure_map = data.get("portal_pressure_map", []) or []
    rival_summary = data.get("rival_summary", {}) or {}
    banner_items = data.get("banner_items", []) or []

    if not advertisers:
        return {
            "market_type": "Sem dados",
            "insights": ["Dados insuficientes para análise."],
            "alerts": [],
            "opportunities": ["Coleta de dados recomendada."],
            "recommendations": ["Ampliar a coleta e validar a base antes da análise comercial."],
            "market_roles": {
                "leader": None,
                "challengers": [],
                "followers": [],
                "niche": [],
            },
            "portal_dependency": [],
        }

    advertisers_sorted = sorted(advertisers, key=lambda x: x.get("share", 0), reverse=True)
    top = advertisers_sorted[0]
    top_name = top.get("name", "Sem dados")
    top_share = float(top.get("share", 0) or 0)

    if top_share > 0.40:
        market_type = "Mercado concentrado"
    elif top_share > 0.25:
        market_type = "Mercado semi-concentrado"
    else:
        market_type = "Mercado pulverizado"

    insights = [
        f"{top_name} lidera com {round(top_share * 100, 2)}% de share."
    ]

    if len(advertisers_sorted) < 15:
        insights.append("Baixa diversidade de anunciantes no ambiente monitorado.")
    else:
        insights.append("Ambiente competitivo com boa diversidade de anunciantes.")

    if segments:
        top_segment = sorted(
            segments,
            key=lambda x: x.get("share_percent", 0),
            reverse=True,
        )[0]
        insights.append(
            f"O segmento {top_segment.get('segment')} lidera o investimento com {round(top_segment.get('share_percent', 0), 2)}% de share."
        )

    if competitive_map:
        top_comp = competitive_map[0]
        insights.append(
            f"{top_comp.get('advertiser_a')} e {top_comp.get('advertiser_b')} disputam {top_comp.get('shared_portals_count')} portais em comum."
        )

        if "balance_score" in top_comp:
            level = classify_competition_level(float(top_comp.get("balance_score", 0) or 0))
            insights.append(
                f"O principal embate competitivo atual é classificado como {level.lower()}."
            )

    if rival_summary and rival_summary.get("top_pressure_pair"):
        pair = rival_summary["top_pressure_pair"]
        insights.append(
            f"O par mais equilibrado é {pair.get('advertiser_a')} vs {pair.get('advertiser_b')}, com equilíbrio competitivo de {pair.get('balance_score')}."
        )

    alerts = []

    nao_identificados = [
        a for a in advertisers_sorted
        if "Nao identificado" in str(a.get("name", ""))
    ]
    if nao_identificados and float(nao_identificados[0].get("share", 0) or 0) > 0.20:
        alerts.append("Alta taxa de inventário não identificado.")

    if portal_pressure_map:
        top_pressure = sorted(
            portal_pressure_map,
            key=lambda x: x.get("pressure_score", 0),
            reverse=True,
        )[0]

        if top_pressure.get("pressure_label") == "Alta":
            alerts.append(
                f"O portal {top_pressure.get('portal')} apresenta alta pressão competitiva."
            )

    opportunities = []

    if top_share < 0.20:
        opportunities.append("Mercado equilibrado com oportunidade de entrada ou expansão de share.")

    if portal_pressure_map:
        low_pressure = sorted(
            portal_pressure_map,
            key=lambda x: x.get("pressure_score", 0),
        )[0]
        opportunities.append(
            f"O portal {low_pressure.get('portal')} apresenta menor pressão competitiva relativa."
        )

    if len(advertisers_sorted) < 12:
        opportunities.append("Espaço para expansão de novos anunciantes.")

    market_roles = classify_market_roles(advertisers_sorted)
    portal_dependency = analyze_portal_dependency(banner_items)

    recommendations = generate_strategic_recommendations(
        advertisers_sorted,
        competitive_map,
        portal_pressure_map,
        portal_dependency,
    )

    return {
        "market_type": market_type,
        "insights": insights,
        "alerts": alerts,
        "opportunities": opportunities,
        "recommendations": recommendations,
        "market_roles": market_roles,
        "portal_dependency": portal_dependency,
    }