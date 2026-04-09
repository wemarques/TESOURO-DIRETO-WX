"""Layouts das paginas do dashboard Tesouro Direto WX."""

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


def navbar():
    """Barra de navegacao superior."""
    return dbc.Navbar(
        dbc.Container(
            [
                dbc.NavbarBrand("Tesouro Direto WX", className="fw-bold"),
                dbc.Nav(
                    [
                        dbc.NavItem(dbc.NavLink("Ranking", href="/", active="exact")),
                        dbc.NavItem(
                            dbc.NavLink("Series", href="/series", active="exact")
                        ),
                        dbc.NavItem(
                            dbc.NavLink(
                                "Melhor Titulo do Dia", href="/calculadora", active="exact"
                            )
                        ),
                        dbc.NavItem(
                            dbc.NavLink("Titulo Individual", href="/titulo", active="exact")
                        ),
                        dbc.NavItem(
                            dbc.NavLink("Guia", href="/guia", active="exact")
                        ),
                    ],
                    navbar=True,
                ),
            ],
            fluid=True,
        ),
        color="dark",
        dark=True,
        className="mb-3",
    )


def metadados_card(
    data_atualizacao: str,
    total_titulos: int,
    total_registros: int,
    info_ingestao: dict | None = None,
):
    """Card com metadados de ultima atualizacao."""
    from datetime import date, datetime

    badges = [
        dbc.Badge(
            f"Dados: {data_atualizacao}",
            color="info",
            className="me-2",
        ),
        dbc.Badge(
            f"{total_titulos} titulos ranqueados",
            color="success",
            className="me-2",
        ),
        dbc.Badge(
            f"{total_registros:,} registros historicos".replace(",", "."),
            color="secondary",
            className="me-2",
        ),
    ]

    if info_ingestao and info_ingestao.get("data_ingestao"):
        data_ing = info_ingestao["data_ingestao"]
        metodo = info_ingestao.get("metodo", "")

        try:
            dt_ing = datetime.fromisoformat(data_ing).date()
            dias = (date.today() - dt_ing).days
            if dias == 0:
                cor = "success"
            elif dias == 1:
                cor = "warning"
            else:
                cor = "danger"
        except (ValueError, TypeError):
            cor = "secondary"

        badges.append(
            dbc.Badge(
                f"Ingestao: {data_ing}",
                color=cor,
                className="me-2",
            )
        )
        if metodo:
            badges.append(
                dbc.Badge(
                    f"Via: {metodo}",
                    color="light",
                    text_color="dark",
                    className="me-2",
                )
            )

    return dbc.Card(
        dbc.CardBody(
            [
                html.H6("Metadados da Base", className="card-title text-muted"),
                html.Div(badges),
            ]
        ),
        className="mb-3",
    )


# =============================================================================
# PAGINA RANKING
# =============================================================================

def pagina_ranking(familias: list[str]):
    """Layout da pagina de ranking por familia."""
    opcoes_familia = [{"label": "Todas", "value": "TODAS"}] + [
        {"label": NOMES_FAMILIA.get(f, f), "value": f} for f in sorted(familias)
    ]

    return dbc.Container(
        [
            html.H4("Ranking de Oportunidades", className="mb-3"),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Formula de Score", className="fw-bold"),
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
                        ],
                        md=3,
                    ),
                    dbc.Col(
                        [
                            html.Label("Familia do Titulo", className="fw-bold"),
                            dcc.Dropdown(
                                id="ranking-familia-dropdown",
                                options=opcoes_familia,
                                value="TODAS",
                                clearable=False,
                            ),
                        ],
                        md=3,
                    ),
                    dbc.Col(
                        [
                            html.Label("Ordenar por", className="fw-bold"),
                            dcc.Dropdown(
                                id="ranking-ordenar-dropdown",
                                options=[
                                    {"label": "Score selecionado", "value": "score"},
                                    {"label": "Carry", "value": "carry"},
                                    {"label": "Valor Relativo (z-score)", "value": "rv_zscore"},
                                    {"label": "Taxa Compra", "value": "taxa_compra_manha"},
                                ],
                                value="score",
                                clearable=False,
                            ),
                        ],
                        md=3,
                    ),
                ],
                className="mb-3",
            ),
            dcc.Graph(id="ranking-bar-chart"),
            html.Hr(),
            html.H5("Detalhamento", className="mb-2"),
            dash_table.DataTable(
                id="ranking-tabela",
                page_size=20,
                sort_action="native",
                tooltip_delay=0,
                tooltip_duration=None,
                css=[
                    {
                        "selector": ".dash-table-tooltip",
                        "rule": (
                            "background-color: #333; color: white; "
                            "max-width: 350px; padding: 8px; "
                            "border-radius: 4px; font-size: 12px;"
                        ),
                    }
                ],
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "left", "padding": "8px", "fontSize": "13px"},
                style_header={
                    "fontWeight": "bold",
                    "backgroundColor": "#f8f9fa",
                    "textDecoration": "underline dotted",
                    "cursor": "help",
                },
                style_data_conditional=[
                    {
                        "if": {"filter_query": "{score} >= 0.6", "column_id": "score"},
                        "backgroundColor": "#d4edda",
                    },
                    {
                        "if": {"filter_query": "{score} < 0.3", "column_id": "score"},
                        "backgroundColor": "#f8d7da",
                    },
                    {
                        "if": {
                            "filter_query": '{taxa_pp_12m_str} contains "+"',
                            "column_id": "taxa_pp_12m_str",
                        },
                        "color": "#1565c0",
                        "fontWeight": "bold",
                    },
                    {
                        "if": {
                            "filter_query": '{taxa_pp_12m_str} contains "-"',
                            "column_id": "taxa_pp_12m_str",
                        },
                        "color": "#616161",
                        "fontWeight": "bold",
                    },
                    {
                        "if": {"filter_query": '{celula_pequena_str} = "✓"'},
                        "fontStyle": "italic",
                        "color": "#9e9e9e",
                    },
                ],
            ),
        ],
        fluid=True,
    )


# =============================================================================
# PAGINA SERIES TEMPORAIS
# =============================================================================

def pagina_series(familias: list[str], titulos: list[str], grupos: list[str]):
    """Layout da pagina de series temporais."""
    opcoes_familia = [{"label": NOMES_FAMILIA.get(f, f), "value": f} for f in sorted(familias)]
    opcoes_titulos = [{"label": t, "value": t} for t in sorted(titulos)]
    opcoes_grupos = [{"label": g, "value": g} for g in sorted(grupos)]

    return dbc.Container(
        [
            html.H4("Series Temporais de Taxas", className="mb-3"),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Familia", className="fw-bold"),
                            dcc.Dropdown(
                                id="series-familia-dropdown",
                                options=opcoes_familia,
                                value=opcoes_familia[0]["value"] if opcoes_familia else None,
                                clearable=False,
                            ),
                        ],
                        md=4,
                    ),
                    dbc.Col(
                        [
                            html.Label("Titulos (selecione para comparar)", className="fw-bold"),
                            dcc.Dropdown(
                                id="series-titulos-dropdown",
                                options=opcoes_titulos,
                                multi=True,
                            ),
                        ],
                        md=6,
                    ),
                    dbc.Col(
                        [
                            html.Label("Periodo", className="fw-bold"),
                            dcc.Dropdown(
                                id="series-periodo-dropdown",
                                options=[
                                    {"label": "1 ano", "value": 365},
                                    {"label": "3 anos", "value": 1095},
                                    {"label": "5 anos", "value": 1825},
                                    {"label": "Todo historico", "value": 0},
                                ],
                                value=1095,
                                clearable=False,
                            ),
                        ],
                        md=2,
                    ),
                ],
                className="mb-3",
            ),
            dcc.Graph(id="series-line-chart"),
            html.Hr(),
            html.H4("Curva Teorica Nelson-Siegel-Svensson", className="mb-3 mt-4"),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Grupo Analitico", className="fw-bold"),
                            dcc.Dropdown(
                                id="curva-grupo-dropdown",
                                options=opcoes_grupos,
                                value=opcoes_grupos[0]["value"] if opcoes_grupos else None,
                                clearable=False,
                            ),
                        ],
                        md=4,
                    ),
                    dbc.Col(
                        [
                            html.Label("Exibir", className="fw-bold"),
                            dcc.Checklist(
                                id="curva-opcoes-checklist",
                                options=[
                                    {"label": " Curva teorica", "value": "curva"},
                                    {"label": " Pontos observados", "value": "pontos"},
                                ],
                                value=["curva", "pontos"],
                                inline=True,
                                className="mt-1",
                            ),
                        ],
                        md=4,
                    ),
                ],
                className="mb-3",
            ),
            dcc.Graph(id="curva-nss-chart"),
        ],
        fluid=True,
    )


# =============================================================================
# PAGINA TITULO INDIVIDUAL
# =============================================================================

def pagina_titulo(titulos: list[str]):
    """Layout da pagina de detalhamento individual."""
    opcoes = [{"label": t, "value": t} for t in sorted(titulos)]

    return dbc.Container(
        [
            html.H4("Detalhamento por Titulo", className="mb-3"),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Selecione um titulo", className="fw-bold"),
                            dcc.Dropdown(
                                id="titulo-dropdown",
                                options=opcoes,
                                value=opcoes[0]["value"] if opcoes else None,
                                clearable=False,
                            ),
                        ],
                        md=6,
                    ),
                    dbc.Col(
                        [
                            html.Label("Periodo do grafico", className="fw-bold"),
                            dcc.Dropdown(
                                id="titulo-periodo-dropdown",
                                options=[
                                    {"label": "30 dias", "value": 30},
                                    {"label": "6 meses", "value": 180},
                                    {"label": "1 ano", "value": 365},
                                    {"label": "5 anos", "value": 1825},
                                    {"label": "Maximo", "value": 0},
                                ],
                                value=365,
                                clearable=False,
                            ),
                        ],
                        md=3,
                    ),
                ],
                className="mb-3",
            ),
            html.Div(id="titulo-stats-cards", className="mb-3"),
            dbc.Row(
                [
                    dbc.Col(dbc.Card(id="titulo-card-info"), md=4),
                    dbc.Col(dcc.Graph(id="titulo-taxa-chart"), md=8),
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(dcc.Graph(id="titulo-pu-chart"), md=6),
                    dbc.Col(dcc.Graph(id="titulo-spread-chart"), md=6),
                ],
            ),
        ],
        fluid=True,
    )


# =============================================================================
# PAGINA CALCULADORA - MELHOR TITULO DO DIA
# =============================================================================

def pagina_calculadora():
    """Layout da pagina de calculadora 'Melhor Titulo do Dia'."""
    return dbc.Container(
        [
            html.H4("Melhor Titulo do Dia", className="mb-2"),
            html.P(
                "Responda 3 perguntas e descubra qual titulo do Tesouro Direto "
                "melhor se encaixa no seu objetivo hoje.",
                className="text-muted mb-4",
            ),
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H5("Suas preferencias", className="card-title mb-3"),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        html.Label(
                                            "Qual seu objetivo?",
                                            className="fw-bold",
                                        ),
                                        dcc.Dropdown(
                                            id="calc-objetivo-dropdown",
                                            options=[
                                                {
                                                    "label": "Reserva de emergencia",
                                                    "value": "reserva",
                                                },
                                                {
                                                    "label": "Curto prazo (ate 2 anos)",
                                                    "value": "curto",
                                                },
                                                {
                                                    "label": "Medio prazo (2-5 anos)",
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
                                    md=4,
                                ),
                                dbc.Col(
                                    [
                                        html.Label(
                                            "Aceita oscilacao no caminho?",
                                            className="fw-bold",
                                        ),
                                        dcc.RadioItems(
                                            id="calc-oscilacao-radio",
                                            options=[
                                                {
                                                    "label": " Nao (conservador)",
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
                                            labelStyle={"display": "block"},
                                        ),
                                    ],
                                    md=4,
                                ),
                                dbc.Col(
                                    [
                                        html.Label(
                                            "Precisa de renda periodica?",
                                            className="fw-bold",
                                        ),
                                        dcc.RadioItems(
                                            id="calc-renda-radio",
                                            options=[
                                                {"label": " Nao", "value": "nao"},
                                                {
                                                    "label": " Sim (juros semestrais)",
                                                    "value": "sim",
                                                },
                                            ],
                                            value="nao",
                                            labelStyle={"display": "block"},
                                        ),
                                    ],
                                    md=4,
                                ),
                            ]
                        ),
                    ]
                ),
                className="mb-4",
            ),
            html.Div(id="calc-resultado"),
        ],
        fluid=True,
    )


# =============================================================================
# PAGINA GUIA - ENTENDA OS TITULOS
# =============================================================================

def _accordion_titulo(label: str, sigla: str, descricao: str, indexador: str):
    """Helper para criar item de accordion para um tipo de titulo."""
    return dbc.AccordionItem(
        [
            html.P([html.Strong("Sigla tecnica: "), sigla]),
            html.P([html.Strong("Indexador: "), indexador]),
            html.P(descricao),
        ],
        title=label,
    )


def pagina_guia():
    """Layout da pagina educativa 'Entenda os Titulos'."""
    return dbc.Container(
        [
            html.H4("Entenda os Titulos", className="mb-3"),
            html.P(
                "Guia rapido sobre o que sao os titulos do Tesouro Direto, "
                "como funcionam e o que cada metrica do dashboard significa.",
                className="text-muted mb-4",
            ),
            dbc.Accordion(
                [
                    # Secao 1
                    dbc.AccordionItem(
                        [
                            html.P(
                                "O Tesouro Direto e um programa do governo federal que "
                                "permite a qualquer pessoa fisica emprestar dinheiro ao "
                                "Tesouro Nacional. Em troca, o governo paga juros sobre "
                                "o valor emprestado, com regras (taxa, prazo e indexador) "
                                "definidas no momento da compra."
                            ),
                            html.P(
                                "E considerado o investimento de menor risco do mercado "
                                "brasileiro, ja que tem garantia do governo federal. Tambem "
                                "e democratico: pode comprar com pouco dinheiro (a partir "
                                "de cerca de R$ 30) e nao depende de banco especifico."
                            ),
                            html.P(
                                "Os titulos podem ser usados para diferentes objetivos: "
                                "reserva de emergencia, projetos de medio prazo, aposentadoria "
                                "ou educacao dos filhos. A escolha do titulo depende do prazo "
                                "do objetivo, da tolerancia a oscilacao e da necessidade ou nao "
                                "de receber renda periodica."
                            ),
                        ],
                        title="O que e Tesouro Direto?",
                    ),
                    # Secao 2
                    dbc.AccordionItem(
                        [
                            html.P(
                                "Cada familia de titulo tem caracteristicas proprias. "
                                "Veja abaixo as principais:",
                                className="text-muted mb-3",
                            ),
                            dbc.Accordion(
                                [
                                    _accordion_titulo(
                                        "Tesouro Selic",
                                        "LFT",
                                        "Acompanha a taxa Selic, com baixissima oscilacao "
                                        "diaria. Ideal para reserva de emergencia, ja que voce "
                                        "pode resgatar a qualquer momento sem grandes perdas. "
                                        "A rentabilidade segue a taxa basica de juros do pais.",
                                        "Selic",
                                    ),
                                    _accordion_titulo(
                                        "Tesouro Prefixado",
                                        "LTN",
                                        "Voce sabe exatamente quanto vai receber no vencimento. "
                                        "A taxa fica travada no momento da compra. Bom quando "
                                        "voce acredita que os juros vao cair no futuro. Se "
                                        "vender antes do vencimento, pode ganhar ou perder.",
                                        "Nenhum (taxa fixa)",
                                    ),
                                    _accordion_titulo(
                                        "Tesouro Prefixado com Juros Semestrais",
                                        "NTN-F",
                                        "Igual ao Prefixado, mas paga cupom (juros) a cada "
                                        "6 meses. Bom para quem quer renda periodica sem "
                                        "esperar o vencimento. O valor recebido a cada cupom "
                                        "sofre IR.",
                                        "Nenhum (taxa fixa)",
                                    ),
                                    _accordion_titulo(
                                        "Tesouro IPCA+",
                                        "NTN-B Principal",
                                        "Paga IPCA + uma taxa real fixa. Protege seu poder "
                                        "de compra contra a inflacao, alem de garantir um "
                                        "ganho real (acima da inflacao). Bom para objetivos "
                                        "de longo prazo.",
                                        "IPCA",
                                    ),
                                    _accordion_titulo(
                                        "Tesouro IPCA+ com Juros Semestrais",
                                        "NTN-B",
                                        "Igual ao IPCA+, mas com cupom semestral. Mesmo "
                                        "racional do NTN-F, mas com indexacao a inflacao.",
                                        "IPCA",
                                    ),
                                    _accordion_titulo(
                                        "Tesouro Educa+",
                                        "NTN-B Principal (variante)",
                                        "Voltado para acumular para a educacao dos filhos. "
                                        "Paga IPCA + taxa real e tem cronograma especifico "
                                        "de pagamento que coincide com o periodo educacional.",
                                        "IPCA",
                                    ),
                                    _accordion_titulo(
                                        "Tesouro Renda+",
                                        "NTN-B (variante)",
                                        "Voltado para aposentadoria. Paga IPCA + taxa real, "
                                        "e na fase de pagamento entrega uma renda mensal por "
                                        "20 anos. Bom complemento para previdencia.",
                                        "IPCA",
                                    ),
                                ],
                                start_collapsed=True,
                                always_open=False,
                            ),
                        ],
                        title="Tipos de titulo",
                    ),
                    # Secao 3
                    dbc.AccordionItem(
                        [
                            html.H6("Taxa de custodia B3", className="fw-bold"),
                            html.P(
                                "0,20% ao ano sobre o valor investido. Cobrada "
                                "semestralmente. O Tesouro Selic e isento dessa taxa "
                                "ate R$ 10.000 investidos."
                            ),
                            html.H6("Imposto de Renda (regressivo)", className="fw-bold"),
                            html.Ul(
                                [
                                    html.Li("Ate 180 dias: 22,5%"),
                                    html.Li("De 181 a 360 dias: 20,0%"),
                                    html.Li("De 361 a 720 dias: 17,5%"),
                                    html.Li("Acima de 720 dias: 15,0%"),
                                ]
                            ),
                            html.P(
                                "O IR incide somente sobre os rendimentos, nao sobre "
                                "o valor investido. E retido na fonte no momento do resgate "
                                "ou do pagamento de cupom."
                            ),
                            html.H6("IOF", className="fw-bold"),
                            html.P(
                                "Cobrado apenas se voce vender antes de 30 dias da compra. "
                                "Comeca em 96% sobre o ganho no primeiro dia e diminui "
                                "progressivamente ate zero no 30o dia."
                            ),
                        ],
                        title="Custos e tributacao",
                    ),
                    # Secao 4
                    dbc.AccordionItem(
                        [
                            html.P(
                                "O dashboard usa varias metricas para ranquear "
                                "oportunidades. Veja o que cada uma significa:",
                                className="text-muted mb-2",
                            ),
                            html.H6("Score A (base)", className="fw-bold"),
                            html.P(
                                "Nota de 0 a 1 que combina Carry (40%), Valor Relativo "
                                "(40%) e Liquidez (20%). E o score mais simples e direto."
                            ),
                            html.H6("Score B (ajustado por risco)", className="fw-bold"),
                            html.P(
                                "Igual ao Score A, mas penaliza titulos de prazo muito "
                                "longo (que oscilam mais). Use quando voce nao quer "
                                "muita oscilacao no caminho."
                            ),
                            html.H6("Score C (residuo de curva)", className="fw-bold"),
                            html.P(
                                "Score mais sofisticado: ajusta uma curva teorica de juros "
                                "(Nelson-Siegel-Svensson) e aponta titulos que pagam mais "
                                "do que a curva sugere. Bom para identificar 'distorcoes' "
                                "de mercado."
                            ),
                            html.H6("Carry", className="fw-bold"),
                            html.P(
                                "Quanto a taxa do titulo esta acima da mediana do seu grupo "
                                "de pares. Positivo = paga mais que a media."
                            ),
                            html.H6("Valor Relativo (z-score)", className="fw-bold"),
                            html.P(
                                "Mede quantos desvios-padrao a taxa esta acima ou abaixo "
                                "da media do grupo. Quanto maior, mais atrativo em "
                                "termos relativos."
                            ),
                            html.H6("Liquidez", className="fw-bold"),
                            html.P(
                                "Indicador de 0 a 1 que mede a facilidade de comprar e "
                                "vender o titulo. Baseado no spread entre compra e venda. "
                                "Perto de 1 = facil de negociar."
                            ),
                            html.H6("Bucket de prazo", className="fw-bold"),
                            html.P(
                                "Faixa de prazo do titulo. Curto (ate 2 anos), "
                                "Intermediario (2-5 anos), Longo (5-15 anos), "
                                "Ultralongo (acima de 15 anos)."
                            ),
                            html.H6("Celula analitica", className="fw-bold"),
                            html.P(
                                "Combinacao de grupo (familia/estrutura) + bucket de prazo. "
                                "Os titulos so sao comparados dentro da mesma celula -- nao "
                                "faz sentido comparar um Selic curto com um IPCA+ longo."
                            ),
                        ],
                        title="O que significam as metricas do dashboard",
                    ),
                    # Secao 5
                    dbc.AccordionItem(
                        [
                            html.P(
                                "Marcacao a mercado e o nome dado ao processo de "
                                "atualizacao diaria do preco do seu titulo. Mesmo que "
                                "voce nao venda, o valor de mercado oscila todos os dias "
                                "conforme as expectativas de juros mudam."
                            ),
                            html.H6("Como funciona", className="fw-bold"),
                            html.P(
                                "Quando voce compra um titulo prefixado a 12% a.a. e "
                                "depois os juros do mercado caem para 10%, o seu titulo "
                                "passa a valer mais no mercado (porque ele paga mais que "
                                "os novos titulos). O contrario tambem vale: se os juros "
                                "subirem, seu titulo passa a valer menos."
                            ),
                            html.H6("Quando isso importa", className="fw-bold"),
                            html.P(
                                "Se voce levar o titulo ate o vencimento, voce sempre "
                                "recebe a taxa contratada na compra. A oscilacao do "
                                "preco no caminho so importa se voce decidir vender antes."
                            ),
                            html.P(
                                "Os Tesouros Selic tem oscilacao baixissima porque a "
                                "taxa do papel acompanha a Selic. Os Prefixados e os "
                                "IPCA+ longos tem oscilacao maior, e por isso sao "
                                "considerados de maior risco de marcacao."
                            ),
                        ],
                        title="Marcacao a mercado",
                    ),
                ],
                start_collapsed=True,
                always_open=False,
            ),
        ],
        fluid=True,
    )
