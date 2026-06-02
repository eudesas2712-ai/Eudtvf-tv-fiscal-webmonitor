def analyze_market_trends(points: list[dict]) -> dict:
    if not points or len(points) < 2:
        return {
            "has_trends": False,
            "summary": "Histórico insuficiente para análise de tendência.",
            "trends": [],
            "alerts": [],
        }

    previous = points[-2]
    current = points[-1]

    trends = []
    alerts = []

    prev_investment = float(previous.get("total_investment", 0) or 0)
    curr_investment = float(current.get("total_investment", 0) or 0)

    prev_share = float(previous.get("top_advertiser_share", 0) or 0)
    curr_share = float(current.get("top_advertiser_share", 0) or 0)

    investment_delta = curr_investment - prev_investment
    share_delta = curr_share - prev_share

    previous_leader = previous.get("top_advertiser", "N/D")
    current_leader = current.get("top_advertiser", "N/D")

    if investment_delta > 0:
        trends.append({
            "type": "investment_growth",
            "label": "Crescimento de investimento",
            "message": f"O investimento estimado cresceu R$ {investment_delta:,.0f}.",
            "value": investment_delta,
        })

    elif investment_delta < 0:
        trends.append({
            "type": "investment_drop",
            "label": "Queda de investimento",
            "message": f"O investimento estimado caiu R$ {abs(investment_delta):,.0f}.",
            "value": investment_delta,
        })

    else:
        trends.append({
            "type": "investment_stable",
            "label": "Investimento estável",
            "message": "O investimento estimado permaneceu estável.",
            "value": 0,
        })

    if current_leader != previous_leader:
        alerts.append({
            "type": "leader_change",
            "label": "Mudança de liderança",
            "message": f"{current_leader} assumiu a liderança, substituindo {previous_leader}.",
        })
    else:
        trends.append({
            "type": "leader_stable",
            "label": "Liderança mantida",
            "message": f"{current_leader} manteve a liderança no período.",
        })

    if share_delta > 0:
        trends.append({
            "type": "share_growth",
            "label": "Crescimento de share",
            "message": f"O share do líder cresceu {share_delta:.2f} pontos percentuais.",
            "value": share_delta,
        })

    elif share_delta < 0:
        trends.append({
            "type": "share_drop",
            "label": "Queda de share",
            "message": f"O share do líder caiu {abs(share_delta):.2f} pontos percentuais.",
            "value": share_delta,
        })

    else:
        trends.append({
            "type": "share_stable",
            "label": "Share estável",
            "message": "O share do líder permaneceu estável.",
            "value": 0,
        })

    return {
        "has_trends": True,
        "summary": "Análise de tendência gerada com sucesso.",
        "previous_snapshot": previous,
        "current_snapshot": current,
        "trends": trends,
        "alerts": alerts,
    }