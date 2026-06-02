from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
import matplotlib.pyplot as plt
import tempfile
from pathlib import Path

from app.services.identification_quality import is_unknown_advertiser

LOGO_HEADER_PATH = Path(__file__).resolve().parent.parent / "assets" / "logo_tvfiscal_header.png"

RED = RGBColor(197, 38, 37)
DARK = RGBColor(28, 31, 35)
GRAY = RGBColor(105, 112, 120)
LIGHT = RGBColor(244, 246, 248)
MID = RGBColor(226, 230, 235)
WHITE = RGBColor(255, 255, 255)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

def generate_timeline_chart(timeline):

    import matplotlib.pyplot as plt
    import tempfile
    import os

    if not timeline:
        return None

    dates = []
    investments = []

    for point in timeline[-10:]:

        label = str(point.get("created_at", ""))[:10]

        value = float(
            point.get("total_investment", 0) or 0
        )

        dates.append(label)
        investments.append(value)

    fig, ax = plt.subplots(figsize=(10, 3))

    ax.plot(
        dates,
        investments,
        marker="o",
        linewidth=3,
    )

    ax.set_title(
        "Evolução Temporal do Investimento",
        fontsize=14,
        fontweight="bold",
    )

    ax.grid(True)

    tmp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".png"
    )

    fig.savefig(
        tmp.name,
        dpi=220,
        bbox_inches="tight",
    )

    plt.close(fig)

    if os.path.exists(tmp.name):
        return tmp.name

    return None

def brl(v):
    try:
        return f"R$ {float(v or 0):,.0f}".replace(",", ".")
    except Exception:
        return "R$ 0"


def pct(v):
    try:
        return f"{float(v or 0):.2f}%"
    except Exception:
        return "0.00%"


def short(text, n=36):
    text = str(text or "")
    return text if len(text) <= n else text[: n - 1] + "…"


def add_bg(slide, color=WHITE):
    bg = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, 0, 0, SLIDE_W, SLIDE_H)
    bg.fill.solid()
    bg.fill.fore_color.rgb = color
    bg.line.fill.background()
    slide.shapes._spTree.remove(bg._element)
    slide.shapes._spTree.insert(2, bg._element)


def add_logo(slide, left=Inches(11.75), top=Inches(0.06), width=Inches(0.95)):
    try:
        if LOGO_HEADER_PATH.exists():
            slide.shapes.add_picture(str(LOGO_HEADER_PATH), left, top, width=width)
    except Exception:
        pass


def add_header(slide, section="TV Fiscal WebMonitor"):
    bar = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, 0, 0, SLIDE_W, Inches(0.42))
    bar.fill.solid()
    bar.fill.fore_color.rgb = RED
    bar.line.fill.background()

    add_text(slide, Inches(0.55), Inches(0.08), Inches(6), Inches(0.25), section, 10, True, WHITE)
    add_logo(slide)


def add_text(slide, left, top, width, height, text, size=14, bold=False, color=DARK, align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP

    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = str(text)
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    r.font.name = "Arial"
    return box


def add_title(slide, title, subtitle=None):
    add_text(slide, Inches(0.65), Inches(0.82), Inches(11.8), Inches(0.45), title, 28, True, DARK)
    if subtitle:
        add_text(slide, Inches(0.68), Inches(1.32), Inches(11.5), Inches(0.35), subtitle, 12, False, GRAY)


def add_card(slide, left, top, width, height, label, value):
    card = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = WHITE
    card.line.color.rgb = MID

    accent = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, left, top, Inches(0.10), height)
    accent.fill.solid()
    accent.fill.fore_color.rgb = RED
    accent.line.fill.background()

    add_text(slide, left + Inches(0.25), top + Inches(0.15), width - Inches(0.35), Inches(0.25), label, 10, True, GRAY)
    add_text(slide, left + Inches(0.25), top + Inches(0.47), width - Inches(0.35), Inches(0.45), value, 22, True, DARK)


def add_panel(slide, left, top, width, height, title, lines):
    panel = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, left, top, width, height)
    panel.fill.solid()
    panel.fill.fore_color.rgb = WHITE
    panel.line.color.rgb = MID

    add_text(slide, left + Inches(0.25), top + Inches(0.15), width - Inches(0.4), Inches(0.25), title, 13, True, RED)

    y = top + Inches(0.52)
    for line in (lines or ["Sem dados disponíveis."])[:6]:
        add_text(slide, left + Inches(0.25), y, width - Inches(0.45), Inches(0.35), f"• {line}", 12, False, DARK)
        y += Inches(0.42)


def add_bar_list(slide, title, data, label_key, value_key, left, top, width, height, max_items=6):
    add_text(slide, left, top - Inches(0.42), width, Inches(0.3), title, 16, True, RED)

    data = (data or [])[:max_items]
    max_value = max([float(x.get(value_key, 0) or 0) for x in data], default=1)

    row_h = height / max(max_items, 1)

    for i, item in enumerate(data):
        y = top + row_h * i
        label = short(item.get(label_key, "—"), 34)
        value = float(item.get(value_key, 0) or 0)
        bar_w = Inches(4.9) * (value / max_value if max_value else 0)

        add_text(slide, left, y, Inches(3.35), Inches(0.28), label, 10.5, True, DARK)

        bg = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, left + Inches(3.55), y, Inches(5.0), Inches(0.22))
        bg.fill.solid()
        bg.fill.fore_color.rgb = LIGHT
        bg.line.fill.background()

        bar = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, left + Inches(3.55), y, bar_w, Inches(0.22))
        bar.fill.solid()
        bar.fill.fore_color.rgb = RED
        bar.line.fill.background()

        add_text(slide, left + Inches(8.75), y - Inches(0.02), Inches(1.1), Inches(0.28), pct(value), 10.5, True, DARK)


def add_table(slide, title, columns, rows, left, top, width, height):
    add_text(slide, left, top - Inches(0.42), width, Inches(0.3), title, 16, True, RED)

    rows = rows[:7] if rows else [["—"] * len(columns)]
    shape = slide.shapes.add_table(len(rows) + 1, len(columns), left, top, width, height)
    table = shape.table

    for c, col in enumerate(columns):
        cell = table.cell(0, c)
        cell.text = str(col)
        cell.fill.solid()
        cell.fill.fore_color.rgb = RED
        for p in cell.text_frame.paragraphs:
            for r in p.runs:
                r.font.size = Pt(8.5)
                r.font.bold = True
                r.font.color.rgb = WHITE
                r.font.name = "Arial"

    for r_idx, row in enumerate(rows, start=1):
        for c_idx, val in enumerate(row):
            cell = table.cell(r_idx, c_idx)
            cell.text = str(val)
            cell.fill.solid()
            cell.fill.fore_color.rgb = WHITE if r_idx % 2 else LIGHT
            for p in cell.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(8.5)
                    r.font.color.rgb = DARK
                    r.font.name = "Arial"


def add_bullets(slide, title, items, left=Inches(0.9), top=Inches(1.95), width=Inches(11.5)):
    add_text(slide, left, top - Inches(0.42), width, Inches(0.3), title, 16, True, RED)

    y = top
    for item in (items or ["Sem dados disponíveis."])[:7]:
        add_text(slide, left, y, width, Inches(0.38), f"• {item}", 14, False, DARK)
        y += Inches(0.52)


def new_slide(prs, title, subtitle=None, bg=WHITE):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide, bg)
    add_header(slide)
    add_title(slide, title, subtitle)
    return slide


def generate_ppt_report(summary: dict, filename: str):
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    market = summary.get("market_analysis", {}) or {}

    # 1 CAPA
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide, LIGHT)
    add_header(slide)
    hero = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.4), Inches(11.7), Inches(2.1))
    hero.fill.solid()
    hero.fill.fore_color.rgb = RED
    hero.line.fill.background()
    add_text(slide, Inches(1.15), Inches(1.8), Inches(10.5), Inches(0.55), "TV Fiscal WebMonitor", 18, True, WHITE)
    add_text(slide, Inches(1.15), Inches(2.28), Inches(10.5), Inches(0.55), "Inteligência de Mercado Publicitário Digital", 28, True, WHITE)
    add_text(slide, Inches(1.15), Inches(3.02), Inches(10.5), Inches(0.35), f"Projeto: {summary.get('project_id')}", 13, False, WHITE)
    add_text(slide, Inches(1.0), Inches(4.25), Inches(10), Inches(0.35), f"Itens de mercado: {summary.get('total_market_items', summary.get('total_banners', 0))}", 18, True)
    add_text(slide, Inches(1.0), Inches(4.70), Inches(10), Inches(0.35), f"Investimento estimado: {brl(summary.get('total_investment', 0))}", 18, True)

    # 2 RESUMO
    slide = new_slide(prs, "Resumo Executivo", "Indicadores principais do projeto monitorado")
    add_card(slide, Inches(0.7), Inches(1.9), Inches(2.7), Inches(1.1), "Investimento", brl(summary.get("total_investment", 0)))
    add_card(slide, Inches(3.65), Inches(1.9), Inches(2.3), Inches(1.1), "Itens Mercado", str(summary.get("total_market_items", summary.get("total_banners", 0))))
    add_card(slide, Inches(6.2), Inches(1.9), Inches(2.3), Inches(1.1), "Anunc. Identificados", str(len(identified_sov)))
    add_card(slide, Inches(8.75), Inches(1.9), Inches(2.3), Inches(1.1), "Portais", str(len(summary.get("portal_ranking", []))))

    sov = summary.get("share_of_voice", []) or []
    identified_sov = summary.get("share_of_voice_identified", []) or [item for item in sov if not is_unknown_advertiser(item.get("advertiser"))]
    id_quality = summary.get("identification_quality", {}) or {}
    portals = summary.get("portal_ranking", []) or []
    top_adv = identified_sov[0] if identified_sov else {}
    top_portal = portals[0] if portals else {}

    add_panel(slide, Inches(0.7), Inches(3.45), Inches(5.6), Inches(1.8), "Maior anunciante identificado", [
        top_adv.get("advertiser", "Sem anunciantes identificados"),
        f"Share: {pct(top_adv.get('share_percent', 0))}",
        f"Investimento: {brl(top_adv.get('investment', 0))}",
    ])
    portal_lines = [
        top_portal.get("portal", "Sem dados"),
        f"Share: {pct(top_portal.get('share_percent', 0))}",
        f"Receita: {brl(top_portal.get('investment', 0))}",
    ]
    if id_quality.get("unknown_items"):
        portal_lines.append(f"Pendentes de identificação: {id_quality.get('unknown_items')} itens")
    add_panel(slide, Inches(6.6), Inches(3.45), Inches(5.6), Inches(1.8), "Portal líder / qualidade", portal_lines)

    # 3 EVIDÊNCIAS
    slide = new_slide(prs, "Qualificação das Evidências", "Separação entre checking, inteligência de mercado e notícias", LIGHT)
    add_card(slide, Inches(0.7), Inches(1.9), Inches(2.45), Inches(1.1), "Detectados", str(summary.get("total_detected_items", 0)))
    add_card(slide, Inches(3.35), Inches(1.9), Inches(2.45), Inches(1.1), "Auditáveis", str(summary.get("total_checking_ready", 0)))
    add_card(slide, Inches(6.0), Inches(1.9), Inches(2.45), Inches(1.1), "Revisão", str(summary.get("total_checking_review", 0)))
    add_card(slide, Inches(8.65), Inches(1.9), Inches(2.45), Inches(1.1), "Notícias", str(summary.get("total_news_candidates", 0)))
    add_panel(slide, Inches(0.8), Inches(3.55), Inches(5.7), Inches(2.5), "Critério operacional", [
        "Auditável: publicidade confirmada com evidência preservada.",
        "Mercado: itens úteis para leitura competitiva e investimento estimado.",
        "Notícia candidata: conteúdo editorial separado do checking publicitário.",
    ])
    add_panel(slide, Inches(6.8), Inches(3.55), Inches(5.5), Inches(2.5), "Base preservada", [
        f"Evidências preservadas: {summary.get('total_preserved_evidence', 0)}",
        f"Rejeitados para checking: {summary.get('total_checking_rejected', 0)}",
        "Itens não aprovados para checking não são descartados automaticamente.",
    ])

    # 4 SNAPSHOT
    slide = new_slide(prs, "Market Snapshot", "Leitura rápida de mercado, oportunidade e concentração", LIGHT)
    roles = market.get("market_roles", {}) or {}
    add_panel(slide, Inches(0.8), Inches(2.0), Inches(5.7), Inches(3.5), "Estrutura do mercado", [
        f"Tipo: {market.get('market_type', 'Sem dados')}",
        f"Líder: {roles.get('leader', '—')}",
        f"Desafiantes: {', '.join(roles.get('challengers', [])[:3]) or '—'}",
    ])
    add_panel(slide, Inches(6.8), Inches(2.0), Inches(5.5), Inches(3.5), "Oportunidades", market.get("opportunities", [])[:4])

    # 4 DIAGNÓSTICO EXECUTIVO
    slide = new_slide(prs, "Diagnóstico Executivo", "Leitura estratégica automática do cenário atual")

    market = summary.get("market_analysis", {}) or {}
    insights = market.get("insights", [])

    # Destaque principal (headline)
    headline = insights[0] if insights else "Cenário competitivo identificado com base nos dados monitorados."

    add_panel(
        slide,
        Inches(0.8),
        Inches(2.0),
        Inches(11.5),
        Inches(1.5),
        "Leitura principal",
        [headline],
    )

    # Complementos
    add_panel(
        slide,
        Inches(0.8),
        Inches(3.7),
        Inches(5.7),
        Inches(2.5),
        "Pontos de atenção",
        insights[1:4] if len(insights) > 1 else ["Sem pontos críticos identificados."],
    )

    add_panel(
        slide,
        Inches(6.8),
        Inches(3.7),
        Inches(5.5),
        Inches(2.5),
        "Implicação estratégica",
        [
            "O posicionamento atual indica oportunidades de otimização de presença.",
            "A dinâmica competitiva permite ganho de share com estratégia direcionada.",
        ],
    )


    # 5 OPORTUNIDADE COMERCIAL
    slide = new_slide(prs, "Oportunidade de Mercado", "Onde agir para ganhar participação com eficiência", LIGHT)

    opportunities = market.get("opportunities", [])

    add_panel(
        slide,
        Inches(0.8),
        Inches(2.0),
        Inches(5.7),
        Inches(3.5),
        "Oportunidades identificadas",
        opportunities if opportunities else ["Nenhuma oportunidade clara identificada automaticamente."],
    )

    # Highlight automático
    if opportunities:
        destaque = opportunities[0]
    else:
        destaque = "Espaço para crescimento identificado com base na estrutura atual do mercado."

    add_panel(
        slide,
        Inches(6.8),
        Inches(2.0),
        Inches(5.5),
        Inches(3.5),
        "Recomendação direta",
        [
            destaque,
            "Atuar em canais com menor pressão competitiva tende a gerar melhor eficiência.",
            "Explorar diferenciação de presença aumenta competitividade.",
        ],
    )   

    # 4 TOP ANUNCIANTES
    slide = new_slide(prs, "Top Anunciantes", "Ranking por share de presença")
    add_bar_list(slide, "Share por anunciante identificado", identified_sov[:6], "advertiser", "share_percent", Inches(0.75), Inches(2.0), Inches(10.8), Inches(4.4))

    # 5 TOP PORTAIS
    slide = new_slide(prs, "Top Portais", "Distribuição de presença por publisher")
    add_bar_list(slide, "Share por portal", portals[:6], "portal", "share_percent", Inches(0.75), Inches(2.0), Inches(10.8), Inches(4.4))

    # 6 SEGMENTOS
    slide = new_slide(prs, "Segmentos de Mercado", "Concentração do investimento por categoria", LIGHT)
    segs = summary.get("segment_ranking", []) or []
    add_bar_list(slide, "Share por segmento", segs[:6], "segment", "share_percent", Inches(0.75), Inches(2.0), Inches(10.8), Inches(4.4))

    # 7 MAPA COMPETITIVO
    slide = new_slide(prs, "Mapa Competitivo", "Pares mais relevantes por intensidade e equilíbrio")
    comp = summary.get("competitive_map", [])[:6]
    rows = [
        [
            i + 1,
            short(c.get("advertiser_a"), 20),
            short(c.get("advertiser_b"), 20),
            c.get("shared_portals_count", 0),
            brl(c.get("combined_investment", 0)),
            f"{float(c.get('balance_score', 0)):.1f}",
            f"{float(c.get('competition_score', 0)):.1f}",
        ]
        for i, c in enumerate(comp)
    ]
    add_table(slide, "Relações competitivas", ["Pos.", "A", "B", "Portais", "Invest.", "Equil.", "Score"], rows, Inches(0.7), Inches(2.0), Inches(12), Inches(4.6))

    # 8 PRESSÃO PORTAL
    slide = new_slide(prs, "Pressão Competitiva por Portal", "Saturação competitiva por publisher", LIGHT)
    pressure = summary.get("portal_pressure_map", [])[:6]
    rows = [
        [i + 1, short(p.get("portal"), 34), p.get("advertisers_count", 0), p.get("banners", 0), brl(p.get("investment", 0)), p.get("pressure_label", "—"), f"{float(p.get('pressure_score', 0)):.1f}"]
        for i, p in enumerate(pressure)
    ]
    add_table(slide, "Intensidade de pressão", ["Pos.", "Portal", "Anunc.", "Banners", "Invest.", "Pressão", "Score"], rows, Inches(0.7), Inches(2.0), Inches(12), Inches(4.6))

    # 9 ESTRUTURA
    slide = new_slide(prs, "Estrutura Competitiva", "Papel dos principais players")
    add_panel(slide, Inches(0.8), Inches(2.0), Inches(5.7), Inches(3.6), "Papéis competitivos", [
        f"Líder: {roles.get('leader', '—')}",
        f"Desafiantes: {', '.join(roles.get('challengers', [])[:4]) or '—'}",
        f"Seguidores: {', '.join(roles.get('followers', [])[:5]) or '—'}",
        f"Nicho: {', '.join(roles.get('niche', [])[:4]) or '—'}",
    ])
    rival = summary.get("rival_summary", {}) or {}
    pair = rival.get("top_rival_pair") or {}
    add_panel(slide, Inches(6.8), Inches(2.0), Inches(5.5), Inches(3.6), "Rivalidade principal", [
        f"{pair.get('advertiser_a', '—')} vs {pair.get('advertiser_b', '—')}",
        f"Score: {pair.get('competition_score', '—')}",
        f"Equilíbrio: {pair.get('balance_score', '—')}",
    ])

    # 10 DEPENDÊNCIA
    slide = new_slide(prs, "Dependência por Portal", "Risco de concentração por anunciante", LIGHT)
    deps = market.get("portal_dependency", [])[:7]
    rows = [[short(d.get("advertiser"), 24), short(d.get("main_portal"), 36), pct(d.get("dependency", 0)), d.get("risk", "—")] for d in deps]
    add_table(slide, "Dependência de canal", ["Anunciante", "Portal principal", "Dependência", "Risco"], rows, Inches(0.8), Inches(2.0), Inches(11.7), Inches(4.5))

    # 11 INSIGHTS
    slide = new_slide(prs, "Insights e Alertas", "Síntese interpretativa para tomada de decisão")
    add_panel(slide, Inches(0.8), Inches(2.0), Inches(5.8), Inches(3.9), "Insights", market.get("insights", [])[:5])
    add_panel(slide, Inches(6.9), Inches(2.0), Inches(5.4), Inches(3.9), "Alertas", market.get("alerts", [])[:5] or ["Sem alertas críticos."])

    # 12 RECOMENDAÇÕES
    slide = new_slide(prs, "Recomendações Estratégicas", "Ações sugeridas para ganho de eficiência e share", LIGHT)
    add_bullets(slide, "Recomendações", market.get("recommendations", [])[:6])

    # =========================================
    # TENDÊNCIAS COMPETITIVAS
    # =========================================

    timeline_analysis = summary.get("timeline_analysis", {}) or {}
    timeline_points = summary.get("timeline", []) or []

    if timeline_analysis and timeline_analysis.get("insights"):
        slide = new_slide(
            prs,
            "Tendências Competitivas",
            "Movimentações recentes identificadas no mercado monitorado",
            LIGHT,
        )

        deltas = timeline_analysis.get("deltas", {}) or {}
        insights = timeline_analysis.get("insights", []) or []

        investment_delta = float(deltas.get("investment_delta", 0) or 0)
        share_delta = float(deltas.get("share_delta", 0) or 0)

        current_leader = deltas.get("current_leader", "—")
        previous_leader = deltas.get("previous_leader", "—")

        # Card 1 — Variação de investimento
        add_card(
            slide,
            Inches(0.8),
            Inches(1.95),
            Inches(3.5),
            Inches(1.25),
            "Variação de investimento",
            f"{'+' if investment_delta > 0 else ''}{brl(investment_delta)}",
        )

        # Card 2 — Variação de share
        add_card(
            slide,
            Inches(4.75),
            Inches(1.95),
            Inches(3.5),
            Inches(1.25),
            "Variação do share líder",
            f"{'+' if share_delta > 0 else ''}{share_delta:.2f} p.p.",
        )

        # Card 3 — Líder atual
        add_card(
            slide,
            Inches(8.7),
            Inches(1.95),
            Inches(3.5),
            Inches(1.25),
            "Líder atual",
            short(current_leader, 22),
        )

        # Painel de leitura executiva
        add_panel(
            slide,
            Inches(0.8),
            Inches(3.65),
            Inches(5.75),
            Inches(2.45),
            "Leitura temporal",
            insights[:4],
        )

        # Painel de implicação estratégica
        if current_leader != previous_leader:
            strategic_note = [
                f"Houve troca de liderança: {previous_leader} perdeu posição para {current_leader}.",
                "Recomenda-se avaliar os canais onde ocorreu a virada competitiva.",
                "A mudança pode indicar reposicionamento de verba ou ampliação de presença.",
            ]
        elif investment_delta > 0:
            strategic_note = [
                f"{current_leader} manteve a liderança com expansão do investimento monitorado.",
                "O movimento sugere aumento de pressão competitiva no curto prazo.",
                "Recomenda-se monitorar frequência, portais e share por segmento.",
            ]
        elif investment_delta < 0:
            strategic_note = [
                f"{current_leader} manteve a liderança, mas com retração no investimento monitorado.",
                "A queda pode abrir oportunidade para avanço de concorrentes.",
                "Recomenda-se observar portais com menor saturação.",
            ]
        else:
            strategic_note = [
                "O cenário permaneceu estável entre os snapshots comparados.",
                "A estabilidade indica baixa movimentação competitiva no período.",
                "Recomenda-se ampliar a janela temporal para leitura mais precisa.",
            ]

        add_panel(
            slide,
            Inches(6.85),
            Inches(3.65),
            Inches(5.45),
            Inches(2.45),
            "Implicação estratégica",
            strategic_note,
        )

    # 15 HISTÓRICO TEMPORAL
    timeline = summary.get("timeline", []) or []
    slide = new_slide(
        prs,
        "Histórico Temporal",
        "Evolução recente do cenário monitorado",
        LIGHT,
    )

    if len(timeline) == 1:
        timeline = timeline * 2

    rows = [
        [
            str(item.get("created_at", ""))[:16],
            short(item.get("top_advertiser", "N/D"), 24),
            f'{item.get("top_advertiser_share", 0)}%',
            brl(item.get("total_investment", 0)),
            str(item.get("total_banners", 0)),
        ]
        for item in timeline[-5:]
    ]

    # =========================
    # TABELA (mais compacta)
    # =========================
    shape = slide.shapes.add_table(
        len(rows) + 1,
        5,
        Inches(0.65),
        Inches(1.75),     # sobe um pouco
        Inches(12.0),
        Inches(1.55),     # reduz altura total
    )

    table = shape.table
    headers = ["Data", "Líder", "Share", "Investimento", "Anúncios"]

    for c, header in enumerate(headers):
        table.cell(0, c).text = header

    for r_idx, row in enumerate(rows, start=1):
        for c_idx, value in enumerate(row):
            table.cell(r_idx, c_idx).text = str(value)

    # linhas mais compactas
    for i in range(len(rows) + 1):
        table.rows[i].height = Inches(0.24)

    # =========================
    # GRÁFICO (bem abaixo da tabela)
    # =========================
    chart_path = generate_timeline_chart(timeline)

    if chart_path:
        slide.shapes.add_picture(
            chart_path,
            Inches(0.7),
            Inches(3.65),   # antes 3.0 / 4.45 → este é o equilíbrio
            width=Inches(11.3),
            height=Inches(2.0),
        )
    
    # 16 ENCERRAMENTO
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide, WHITE)
    add_header(slide)
    band = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, Inches(1.2), Inches(2.0), Inches(10.8), Inches(2.1))
    band.fill.solid()
    band.fill.fore_color.rgb = RED
    band.line.fill.background()
    add_text(slide, Inches(1.5), Inches(2.55), Inches(10.2), Inches(0.5), "TV Fiscal WebMonitor", 30, True, WHITE, PP_ALIGN.CENTER)
    add_text(slide, Inches(1.5), Inches(3.15), Inches(10.2), Inches(0.5), "Inteligência, monitoramento e estratégia de mídia", 17, False, WHITE, PP_ALIGN.CENTER)

    prs.save(filename)