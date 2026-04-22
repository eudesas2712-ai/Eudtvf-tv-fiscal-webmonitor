from collections import defaultdict


def calculate_hhi(shares: list[float]) -> float:
    return sum([(s * 100) ** 2 for s in shares])


def classify_market(hhi: float) -> str:
    if hhi < 1500:
        return "Mercado pulverizado"
    elif hhi < 2500:
        return "Concentração moderada"
    return "Alta concentração"


def calculate_dominance(share: float, visibility: float) -> float:
    return round(share * visibility, 2)


def classify_market_roles(advertisers: list[dict]) -> dict:
    sorted_adv = sorted(advertisers, key=lambda x: x["share"], reverse=True)

    roles = {
        "leader": None,
        "challengers": [],
        "followers": [],
        "niche": [],
    }

    if not sorted_adv:
        return roles

    roles["leader"] = sorted_adv[0]["name"]

    for adv in sorted_adv[1:]:
        share = adv["share"]

        if share >= 0.10:
            roles["challengers"].append(adv["name"])
        elif share >= 0.05:
            roles["followers"].append(adv["name"])
        else:
            roles["niche"].append(adv["name"])

    return roles


def classify_competition_level(balance_score: float) -> str:
    if balance_score >= 90:
        return "Conflito direto"
    elif balance_score >= 70:
        return "Competição moderada"
    return "Domínio"


def analyze_portal_dependency(banner_items: list[dict]) -> list[dict]:
    adv_portal = defaultdict(lambda: defaultdict(float))
    adv_total = defaultdict(float)

    for item in banner_items:
        adv = item.get("advertiser") or "Nao identificado"
        portal = item.get("portal")
        inv = float(item.get("investment", 0) or 0)

        if adv == "Nao identificado":
            continue

        adv_portal[adv][portal] += inv
        adv_total[adv] += inv

    results = []

    for adv, portals in adv_portal.items():
        total = adv_total[adv]
        if total == 0:
            continue

        main_portal = max(portals, key=portals.get)
        dependency = portals[main_portal] / total

        if dependency >= 0.60:
            risk = "Alta"
        elif dependency >= 0.40:
            risk = "Média"
        else:
            risk = "Baixa"

        results.append(
            {
                "advertiser": adv,
                "main_portal": main_portal,
                "dependency": round(dependency * 100, 2),
                "risk": risk,
            }
        )

    return sorted(results, key=lambda x: x["dependency"], reverse=True)

def generate_strategic_recommendations(
    advertisers,
    competitive_map,
    portal_pressure_map,
    portal_dependency,
):
    recommendations = []

    if not advertisers:
        return recommendations

    # Ordenar anunciantes por share
    sorted_adv = sorted(advertisers, key=lambda x: x["share"], reverse=True)

    leader = sorted_adv[0]["name"]

    # 1. Ataque competitivo direto
    if competitive_map:
        top_pair = competitive_map[0]

        if top_pair["balance_score"] >= 90:
            recommendations.append(
                f"{top_pair['advertiser_a']} e {top_pair['advertiser_b']} disputam fortemente os mesmos portais. Estratégia recomendada: explorar diferenciação de canais ou aumento de frequência em portais estratégicos."
            )

    # 2. Oportunidade em portal de baixa pressão
    if portal_pressure_map:
        low_pressure = sorted(portal_pressure_map, key=lambda x: x["pressure_score"])[0]

        recommendations.append(
            f"O portal {low_pressure['portal']} apresenta menor pressão competitiva relativa, indicando oportunidade para ganho incremental de share com menor custo de disputa."
        )

    # 3. Dependência alta (risco)
    high_dependency = [d for d in portal_dependency if d["risk"] == "Alta"]

    if high_dependency:
        dep = high_dependency[0]
        recommendations.append(
            f"{dep['advertiser']} apresenta alta dependência do portal {dep['main_portal']} ({dep['dependency']}%). Recomenda-se diversificação de canais para reduzir risco de exposição concentrada."
        )

    # 4. Mercado pulverizado → oportunidade
    if sorted_adv[0]["share"] < 0.20:
        recommendations.append(
            "O mercado apresenta baixa concentração, indicando oportunidade para entrada ou expansão agressiva de share por novos anunciantes."
        )

    # 5. Baixa diversidade
    if len(advertisers) < 12:
        recommendations.append(
            "Baixa diversidade de anunciantes sugere espaço para prospecção comercial e ampliação de inventário competitivo."
        )

    return recommendations


def generate_market_insights(data: dict) -> dict:
    advertisers = data.get("advertisers", [])
    segments = data.get("segments", [])
    competitive_map = data.get("competitive_map", [])
    portal_pressure_map = data.get("portal_pressure_map", [])
    rival_summary = data.get("rival_summary", {})
    banner_items = data.get("banner_items", [])

    if not advertisers:
        return {
            "hhi": 0,
            "market_type": "Sem dados",
            "insights": [],
            "alerts": [],
            "opportunities": [],
            "market_roles": {
                "leader": None,
                "challengers": [],
                "followers": [],
                "niche": [],
            },
            "portal_dependency": [],
        }

    shares = [a["share"] for a in advertisers if a.get("share", 0) > 0]

    hhi = calculate_hhi(shares)
    market_type = classify_market(hhi)

    insights = []
    alerts = []
    opportunities = []

    advertisers_sorted = sorted(advertisers, key=lambda x: x["share"], reverse=True)
    top_share = advertisers_sorted[0]["share"]
    top_name = advertisers_sorted[0]["name"]

    market_roles = classify_market_roles(advertisers)
    portal_dependency = analyze_portal_dependency(banner_items)

    insights.append(
        f"{top_name} lidera com {round(top_share * 100, 2)}% de share"
    )

    if len(advertisers) < 15:
        insights.append("Baixa diversidade de anunciantes no ambiente monitorado")

    if segments:
        top_segment = sorted(segments, key=lambda x: x["share_percent"], reverse=True)[0]
        insights.append(
            f"O segmento {top_segment['segment']} lidera o investimento com {round(top_segment['share_percent'], 2)}% de share."
        )

    if competitive_map:
        top_comp = competitive_map[0]
        insights.append(
            f"{top_comp['advertiser_a']} e {top_comp['advertiser_b']} disputam {top_comp['shared_portals_count']} portais em comum."
        )

        if "balance_score" in top_comp:
            comp_level = classify_competition_level(top_comp["balance_score"])
            insights.append(
                f"O principal embate competitivo atual é classificado como {comp_level.lower()}."
            )

    if rival_summary and rival_summary.get("top_pressure_pair"):
        pair = rival_summary["top_pressure_pair"]
        insights.append(
            f"O par mais equilibrado é {pair['advertiser_a']} vs {pair['advertiser_b']}, com equilíbrio competitivo de {pair['balance_score']}."
        )

    if market_roles.get("leader"):
        challengers = market_roles.get("challengers", [])
        if challengers:
            insights.append(
                f"O líder atual é {market_roles['leader']}, com desafiantes diretos: {', '.join(challengers[:3])}."
            )

    if top_share > 0.30:
        alerts.append("Alta concentração de investimento em um único anunciante")

    nao_identificados = [a for a in advertisers if "Nao identificado" in a["name"]]
    if nao_identificados:
        ni_share = nao_identificados[0]["share"]
        if ni_share > 0.20:
            alerts.append("Alta taxa de inventário não identificado")

    if portal_pressure_map:
        top_pressure = portal_pressure_map[0]
        if top_pressure["pressure_label"] == "Alta":
            alerts.append(
                f"O portal {top_pressure['portal']} apresenta alta pressão competitiva."
            )

    high_dependency = [d for d in portal_dependency if d["risk"] == "Alta"]
    if high_dependency:
        dep = high_dependency[0]
        alerts.append(
            f"{dep['advertiser']} apresenta alta dependência do portal {dep['main_portal']} ({dep['dependency']}%)."
        )

    if len(advertisers) < 12:
        opportunities.append("Espaço para expansão de novos anunciantes")

    if top_share < 0.20:
        opportunities.append("Mercado equilibrado com oportunidade de entrada")

    if portal_pressure_map:
        low_pressure = sorted(portal_pressure_map, key=lambda x: x["pressure_score"])[0]
        opportunities.append(
            f"O portal {low_pressure['portal']} apresenta menor pressão competitiva relativa."
        )

    if portal_dependency:
        low_risk = [d for d in portal_dependency if d["risk"] == "Baixa"]
        if low_risk:
            opportunities.append(
                f"{low_risk[0]['advertiser']} apresenta portfólio mais distribuído entre portais, indicando resiliência de presença."
            )

    recommendations = generate_strategic_recommendations(
      advertisers,
      competitive_map,
      portal_pressure_map,
      portal_dependency,
  )

    return {
        "hhi": round(hhi, 2),
        "market_type": market_type,
        "insights": insights,
        "alerts": alerts,
        "opportunities": opportunities,
        "market_roles": market_roles,
        "portal_dependency": portal_dependency,
        "recommendations": recommendations,
    }