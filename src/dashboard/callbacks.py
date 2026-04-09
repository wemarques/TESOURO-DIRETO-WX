"""Callbacks de interatividade do dashboard."""

import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, html, no_update

from src.dashboard.layouts import NOMES_FAMILIA
from src.utils.constants import IPCA_ATUAL

MAPA_INDEXADOR = {
    "Tesouro Selic": "Selic",
    "Tesouro Prefixado": "Prefixado",
    "Tesouro Prefixado com Juros Semestrais": "Prefixado",
    "Tesouro IPCA+": "IPCA",
    "Tesouro IPCA+ com Juros Semestrais": "IPCA",
    "Tesouro IGPM+ com Juros Semestrais": "IGP-M",
    "Tesouro Educa+": "IPCA",
    "Tesouro Renda+ Aposentadoria Extra": "IPCA",
}


# =============================================================================
# HELPERS
# =============================================================================

def calcular_variacao_e_pu(df_ranking: pd.DataFrame, df_historico: pd.DataFrame) -> pd.DataFrame:
    """Acrescenta colunas taxa_12m_atras, taxa_pp_12m e pu_compra_atual ao ranking."""
    df = df_ranking.copy()
    df["taxa_12m_atras"] = float("nan")
    df["taxa_pp_12m"] = float("nan")
    df["pu_compra_atual"] = float("nan")

    data_max = df_historico["data_base"].max()
    data_12m = data_max - pd.Timedelta(days=365)

    for idx, row in df.iterrows():
        hist = df_historico[
            (df_historico["tipo_titulo"] == row["tipo_titulo"])
            & (df_historico["data_vencimento"] == row["data_vencimento"])
        ].sort_values("data_base")

        if hist.empty:
            continue

        atual = hist.iloc[-1]
        if "pu_compra_manha" in atual.index and pd.notna(atual["pu_compra_manha"]):
            df.at[idx, "pu_compra_atual"] = float(atual["pu_compra_manha"])

        hist_antes = hist[hist["data_base"] <= data_12m]
        if hist_antes.empty:
            # Usar o registro mais antigo disponivel se nao houver 12m completo
            hist_antes = hist.iloc[[0]]
        if not hist_antes.empty:
            taxa_antiga = hist_antes.iloc[-1]["taxa_compra_manha"]
            taxa_atual = atual["taxa_compra_manha"]
            df.at[idx, "taxa_12m_atras"] = float(taxa_antiga)
            df.at[idx, "taxa_pp_12m"] = float(taxa_atual - taxa_antiga)

    return df


def _formatar_pp(v: float) -> str:
    """Formata variacao em pontos percentuais. Ex: '+0.50 pp' ou '-0.30 pp'."""
    if pd.isna(v):
        return "—"
    return f"{v:+.2f} pp"


def _formatar_moeda(v: float) -> str:
    """Formata valor como moeda BRL."""
    if pd.isna(v):
        return "—"
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _info_row(label: str, value: str) -> html.Div:
    """Linha de informacao para o card de titulo."""
    return html.Div(
        [
            html.Span(f"{label}: ", className="fw-bold text-muted"),
            html.Span(value),
        ],
        className="mb-1",
    )


def _stat_card(titulo: str, valor: str, cor: str = "primary", subtitulo: str = "") -> dbc.Col:
    """Card pequeno com estatistica."""
    return dbc.Col(
        dbc.Card(
            dbc.CardBody(
                [
                    html.Div(titulo, className="text-muted small"),
                    html.H5(valor, className=f"text-{cor} mb-0 mt-1"),
                    html.Small(subtitulo, className="text-muted") if subtitulo else None,
                ]
            ),
            className="shadow-sm h-100",
        ),
        md=2,
    )


# =============================================================================
# LOGICA DA CALCULADORA
# =============================================================================

def selecionar_titulo_calculadora(
    df_ranking: pd.DataFrame, objetivo: str, oscilacao: str, renda_periodica: str,
) -> tuple[pd.Series | None, pd.DataFrame, str, str]:
    """Aplica regras para selecionar o melhor titulo conforme respostas.

    Returns:
        (melhor_titulo, alternativas_df, score_col, explicacao)
    """
    df = df_ranking.copy()

    # Filtro: precisa renda periodica = somente titulos com cupom
    if renda_periodica == "sim":
        df = df[df["tipo_titulo"].str.contains("Juros Semestrais", case=False, na=False)]

    # Selecao por objetivo + oscilacao
    if objetivo == "reserva":
        df = df[df["familia_normalizada"] == "SELIC"]
        score_col = "score_b"
        explicacao = (
            "Para reserva de emergencia, o Tesouro Selic e a melhor escolha: "
            "baixissima oscilacao e liquidez diaria."
        )
    elif objetivo == "curto":
        if oscilacao == "conservador":
            df = df[
                df["familia_normalizada"].isin(["SELIC", "PRE", "PRE_JS"])
                & (df["bucket_prazo"] == "CURTO")
            ]
            score_col = "score_b"
            explicacao = (
                "Curto prazo conservador: priorizamos Selic e Prefixados curtos, "
                "ajustados por risco para minimizar oscilacao."
            )
        else:
            df = df[
                df["familia_normalizada"].isin(["PRE", "PRE_JS"])
                & df["bucket_prazo"].isin(["CURTO", "INTER"])
            ]
            score_col = "score_a"
            explicacao = (
                "Curto prazo com tolerancia a oscilacao: Prefixados curtos/intermediarios "
                "permitem capturar a taxa atual ate o vencimento."
            )
    elif objetivo == "medio":
        df = df[
            df["familia_normalizada"].isin(["PRE", "PRE_JS", "IPCA", "IPCA_JS"])
            & (df["bucket_prazo"] == "INTER")
        ]
        score_col = "score_b"
        explicacao = (
            "Medio prazo: Prefixados ou IPCA+ intermediarios oferecem boa "
            "relacao retorno/risco com horizonte de 2 a 5 anos."
        )
    elif objetivo == "longo":
        df = df[
            df["familia_normalizada"].isin(["IPCA", "IPCA_JS"])
            & (df["bucket_prazo"] == "LONGO")
        ]
        score_col = "score_c"
        explicacao = (
            "Longo prazo: IPCA+ longo protege contra inflacao e o Score C "
            "identifica titulos pagando acima da curva teorica."
        )
    elif objetivo == "aposentadoria":
        df = df[
            df["familia_normalizada"].isin(["IPCA", "IPCA_JS", "RENDA"])
            & df["bucket_prazo"].isin(["LONGO", "ULTRA"])
        ]
        score_col = "score_c"
        explicacao = (
            "Aposentadoria: IPCA+ longo/ultralongo ou Renda+ entregam ganho real "
            "sustentado para horizontes acima de 15 anos."
        )
    else:
        score_col = "score_a"
        explicacao = ""

    if df.empty:
        return None, pd.DataFrame(), score_col, (
            "Nao ha titulos disponiveis com essa combinacao de filtros. "
            "Tente alterar 'renda periodica' ou o objetivo."
        )

    df = df.sort_values(score_col, ascending=False).reset_index(drop=True)
    melhor = df.iloc[0]
    alternativas = df.head(3)
    return melhor, alternativas, score_col, explicacao


# =============================================================================
# REGISTRAR CALLBACKS
# =============================================================================

def registrar_callbacks(app, df_ranking: pd.DataFrame, df_historico: pd.DataFrame):
    """Registra todos os callbacks no app Dash."""

    SCORE_LABELS = {
        "score_a": "Score A (base)",
        "score_b": "Score B (risco)",
        "score_c": "Score C (curva)",
    }

    TOOLTIPS_COLUNAS = {
        "tipo_titulo": "Nome da familia do titulo do Tesouro Direto",
        "indexador": (
            "Indice ao qual o rendimento esta atrelado. "
            "Prefixado = taxa fixa. Selic/IPCA/IGP-M = taxa + variacao do indice"
        ),
        "data_vencimento": "Data em que o titulo expira e o governo paga o valor de face",
        "bucket_prazo": (
            "Faixa de prazo - Curto (<=2a), Intermediario (2-5a), "
            "Longo (5-15a), Ultralongo (>15a)"
        ),
        "taxa_compra_manha": (
            "Taxa anual que o investidor recebe se comprar e segurar ate o vencimento"
        ),
        "taxa_pp_12m_str": (
            "Variacao da taxa em pontos percentuais (pp) nos ultimos 12 meses. "
            "Em renda fixa: taxa subindo = preco caindo = oportunidade para "
            "quem quer comprar. Taxa caindo = preco subindo = bom para quem ja tem."
        ),
        "pu_compra_str": "Preco unitario de compra atual em reais",
        "carry": (
            "Quanto esse titulo paga acima da mediana do seu grupo. "
            "Positivo = acima da media dos pares"
        ),
        "rv_zscore": (
            "Valor Relativo - quantos desvios-padrao a taxa esta acima ou abaixo "
            "da media do grupo. Quanto maior, mais atrativo"
        ),
        "liquidez_norm": (
            "Facilidade de compra/venda, baseada no spread. "
            "Perto de 1 = facil de negociar, perto de 0 = dificil"
        ),
        "score_a": (
            "Nota de oportunidade (0 a 1) combinando "
            "Carry 40% + Valor Relativo 40% + Liquidez 20%"
        ),
        "score_b": (
            "Nota ajustada por risco (0 a 1) - penaliza titulos com prazo muito longo. "
            "Carry 35% + RV 30% + Liquidez 15% + Risco 20%"
        ),
        "score_c": (
            "Nota por residuo de curva NSS (0 a 1) - identifica titulos que pagam "
            "mais que a curva teorica sugere. Carry 30% + Residuo 40% + Rolldown 15% + Liquidez 15%"
        ),
        "posicao_celula": (
            "Posicao do titulo no ranking dentro do seu grupo comparavel (familia + prazo)"
        ),
        "posicao_global": (
            "Posicao no ranking geral - apenas informativo, "
            "nao use para decisao entre familias diferentes"
        ),
    }

    # =========================================================================
    # RANKING
    # =========================================================================

    @app.callback(
        Output("ranking-bar-chart", "figure"),
        Output("ranking-tabela", "data"),
        Output("ranking-tabela", "columns"),
        Output("ranking-tabela", "tooltip_header"),
        Input("ranking-score-dropdown", "value"),
        Input("ranking-familia-dropdown", "value"),
        Input("ranking-ordenar-dropdown", "value"),
    )
    def atualizar_ranking(score_col: str, familia: str, ordenar_por: str):
        if not score_col or not familia or not ordenar_por:
            return no_update, no_update, no_update, no_update
        df = df_ranking.copy()
        if familia != "TODAS":
            df = df[df["familia_normalizada"] == familia]

        col_ordenar = score_col if ordenar_por == "score" else ordenar_por
        df = df.sort_values(col_ordenar, ascending=False)

        df["titulo_label"] = (
            df["tipo_titulo"] + " " + df["data_vencimento"].dt.strftime("%Y")
        )

        score_label = SCORE_LABELS.get(score_col, score_col)
        fig = px.bar(
            df,
            x="titulo_label",
            y=score_col,
            color="familia_normalizada",
            color_discrete_sequence=px.colors.qualitative.Set2,
            labels={
                "titulo_label": "Titulo",
                score_col: score_label,
                "familia_normalizada": "Familia",
            },
            title=f"{score_label} por Titulo",
        )
        fig.update_layout(
            xaxis_tickangle=-45,
            height=450,
            margin=dict(b=120),
            template="plotly_white",
        )

        # Colunas derivadas para apresentacao
        df["indexador"] = df["tipo_titulo"].map(MAPA_INDEXADOR).fillna("-")
        df["taxa_pp_12m_str"] = df["taxa_pp_12m"].apply(_formatar_pp)
        df["pu_compra_str"] = df["pu_compra_atual"].apply(_formatar_moeda)

        colunas_tabela = [
            ("tipo_titulo", "Titulo"),
            ("indexador", "Indexador"),
            ("data_vencimento", "Vencimento"),
            ("bucket_prazo", "Bucket"),
            ("taxa_compra_manha", "Taxa Compra (%)"),
            ("taxa_pp_12m_str", "Taxa 12M (pp)"),
            ("pu_compra_str", "PU Compra"),
            ("carry", "Carry"),
            ("rv_zscore", "RV z-score"),
            ("liquidez_norm", "Liquidez"),
            (score_col, score_label),
            ("posicao_celula", "Pos. Celula"),
            ("posicao_global", "Pos. Global"),
        ]
        cols_dash = [{"name": label, "id": col_id} for col_id, label in colunas_tabela]

        tooltip_header = {
            col_id: {"value": TOOLTIPS_COLUNAS.get(col_id, label), "type": "text"}
            for col_id, label in colunas_tabela
        }

        df_tab = df[[c for c, _ in colunas_tabela]].copy()
        df_tab["data_vencimento"] = df_tab["data_vencimento"].dt.strftime("%d/%m/%Y")
        for col in ["taxa_compra_manha", "carry", "rv_zscore", "liquidez_norm", score_col]:
            df_tab[col] = df_tab[col].round(4)

        return fig, df_tab.to_dict("records"), cols_dash, tooltip_header

    # =========================================================================
    # SERIES TEMPORAIS
    # =========================================================================

    @app.callback(
        Output("series-titulos-dropdown", "options"),
        Output("series-titulos-dropdown", "value"),
        Input("series-familia-dropdown", "value"),
    )
    def atualizar_titulos_serie(familia: str):
        df = df_historico[df_historico["familia_normalizada"] == familia]
        titulos = sorted(df["tipo_titulo"].unique())
        venc_map = (
            df.groupby("tipo_titulo")["data_vencimento"]
            .first()
            .dt.strftime("%Y")
            .to_dict()
        )
        opcoes = [
            {"label": f"{t} ({venc_map.get(t, '')})", "value": t}
            for t in titulos
        ]
        default = titulos[:3] if len(titulos) >= 3 else titulos
        return opcoes, default

    @app.callback(
        Output("series-line-chart", "figure"),
        Input("series-titulos-dropdown", "value"),
        Input("series-periodo-dropdown", "value"),
    )
    def atualizar_grafico_series(titulos: list[str] | None, periodo_dias: int):
        if not titulos:
            return go.Figure().update_layout(
                title="Selecione titulos para visualizar",
                template="plotly_white",
            )

        df = df_historico[df_historico["tipo_titulo"].isin(titulos)].copy()

        if periodo_dias > 0:
            data_corte = df["data_base"].max() - pd.Timedelta(days=periodo_dias)
            df = df[df["data_base"] >= data_corte]

        df["titulo_label"] = (
            df["tipo_titulo"] + " " + df["data_vencimento"].dt.strftime("%Y")
        )

        fig = px.line(
            df,
            x="data_base",
            y="taxa_compra_manha",
            color="titulo_label",
            labels={
                "data_base": "Data",
                "taxa_compra_manha": "Taxa Compra (% a.a.)",
                "titulo_label": "Titulo",
            },
            title="Evolucao da Taxa de Compra",
        )
        fig.update_layout(
            height=500,
            template="plotly_white",
            hovermode="x unified",
        )
        return fig

    # =========================================================================
    # CURVA NSS
    # =========================================================================

    @app.callback(
        Output("curva-nss-chart", "figure"),
        Input("curva-grupo-dropdown", "value"),
        Input("curva-opcoes-checklist", "value"),
    )
    def atualizar_curva_nss(grupo: str | None, opcoes: list[str] | None):
        if not grupo or not opcoes:
            return go.Figure().update_layout(
                title="Selecione um grupo analitico",
                template="plotly_white",
            )

        from src.analytics.curva import obter_curva_snapshot

        resultado = obter_curva_snapshot(df_historico, grupo)
        fig = go.Figure()

        if resultado is None:
            fig.update_layout(
                title=f"Curva indisponivel para {grupo} (pontos insuficientes)",
                template="plotly_white",
                height=450,
            )
            return fig

        if "pontos" in opcoes:
            fig.add_trace(go.Scatter(
                x=resultado["prazos_obs"],
                y=resultado["taxas_obs"],
                mode="markers",
                name="Taxas observadas",
                marker=dict(size=10, color="#2196F3"),
            ))

        if "curva" in opcoes:
            fig.add_trace(go.Scatter(
                x=resultado["prazos_plot"],
                y=resultado["taxas_plot"],
                mode="lines",
                name="Curva NSS ajustada",
                line=dict(color="#FF5722", width=2.5),
            ))

        params = resultado["params"]
        fig.update_layout(
            title=f"Estrutura a Termo - {grupo} (RMSE: {params.rmse:.4f})",
            xaxis_title="Prazo (anos)",
            yaxis_title="Taxa (% a.a.)",
            template="plotly_white",
            height=450,
            hovermode="x unified",
        )

        return fig

    # =========================================================================
    # TITULO INDIVIDUAL
    # =========================================================================

    @app.callback(
        Output("titulo-card-info", "children"),
        Output("titulo-stats-cards", "children"),
        Output("titulo-taxa-chart", "figure"),
        Output("titulo-pu-chart", "figure"),
        Output("titulo-spread-chart", "figure"),
        Input("titulo-dropdown", "value"),
        Input("titulo-periodo-dropdown", "value"),
    )
    def atualizar_titulo_individual(titulo: str | None, periodo_dias: int):
        fig_vazia = go.Figure().update_layout(template="plotly_white")
        if not titulo:
            return html.P("Selecione um titulo"), html.Div(), fig_vazia, fig_vazia, fig_vazia

        df_full = df_historico[df_historico["tipo_titulo"] == titulo].sort_values("data_base")
        if df_full.empty:
            return html.P("Sem dados"), html.Div(), fig_vazia, fig_vazia, fig_vazia

        ultimo = df_full.iloc[-1]
        data_max = df_full["data_base"].max()

        # 52 semanas (365 dias)
        df_52w = df_full[df_full["data_base"] >= data_max - pd.Timedelta(days=365)]
        # 12 meses para variacao
        df_12m_atras = df_full[df_full["data_base"] <= data_max - pd.Timedelta(days=365)]
        # Mes atual
        primeiro_dia_mes = data_max.replace(day=1)
        df_mes = df_full[df_full["data_base"] >= primeiro_dia_mes]

        # Variacoes
        valorizacao_12m = float("nan")
        if not df_12m_atras.empty and "pu_compra_manha" in df_full.columns:
            pu_antigo = df_12m_atras.iloc[-1]["pu_compra_manha"]
            pu_atual = ultimo["pu_compra_manha"]
            if pu_antigo and pu_antigo > 0:
                valorizacao_12m = ((pu_atual - pu_antigo) / pu_antigo) * 100

        valorizacao_mes = float("nan")
        if len(df_mes) >= 2 and "pu_compra_manha" in df_full.columns:
            pu_inicio = df_mes.iloc[0]["pu_compra_manha"]
            pu_atual = ultimo["pu_compra_manha"]
            if pu_inicio and pu_inicio > 0:
                valorizacao_mes = ((pu_atual - pu_inicio) / pu_inicio) * 100

        # Min/Max 52 semanas
        if "pu_compra_manha" in df_52w.columns:
            pu_min = df_52w["pu_compra_manha"].min()
            pu_max = df_52w["pu_compra_manha"].max()
        else:
            pu_min = pu_max = float("nan")
        taxa_min = df_52w["taxa_compra_manha"].min()
        taxa_max = df_52w["taxa_compra_manha"].max()

        # Comparacao 12 meses (taxa em pp)
        taxa_atual = float(ultimo["taxa_compra_manha"])
        if not df_12m_atras.empty:
            taxa_antiga = float(df_12m_atras.iloc[-1]["taxa_compra_manha"])
        else:
            taxa_antiga = float("nan")
        pp_12m = (
            taxa_atual - taxa_antiga
            if pd.notna(taxa_antiga)
            else float("nan")
        )

        def _fmt_pct(v):
            if pd.isna(v):
                return "—"
            return f"{v:+.2f}%"

        stats_row = dbc.Row(
            [
                _stat_card("PU Min 52s", _formatar_moeda(pu_min), "secondary"),
                _stat_card("PU Max 52s", _formatar_moeda(pu_max), "secondary"),
                _stat_card("Taxa Min 52s", f"{taxa_min:.2f}%" if pd.notna(taxa_min) else "—", "secondary"),
                _stat_card("Taxa Max 52s", f"{taxa_max:.2f}%" if pd.notna(taxa_max) else "—", "secondary"),
                _stat_card(
                    "Valor. 12M",
                    _fmt_pct(valorizacao_12m),
                    "success" if (pd.notna(valorizacao_12m) and valorizacao_12m >= 0) else "danger",
                ),
                _stat_card(
                    "Valor. mes",
                    _fmt_pct(valorizacao_mes),
                    "success" if (pd.notna(valorizacao_mes) and valorizacao_mes >= 0) else "danger",
                ),
            ],
            className="g-2",
        )

        # Card de comparacao 12 meses com efeito no preco
        if pd.isna(pp_12m):
            efeito_icone = ""
            efeito_texto = "Sem dado de 12 meses atras"
            efeito_cor = "secondary"
        elif pp_12m > 0:
            efeito_icone = "🛒"
            efeito_texto = "titulo ficou mais barato (oportunidade para compra)"
            efeito_cor = "primary"
        elif pp_12m < 0:
            efeito_icone = "⚠️"
            efeito_texto = "titulo ficou mais caro (menos atrativo para entrada agora)"
            efeito_cor = "warning"
        else:
            efeito_icone = "="
            efeito_texto = "preco praticamente inalterado"
            efeito_cor = "secondary"

        card_12m = dbc.Card(
            dbc.CardBody(
                [
                    html.H6(
                        "Comparacao 12 meses (taxa)",
                        className="card-title text-muted",
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Div("Taxa ha 12 meses", className="small text-muted"),
                                    html.H5(
                                        f"{taxa_antiga:.2f}%" if pd.notna(taxa_antiga) else "—",
                                    ),
                                ],
                                md=3,
                            ),
                            dbc.Col(
                                [
                                    html.Div("Taxa hoje", className="small text-muted"),
                                    html.H5(f"{taxa_atual:.2f}%"),
                                ],
                                md=3,
                            ),
                            dbc.Col(
                                [
                                    html.Div("Variacao", className="small text-muted"),
                                    html.H5(_formatar_pp(pp_12m)),
                                ],
                                md=3,
                            ),
                            dbc.Col(
                                [
                                    html.Div(
                                        "Efeito no preco", className="small text-muted"
                                    ),
                                    html.H6(
                                        [
                                            html.Span(efeito_icone, className="me-2"),
                                            efeito_texto,
                                        ],
                                        className=f"text-{efeito_cor}",
                                    ),
                                ],
                                md=3,
                            ),
                        ],
                    ),
                ]
            ),
            className="shadow-sm mt-3",
        )

        stats_div = html.Div([stats_row, card_12m])

        # Filtrar pelo periodo do grafico
        if periodo_dias and periodo_dias > 0:
            df = df_full[df_full["data_base"] >= data_max - pd.Timedelta(days=periodo_dias)]
        else:
            df = df_full

        # Card de informacoes
        indexador = MAPA_INDEXADOR.get(titulo, "-")
        card_body = dbc.CardBody(
            [
                html.H5(titulo, className="card-title"),
                html.Hr(),
                _info_row("Familia", NOMES_FAMILIA.get(
                    str(ultimo["familia_normalizada"]), str(ultimo["familia_normalizada"])
                )),
                _info_row("Indexador", indexador),
                _info_row("Vencimento", pd.Timestamp(ultimo["data_vencimento"]).strftime("%d/%m/%Y")),
                _info_row("Prazo", f"{ultimo['anos_ate_vencimento']:.1f} anos"),
                _info_row("Bucket", str(ultimo["bucket_prazo"])),
                _info_row("Taxa Compra", f"{ultimo['taxa_compra_manha']:.2f}%"),
                _info_row("Taxa Venda", f"{ultimo['taxa_venda_manha']:.2f}%"),
                _info_row("Spread", f"{ultimo['spread_compra_venda']:.4f}"),
                _info_row("PU Compra", _formatar_moeda(
                    ultimo.get("pu_compra_manha", float("nan"))
                )),
                html.Hr(),
                _info_row("IPCA atual (ref)", f"{IPCA_ATUAL:.2f}%"),
            ]
        )

        # Grafico de taxa
        fig_taxa = px.line(
            df,
            x="data_base",
            y=["taxa_compra_manha", "taxa_venda_manha"],
            labels={"data_base": "Data", "value": "Taxa (% a.a.)", "variable": ""},
            title="Taxas de Compra e Venda",
        )
        fig_taxa.update_layout(template="plotly_white", height=350)

        # Grafico de PU
        pu_cols = [c for c in ["pu_compra_manha", "pu_venda_manha"] if c in df.columns]
        if pu_cols:
            fig_pu = px.line(
                df,
                x="data_base",
                y=pu_cols,
                labels={"data_base": "Data", "value": "PU (R$)", "variable": ""},
                title="Precos Unitarios",
            )
        else:
            fig_pu = fig_vazia
        fig_pu.update_layout(template="plotly_white", height=350)

        # Grafico de spread
        fig_spread = px.area(
            df,
            x="data_base",
            y="spread_compra_venda",
            labels={"data_base": "Data", "spread_compra_venda": "Spread Relativo"},
            title="Spread Compra/Venda",
        )
        fig_spread.update_layout(template="plotly_white", height=350)

        return card_body, stats_div, fig_taxa, fig_pu, fig_spread

    # =========================================================================
    # CALCULADORA
    # =========================================================================

    @app.callback(
        Output("calc-resultado", "children"),
        Input("calc-objetivo-dropdown", "value"),
        Input("calc-oscilacao-radio", "value"),
        Input("calc-renda-radio", "value"),
    )
    def atualizar_calculadora(objetivo: str, oscilacao: str, renda: str):
        if not objetivo or not oscilacao or not renda:
            return html.Div()

        melhor, alternativas, score_col, explicacao = selecionar_titulo_calculadora(
            df_ranking, objetivo, oscilacao, renda,
        )
        score_label = SCORE_LABELS.get(score_col, score_col)

        if melhor is None:
            return dbc.Alert(explicacao, color="warning")

        indexador = MAPA_INDEXADOR.get(str(melhor["tipo_titulo"]), "-")
        venc = pd.Timestamp(melhor["data_vencimento"]).strftime("%d/%m/%Y")
        pu = _formatar_moeda(melhor.get("pu_compra_atual", float("nan")))

        card_destaque = dbc.Card(
            dbc.CardBody(
                [
                    html.Div("Melhor opcao para voce hoje:", className="text-muted"),
                    html.H3(
                        melhor["tipo_titulo"], className="text-primary mt-2 mb-2"
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Div("Indexador", className="small text-muted"),
                                    html.H5(indexador),
                                ],
                                md=2,
                            ),
                            dbc.Col(
                                [
                                    html.Div("Taxa Compra", className="small text-muted"),
                                    html.H5(f"{melhor['taxa_compra_manha']:.2f}%"),
                                ],
                                md=2,
                            ),
                            dbc.Col(
                                [
                                    html.Div("Vencimento", className="small text-muted"),
                                    html.H5(venc),
                                ],
                                md=2,
                            ),
                            dbc.Col(
                                [
                                    html.Div("PU Compra", className="small text-muted"),
                                    html.H5(pu),
                                ],
                                md=2,
                            ),
                            dbc.Col(
                                [
                                    html.Div(score_label, className="small text-muted"),
                                    html.H5(f"{melhor[score_col]:.3f}"),
                                ],
                                md=2,
                            ),
                            dbc.Col(
                                [
                                    html.Div("Pos. Celula", className="small text-muted"),
                                    html.H5(f"{int(melhor['posicao_celula'])}"),
                                ],
                                md=2,
                            ),
                        ],
                        className="mb-3",
                    ),
                    dbc.Alert(explicacao, color="info", className="mb-0"),
                ]
            ),
            color="success",
            outline=True,
            className="mb-4 shadow",
        )

        # Tabela de alternativas
        if len(alternativas) > 1:
            alt = alternativas.copy()
            alt["indexador"] = alt["tipo_titulo"].map(MAPA_INDEXADOR).fillna("-")
            alt["venc_str"] = alt["data_vencimento"].dt.strftime("%d/%m/%Y")
            alt["score_str"] = alt[score_col].map(lambda v: f"{v:.3f}")
            alt["taxa_str"] = alt["taxa_compra_manha"].map(lambda v: f"{v:.2f}%")

            tabela = dbc.Table.from_dataframe(
                alt[[
                    "tipo_titulo", "indexador", "venc_str",
                    "bucket_prazo", "taxa_str", "score_str",
                ]].rename(
                    columns={
                        "tipo_titulo": "Titulo",
                        "indexador": "Indexador",
                        "venc_str": "Vencimento",
                        "bucket_prazo": "Bucket",
                        "taxa_str": "Taxa",
                        "score_str": score_label,
                    }
                ),
                striped=True,
                bordered=True,
                hover=True,
                className="mt-2",
            )
            secao_alternativas = html.Div(
                [
                    html.H5("Top alternativas do mesmo grupo", className="mt-3 mb-2"),
                    tabela,
                ]
            )
        else:
            secao_alternativas = html.Div()

        return html.Div([card_destaque, secao_alternativas])
