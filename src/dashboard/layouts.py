"""Layouts das paginas do dashboard Tesouro Direto WX.

Design system: Financial Intelligence (dark editorial inspirado em Bloomberg).
Estilos definidos em src/dashboard/assets/style.css.
"""

import dash_bootstrap_components as dbc
from dash import dash_table, dcc, html

# === Mapa de nomes amigaveis para familias ===
NOMES_FAMILIA = {
    "SELIC": "Tesouro Selic",
    "PRE": "Tesouro Prefixado",
    "PRE_JS": "Prefixado c/ Juros",
    "IPCA": "Tesouro IPCA+",
    "IPCA_JS": "IPCA+ c/ Juros",
    "IGPM_JS": "IGPM+ c/ Juros",
    "EDUCA": "Tesouro Educa+",
    "RENDA": "Tesouro Renda+",
}


# =============================================================================
# NAVBAR
# =============================================================================

def navbar():
    """Navbar customizada com logo, brand e links."""
    nav_links = html.Ul(
        [
            html.Li(dcc.Link("Ranking", href="/", className="tdwx-nav-link")),
            html.Li(dcc.Link("Series", href="/series", className="tdwx-nav-link")),
            html.Li(
                dcc.Link(
                    "Melhor Titulo do Dia",
                    href="/calculadora",
                    className="tdwx-nav-link",
                )
            ),
            html.Li(
                dcc.Link(
                    "Titulo Individual", href="/titulo", className="tdwx-nav-link"
                )
            ),
            html.Li(dcc.Link("Guia", href="/guia", className="tdwx-nav-link")),
        ],
        className="tdwx-nav-links",
        id="tdwx-nav-links",
    )

    return html.Nav(
        html.Div(
            [
                dcc.Link(
                    [
                        html.Div("TD", className="tdwx-logo"),
                        html.Span("Tesouro Direto WX", className="tdwx-brand-text"),
                    ],
                    href="/",
                    className="tdwx-brand",
                ),
                nav_links,
                html.Button(
                    "☰",
                    id="tdwx-hamburger-btn",
                    className="tdwx-hamburger",
                    n_clicks=0,
                    **{"aria-label": "Abrir menu"},
                ),
            ],
            className="tdwx-navbar-inner",
        ),
        className="tdwx-navbar",
    )


# =============================================================================
# STATUS BAR (substitui metadados_card)
# =============================================================================

def status_bar(
    data_atualizacao: str,
    total_titulos: int,
    total_registros: int,
    info_ingestao: dict | None = None,
):
    """Barra fina abaixo da navbar com metadados em linha."""
    from datetime import date, datetime

    items = [
        html.Div(
            [
                html.Span("📊 ", style={"marginRight": "4px"}),
                html.Strong(f"{total_titulos}"),
                html.Span(" titulos analisados"),
            ],
            className="tdwx-status-item",
        ),
        html.Div(
            [
                html.Span("📅 ", style={"marginRight": "4px"}),
                html.Span("Dados: "),
                html.Strong(data_atualizacao),
            ],
            className="tdwx-status-item",
        ),
        html.Div(
            [
                html.Span("📚 ", style={"marginRight": "4px"}),
                html.Strong(f"{total_registros:,}".replace(",", ".")),
                html.Span(" registros"),
            ],
            className="tdwx-status-item",
        ),
    ]

    # Status de ingestao
    if info_ingestao and info_ingestao.get("data_ingestao"):
        data_ing = info_ingestao["data_ingestao"]
        metodo = info_ingestao.get("metodo", "")
        try:
            dt_ing = datetime.fromisoformat(data_ing).date()
            dias = (date.today() - dt_ing).days
            if dias == 0:
                cor_class = ""
            elif dias == 1:
                cor_class = "warning"
            else:
                cor_class = "danger"
        except (ValueError, TypeError):
            cor_class = "warning"

        items.append(
            html.Div(
                [
                    html.Span(className=f"tdwx-status-dot {cor_class}"),
                    html.Span("Ingestao: "),
                    html.Strong(data_ing),
                    html.Span(f" via {metodo}" if metodo else ""),
                ],
                className="tdwx-status-item",
            )
        )

    return html.Div(
        html.Div(items, className="tdwx-status-inner"),
        className="tdwx-status-bar",
    )


# =============================================================================
# COMPONENTE: SUMMARY CARD
# =============================================================================

def summary_card(
    label: str, value: str, meta: str = "", variant: str = ""
) -> html.Div:
    """Card de resumo (cards no topo da pagina ranking)."""
    return html.Div(
        [
            html.P(label, className="tdwx-summary-label"),
            html.P(value, className="tdwx-summary-value"),
            html.P(meta, className="tdwx-summary-meta") if meta else None,
        ],
        className=f"tdwx-summary-card {variant}",
    )


# =============================================================================
# PAGINA RANKING
# =============================================================================

def pagina_ranking(familias: list[str], summary_stats: dict | None = None):
    """Layout da pagina de ranking."""
    opcoes_familia = [{"label": "Todas as familias", "value": "TODAS"}] + [
        {"label": NOMES_FAMILIA.get(f, f), "value": f} for f in sorted(familias)
    ]

    summary_stats = summary_stats or {}
    summary_section = html.Div(
        [
            summary_card(
                "Melhor Score",
                summary_stats.get("melhor_score_valor", "—"),
                summary_stats.get("melhor_score_titulo", ""),
                "",
            ),
            summary_card(
                "Maior Taxa",
                summary_stats.get("maior_taxa_valor", "—"),
                summary_stats.get("maior_taxa_titulo", ""),
                "warning",
            ),
            summary_card(
                "Melhor Liquidez",
                summary_stats.get("melhor_liquidez_valor", "—"),
                summary_stats.get("melhor_liquidez_titulo", ""),
                "info",
            ),
            summary_card(
                "Titulos Analisados",
                str(summary_stats.get("total", "—")),
                "snapshot mais recente",
                "purple",
            ),
        ],
        className="tdwx-summary-row",
    )

    filtros_section = html.Div(
        [
            html.Div(
                [
                    html.Label("Formula de Score", className="tdwx-filter-label"),
                    dcc.Dropdown(
                        id="ranking-score-dropdown",
                        options=[
                            {"label": "Score A (base)", "value": "score_a"},
                            {
                                "label": "Score B (ajustado por risco)",
                                "value": "score_b",
                            },
                            {
                                "label": "Score C (curva NSS)",
                                "value": "score_c",
                            },
                        ],
                        value="score_a",
                        clearable=False,
                    ),
                ]
            ),
            html.Div(
                [
                    html.Label("Familia", className="tdwx-filter-label"),
                    dcc.Dropdown(
                        id="ranking-familia-dropdown",
                        options=opcoes_familia,
                        value="TODAS",
                        clearable=False,
                    ),
                ]
            ),
            html.Div(
                [
                    html.Label("Ordenar por", className="tdwx-filter-label"),
                    dcc.Dropdown(
                        id="ranking-ordenar-dropdown",
                        options=[
                            {"label": "Score selecionado", "value": "score"},
                            {"label": "Carry", "value": "carry"},
                            {
                                "label": "Valor Relativo (z-score)",
                                "value": "rv_zscore",
                            },
                            {"label": "Taxa Compra", "value": "taxa_compra_manha"},
                        ],
                        value="score",
                        clearable=False,
                    ),
                ]
            ),
        ],
        className="tdwx-filter-row",
    )

    tabela = dash_table.DataTable(
        id="ranking-tabela",
        page_size=20,
        sort_action="native",
        tooltip_delay=0,
        tooltip_duration=None,
        style_table={"overflowX": "auto"},
        style_cell={
            "textAlign": "left",
            "padding": "12px 10px",
            "fontSize": "12px",
            "fontFamily": "JetBrains Mono, monospace",
            "backgroundColor": "#1A2736",
            "color": "#E8ECF1",
            "border": "1px solid #2A3A4A",
        },
        style_header={
            "backgroundColor": "#0F1923",
            "color": "#8899AA",
            "fontWeight": "500",
            "textTransform": "uppercase",
            "letterSpacing": "0.5px",
            "fontSize": "11px",
            "fontFamily": "DM Sans, sans-serif",
            "border": "1px solid #2A3A4A",
        },
        style_data={"backgroundColor": "#1A2736", "color": "#E8ECF1"},
        style_data_conditional=[
            {
                "if": {"row_index": "odd"},
                "backgroundColor": "#1E2F3F",
            },
            {
                "if": {"state": "active"},
                "backgroundColor": "#223345",
                "border": "1px solid #00D4AA",
            },
            {
                "if": {"filter_query": "{score} >= 0.6", "column_id": "score"},
                "color": "#00D4AA",
                "fontWeight": "bold",
            },
            {
                "if": {"filter_query": "{score} < 0.3", "column_id": "score"},
                "color": "#FF5555",
            },
            {
                "if": {
                    "filter_query": '{taxa_pp_12m_str} contains "+"',
                    "column_id": "taxa_pp_12m_str",
                },
                "color": "#4DA6FF",
                "fontWeight": "bold",
            },
            {
                "if": {
                    "filter_query": '{taxa_pp_12m_str} contains "-"',
                    "column_id": "taxa_pp_12m_str",
                },
                "color": "#8899AA",
            },
            {
                "if": {"filter_query": '{celula_pequena_str} = "✓"'},
                "fontStyle": "italic",
                "color": "#5A6B7C",
            },
        ],
    )

    return html.Div(
        [
            html.Div(
                [
                    html.H1(
                        "Ranking de Oportunidades", className="tdwx-page-title"
                    ),
                    html.P(
                        "Análise multifatorial dos títulos disponíveis no Tesouro Direto",
                        className="tdwx-page-subtitle",
                    ),
                ],
                className="tdwx-page-header",
            ),
            summary_section,
            filtros_section,
            html.Div(
                dcc.Graph(id="ranking-bar-chart"),
                className="tdwx-chart-wrapper",
            ),
            html.H2(
                "Detalhamento",
                style={
                    "fontSize": "18px",
                    "fontWeight": "700",
                    "color": "#E8ECF1",
                    "margin": "32px 0 16px 0",
                },
            ),
            tabela,
        ],
        className="tdwx-container",
    )


# =============================================================================
# PAGINA SERIES TEMPORAIS
# =============================================================================

def pagina_series(familias: list[str], titulos: list[str], grupos: list[str]):
    """Layout da pagina de series temporais."""
    opcoes_familia = [
        {"label": NOMES_FAMILIA.get(f, f), "value": f} for f in sorted(familias)
    ]
    opcoes_titulos = [{"label": t, "value": t} for t in sorted(titulos)]
    opcoes_grupos = [{"label": g, "value": g} for g in sorted(grupos)]

    return html.Div(
        [
            html.Div(
                [
                    html.H1("Séries Temporais", className="tdwx-page-title"),
                    html.P(
                        "Evolução histórica das taxas e curvas de juros",
                        className="tdwx-page-subtitle",
                    ),
                ],
                className="tdwx-page-header",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Família", className="tdwx-filter-label"),
                            dcc.Dropdown(
                                id="series-familia-dropdown",
                                options=opcoes_familia,
                                value=opcoes_familia[0]["value"]
                                if opcoes_familia
                                else None,
                                clearable=False,
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.Label(
                                "Títulos para comparar", className="tdwx-filter-label"
                            ),
                            dcc.Dropdown(
                                id="series-titulos-dropdown",
                                options=opcoes_titulos,
                                multi=True,
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.Label("Período", className="tdwx-filter-label"),
                            dcc.Dropdown(
                                id="series-periodo-dropdown",
                                options=[
                                    {"label": "1 ano", "value": 365},
                                    {"label": "3 anos", "value": 1095},
                                    {"label": "5 anos", "value": 1825},
                                    {"label": "Todo histórico", "value": 0},
                                ],
                                value=1095,
                                clearable=False,
                            ),
                        ]
                    ),
                ],
                className="tdwx-filter-row",
            ),
            html.Div(
                dcc.Graph(id="series-line-chart"),
                className="tdwx-chart-wrapper",
            ),
            html.H2(
                "Curva Teórica Nelson-Siegel-Svensson",
                style={
                    "fontSize": "20px",
                    "fontWeight": "700",
                    "color": "#E8ECF1",
                    "margin": "40px 0 8px 0",
                },
            ),
            html.P(
                "Estrutura a termo ajustada por grupo analítico",
                className="tdwx-page-subtitle",
                style={"marginBottom": "16px"},
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label(
                                "Grupo Analítico", className="tdwx-filter-label"
                            ),
                            dcc.Dropdown(
                                id="curva-grupo-dropdown",
                                options=opcoes_grupos,
                                value=opcoes_grupos[0]["value"]
                                if opcoes_grupos
                                else None,
                                clearable=False,
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.Label("Exibir", className="tdwx-filter-label"),
                            dcc.Checklist(
                                id="curva-opcoes-checklist",
                                options=[
                                    {"label": " Curva teórica", "value": "curva"},
                                    {"label": " Pontos observados", "value": "pontos"},
                                ],
                                value=["curva", "pontos"],
                                inline=True,
                                className="tdwx-radio-group",
                                style={"display": "flex", "gap": "16px"},
                            ),
                        ]
                    ),
                    html.Div(),
                ],
                className="tdwx-filter-row",
            ),
            html.Div(
                dcc.Graph(id="curva-nss-chart"),
                className="tdwx-chart-wrapper",
            ),
        ],
        className="tdwx-container",
    )


# =============================================================================
# PAGINA TITULO INDIVIDUAL
# =============================================================================

def pagina_titulo(titulos: list[str]):
    """Layout da pagina de detalhamento individual."""
    opcoes = [{"label": t, "value": t} for t in sorted(titulos)]

    return html.Div(
        [
            html.Div(
                [
                    html.H1("Título Individual", className="tdwx-page-title"),
                    html.P(
                        "Análise detalhada de um título específico",
                        className="tdwx-page-subtitle",
                    ),
                ],
                className="tdwx-page-header",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Selecione um título", className="tdwx-filter-label"),
                            dcc.Dropdown(
                                id="titulo-dropdown",
                                options=opcoes,
                                value=opcoes[0]["value"] if opcoes else None,
                                clearable=False,
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.Label("Período do gráfico", className="tdwx-filter-label"),
                            dcc.Dropdown(
                                id="titulo-periodo-dropdown",
                                options=[
                                    {"label": "30 dias", "value": 30},
                                    {"label": "6 meses", "value": 180},
                                    {"label": "1 ano", "value": 365},
                                    {"label": "5 anos", "value": 1825},
                                    {"label": "Máximo", "value": 0},
                                ],
                                value=365,
                                clearable=False,
                            ),
                        ]
                    ),
                    html.Div(),
                ],
                className="tdwx-filter-row",
            ),
            html.Div(id="titulo-stats-cards", className="mb-3"),
            html.Div(
                [
                    html.Div(id="titulo-card-info"),
                    html.Div(
                        dcc.Graph(id="titulo-taxa-chart"),
                        className="tdwx-chart-wrapper",
                    ),
                ],
                className="tdwx-titulo-grid",
            ),
            html.Div(
                [
                    html.Div(
                        dcc.Graph(id="titulo-pu-chart"),
                        className="tdwx-chart-wrapper",
                    ),
                    html.Div(
                        dcc.Graph(id="titulo-spread-chart"),
                        className="tdwx-chart-wrapper",
                    ),
                ],
                className="tdwx-charts-grid",
            ),
        ],
        className="tdwx-container",
    )


# =============================================================================
# PAGINA CALCULADORA
# =============================================================================

def pagina_calculadora():
    """Layout da pagina 'Melhor Titulo do Dia'."""
    return html.Div(
        [
            html.Div(
                [
                    html.H1(
                        ["🏆 Melhor Título do Dia"], className="tdwx-page-title"
                    ),
                    html.P(
                        "Responda 3 perguntas e descubra qual título do Tesouro "
                        "Direto melhor se encaixa no seu objetivo hoje.",
                        className="tdwx-page-subtitle",
                    ),
                ],
                className="tdwx-page-header",
            ),
            html.Div(
                [
                    # Pergunta 1
                    html.Div(
                        [
                            html.Div("🎯", className="tdwx-question-icon"),
                            html.H3("Objetivo", className="tdwx-question-title"),
                            html.P(
                                "Qual seu objetivo?",
                                className="tdwx-question-subtitle",
                            ),
                            dcc.Dropdown(
                                id="calc-objetivo-dropdown",
                                options=[
                                    {
                                        "label": "Reserva de emergência",
                                        "value": "reserva",
                                    },
                                    {
                                        "label": "Curto prazo (até 2 anos)",
                                        "value": "curto",
                                    },
                                    {
                                        "label": "Médio prazo (2-5 anos)",
                                        "value": "medio",
                                    },
                                    {
                                        "label": "Longo prazo (5-15 anos)",
                                        "value": "longo",
                                    },
                                    {
                                        "label": "Aposentadoria (15+ anos)",
                                        "value": "aposentadoria",
                                    },
                                ],
                                value="medio",
                                clearable=False,
                            ),
                        ],
                        className="tdwx-question-card",
                    ),
                    # Pergunta 2
                    html.Div(
                        [
                            html.Div("📊", className="tdwx-question-icon"),
                            html.H3(
                                "Tolerância a risco", className="tdwx-question-title"
                            ),
                            html.P(
                                "Aceita oscilação no caminho?",
                                className="tdwx-question-subtitle",
                            ),
                            dcc.RadioItems(
                                id="calc-oscilacao-radio",
                                options=[
                                    {
                                        "label": " Não (conservador)",
                                        "value": "conservador",
                                    },
                                    {
                                        "label": " Um pouco (moderado)",
                                        "value": "moderado",
                                    },
                                    {
                                        "label": " Sim (arrojado)",
                                        "value": "arrojado",
                                    },
                                ],
                                value="moderado",
                                className="tdwx-radio-group",
                            ),
                        ],
                        className="tdwx-question-card",
                    ),
                    # Pergunta 3
                    html.Div(
                        [
                            html.Div("💰", className="tdwx-question-icon"),
                            html.H3(
                                "Renda periódica", className="tdwx-question-title"
                            ),
                            html.P(
                                "Precisa de renda no caminho?",
                                className="tdwx-question-subtitle",
                            ),
                            dcc.RadioItems(
                                id="calc-renda-radio",
                                options=[
                                    {"label": " Não", "value": "nao"},
                                    {
                                        "label": " Sim (juros semestrais)",
                                        "value": "sim",
                                    },
                                ],
                                value="nao",
                                className="tdwx-radio-group",
                            ),
                        ],
                        className="tdwx-question-card",
                    ),
                ],
                className="tdwx-question-grid",
            ),
            html.Div(id="calc-resultado"),
        ],
        className="tdwx-container",
    )


# =============================================================================
# PAGINA GUIA
# =============================================================================

def _accordion_titulo(label: str, sigla: str, descricao: str, indexador: str):
    """Helper para criar item de accordion para um tipo de titulo."""
    return dbc.AccordionItem(
        [
            html.P([html.Strong("Sigla técnica: "), sigla]),
            html.P([html.Strong("Indexador: "), indexador]),
            html.P(descricao),
        ],
        title=label,
    )


def pagina_guia():
    """Layout da pagina educativa 'Entenda os Titulos'."""
    return html.Div(
        [
            html.Div(
                [
                    html.H1("Entenda os Títulos", className="tdwx-page-title"),
                    html.P(
                        "Guia rápido sobre o que são os títulos do Tesouro Direto, "
                        "como funcionam e o que cada métrica significa.",
                        className="tdwx-page-subtitle",
                    ),
                ],
                className="tdwx-page-header",
            ),
            dbc.Accordion(
                [
                    dbc.AccordionItem(
                        [
                            html.P(
                                "O Tesouro Direto é um programa do governo federal que "
                                "permite a qualquer pessoa física emprestar dinheiro "
                                "ao Tesouro Nacional. Em troca, o governo paga juros "
                                "sobre o valor emprestado, com regras (taxa, prazo e "
                                "indexador) definidas no momento da compra."
                            ),
                            html.P(
                                "É considerado o investimento de menor risco do mercado "
                                "brasileiro, já que tem garantia do governo federal. "
                                "Também é democrático: pode comprar com pouco dinheiro "
                                "(a partir de cerca de R$ 30) e não depende de banco "
                                "específico."
                            ),
                            html.P(
                                "Os títulos podem ser usados para diferentes objetivos: "
                                "reserva de emergência, projetos de médio prazo, "
                                "aposentadoria ou educação dos filhos."
                            ),
                        ],
                        title="📘 O que é Tesouro Direto?",
                    ),
                    dbc.AccordionItem(
                        [
                            html.P(
                                "Cada família de título tem características próprias. "
                                "Veja abaixo as principais:",
                                className="text-muted",
                            ),
                            dbc.Accordion(
                                [
                                    _accordion_titulo(
                                        "Tesouro Selic",
                                        "LFT",
                                        "Acompanha a taxa Selic, com baixíssima oscilação "
                                        "diária. Ideal para reserva de emergência. "
                                        "A rentabilidade segue a taxa básica de juros do país.",
                                        "Selic",
                                    ),
                                    _accordion_titulo(
                                        "Tesouro Prefixado",
                                        "LTN",
                                        "Você sabe exatamente quanto vai receber no vencimento. "
                                        "A taxa fica travada no momento da compra. Bom quando "
                                        "você acredita que os juros vão cair no futuro.",
                                        "Nenhum (taxa fixa)",
                                    ),
                                    _accordion_titulo(
                                        "Tesouro Prefixado com Juros Semestrais",
                                        "NTN-F",
                                        "Igual ao Prefixado, mas paga cupom (juros) a cada "
                                        "6 meses. Bom para quem quer renda periódica sem "
                                        "esperar o vencimento.",
                                        "Nenhum (taxa fixa)",
                                    ),
                                    _accordion_titulo(
                                        "Tesouro IPCA+",
                                        "NTN-B Principal",
                                        "Paga IPCA + uma taxa real fixa. Protege seu poder "
                                        "de compra contra a inflação, além de garantir um "
                                        "ganho real (acima da inflação).",
                                        "IPCA",
                                    ),
                                    _accordion_titulo(
                                        "Tesouro IPCA+ com Juros Semestrais",
                                        "NTN-B",
                                        "Igual ao IPCA+, mas com cupom semestral.",
                                        "IPCA",
                                    ),
                                    _accordion_titulo(
                                        "Tesouro Educa+",
                                        "NTN-B Principal (variante)",
                                        "Voltado para acumular para a educação dos filhos. "
                                        "Paga IPCA + taxa real e tem cronograma específico.",
                                        "IPCA",
                                    ),
                                    _accordion_titulo(
                                        "Tesouro Renda+",
                                        "NTN-B (variante)",
                                        "Voltado para aposentadoria. Paga IPCA + taxa real, "
                                        "e na fase de pagamento entrega uma renda mensal por "
                                        "20 anos.",
                                        "IPCA",
                                    ),
                                ],
                                start_collapsed=True,
                                always_open=False,
                            ),
                        ],
                        title="📚 Tipos de título",
                    ),
                    dbc.AccordionItem(
                        [
                            html.H6("Taxa de custódia B3"),
                            html.P(
                                "0,20% ao ano sobre o valor investido. Cobrada "
                                "semestralmente. O Tesouro Selic é isento dessa taxa "
                                "até R$ 10.000 investidos."
                            ),
                            html.H6("Imposto de Renda (regressivo)"),
                            html.Ul(
                                [
                                    html.Li("Até 180 dias: 22,5%"),
                                    html.Li("De 181 a 360 dias: 20,0%"),
                                    html.Li("De 361 a 720 dias: 17,5%"),
                                    html.Li("Acima de 720 dias: 15,0%"),
                                ]
                            ),
                            html.P(
                                "O IR incide somente sobre os rendimentos, não sobre "
                                "o valor investido."
                            ),
                            html.H6("IOF"),
                            html.P(
                                "Cobrado apenas se você vender antes de 30 dias da compra. "
                                "Começa em 96% sobre o ganho no primeiro dia e diminui "
                                "progressivamente até zero no 30º dia."
                            ),
                        ],
                        title="💰 Custos e tributação",
                    ),
                    dbc.AccordionItem(
                        [
                            html.P(
                                "O dashboard usa várias métricas para ranquear "
                                "oportunidades:",
                                className="text-muted",
                            ),
                            html.H6("Score A (base)"),
                            html.P(
                                "Nota de 0 a 1 que combina Carry (40%), Valor Relativo "
                                "(40%) e Liquidez (20%)."
                            ),
                            html.H6("Score B (ajustado por risco)"),
                            html.P(
                                "Igual ao Score A, mas penaliza títulos de prazo muito "
                                "longo (que oscilam mais)."
                            ),
                            html.H6("Score C (resíduo de curva)"),
                            html.P(
                                "Score mais sofisticado: ajusta uma curva teórica de juros "
                                "(Nelson-Siegel-Svensson) e aponta títulos que pagam mais "
                                "do que a curva sugere."
                            ),
                            html.H6("Carry"),
                            html.P(
                                "Quanto a taxa do título está acima da mediana do seu grupo "
                                "de pares. Positivo = paga mais que a média."
                            ),
                            html.H6("Valor Relativo (z-score)"),
                            html.P(
                                "Mede quantos desvios-padrão a taxa está acima ou abaixo "
                                "da média do grupo."
                            ),
                            html.H6("Liquidez"),
                            html.P(
                                "Indicador de 0 a 1 que mede a facilidade de comprar e "
                                "vender o título. Baseado no spread entre compra e venda."
                            ),
                            html.H6("Bucket de prazo"),
                            html.P(
                                "Curto (até 2 anos), Intermediário (2-5 anos), "
                                "Longo (5-15 anos), Ultralongo (acima de 15 anos)."
                            ),
                        ],
                        title="📊 Métricas do dashboard",
                    ),
                    dbc.AccordionItem(
                        [
                            html.P(
                                "Marcação a mercado é o nome dado ao processo de "
                                "atualização diária do preço do seu título. Mesmo que "
                                "você não venda, o valor de mercado oscila todos os dias "
                                "conforme as expectativas de juros mudam."
                            ),
                            html.H6("Como funciona"),
                            html.P(
                                "Quando você compra um título prefixado a 12% a.a. e "
                                "depois os juros do mercado caem para 10%, o seu título "
                                "passa a valer mais no mercado. O contrário também vale: "
                                "se os juros subirem, seu título passa a valer menos."
                            ),
                            html.H6("Quando isso importa"),
                            html.P(
                                "Se você levar o título até o vencimento, sempre recebe "
                                "a taxa contratada na compra. A oscilação só importa se "
                                "você decidir vender antes."
                            ),
                        ],
                        title="📈 Marcação a mercado",
                    ),
                ],
                start_collapsed=True,
                always_open=False,
            ),
        ],
        className="tdwx-container",
    )
