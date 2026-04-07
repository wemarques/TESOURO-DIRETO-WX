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
                            dbc.NavLink("Series Temporais", href="/series", active="exact")
                        ),
                        dbc.NavItem(
                            dbc.NavLink("Titulo Individual", href="/titulo", active="exact")
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

    # Badge de ingestão com cor baseada em frescor
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
            dias = -1

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
                ],
            ),
        ],
        fluid=True,
    )


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
                ],
                className="mb-3",
            ),
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
