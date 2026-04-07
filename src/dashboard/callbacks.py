"""Callbacks de interatividade do dashboard."""

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, callback, html, no_update

from src.dashboard.layouts import NOMES_FAMILIA


def registrar_callbacks(app, df_ranking: pd.DataFrame, df_historico: pd.DataFrame):
    """Registra todos os callbacks no app Dash."""

    # =========================================================================
    # RANKING
    # =========================================================================

    SCORE_LABELS = {
        "score_a": "Score A (base)",
        "score_b": "Score B (risco)",
    }

    TOOLTIPS_COLUNAS = {
        "tipo_titulo": "Nome da familia do titulo do Tesouro Direto",
        "data_vencimento": "Data em que o titulo expira e o governo paga o valor de face",
        "bucket_prazo": (
            "Faixa de prazo — Curto (<=2a), Intermediario (2-5a), "
            "Longo (5-15a), Ultralongo (>15a)"
        ),
        "taxa_compra_manha": (
            "Taxa anual que o investidor recebe se comprar e segurar ate o vencimento"
        ),
        "carry": (
            "Quanto esse titulo paga acima da mediana do seu grupo. "
            "Positivo = acima da media dos pares"
        ),
        "rv_zscore": (
            "Valor Relativo — quantos desvios-padrao a taxa esta acima ou abaixo "
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
            "Nota ajustada por risco (0 a 1) — penaliza titulos com prazo muito longo. "
            "Carry 35% + RV 30% + Liquidez 15% + Risco 20%"
        ),
        "posicao_celula": (
            "Posicao do titulo no ranking dentro do seu grupo comparavel (familia + prazo)"
        ),
        "posicao_global": (
            "Posicao no ranking geral — apenas informativo, "
            "nao use para decisao entre familias diferentes"
        ),
    }

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

        # Resolver "score" para a coluna real selecionada
        col_ordenar = score_col if ordenar_por == "score" else ordenar_por
        df = df.sort_values(col_ordenar, ascending=False)

        # Label amigavel para o titulo
        df["titulo_label"] = (
            df["tipo_titulo"]
            + " "
            + df["data_vencimento"].dt.strftime("%Y")
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

        # Tabela — coluna "score" mostra o score selecionado
        colunas_tabela = [
            ("tipo_titulo", "Titulo"),
            ("data_vencimento", "Vencimento"),
            ("bucket_prazo", "Bucket"),
            ("taxa_compra_manha", "Taxa Compra (%)"),
            ("carry", "Carry"),
            ("rv_zscore", "RV z-score"),
            ("liquidez_norm", "Liquidez"),
            (score_col, score_label),
            ("posicao_celula", "Pos. Celula"),
            ("posicao_global", "Pos. Global"),
        ]
        cols_dash = [{"name": label, "id": col_id} for col_id, label in colunas_tabela]

        # Tooltip por coluna — mapeia col_id para texto explicativo
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
        # Criar labels com vencimento para distinguir
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
        # Selecionar ate 3 titulos por padrao
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
            df["tipo_titulo"]
            + " "
            + df["data_vencimento"].dt.strftime("%Y")
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
    # TITULO INDIVIDUAL
    # =========================================================================

    @app.callback(
        Output("titulo-card-info", "children"),
        Output("titulo-taxa-chart", "figure"),
        Output("titulo-pu-chart", "figure"),
        Output("titulo-spread-chart", "figure"),
        Input("titulo-dropdown", "value"),
    )
    def atualizar_titulo_individual(titulo: str | None):
        fig_vazia = go.Figure().update_layout(template="plotly_white")
        if not titulo:
            return html.P("Selecione um titulo"), fig_vazia, fig_vazia, fig_vazia

        df = df_historico[df_historico["tipo_titulo"] == titulo].sort_values("data_base")

        ultimo = df.iloc[-1]
        # Card de informacoes
        card_body = dbc.CardBody(
            [
                html.H5(titulo, className="card-title"),
                html.Hr(),
                _info_row("Familia", NOMES_FAMILIA.get(
                    str(ultimo["familia_normalizada"]), str(ultimo["familia_normalizada"])
                )),
                _info_row("Vencimento", pd.Timestamp(ultimo["data_vencimento"]).strftime("%d/%m/%Y")),
                _info_row(
                    "Prazo",
                    f"{ultimo['anos_ate_vencimento']:.1f} anos",
                ),
                _info_row("Bucket", str(ultimo["bucket_prazo"])),
                _info_row("Taxa Compra", f"{ultimo['taxa_compra_manha']:.2f}%"),
                _info_row("Taxa Venda", f"{ultimo['taxa_venda_manha']:.2f}%"),
                _info_row("Spread", f"{ultimo['spread_compra_venda']:.4f}"),
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

        return card_body, fig_taxa, fig_pu, fig_spread


def _info_row(label: str, value: str) -> html.Div:
    """Linha de informacao para o card de titulo."""
    return html.Div(
        [
            html.Span(f"{label}: ", className="fw-bold text-muted"),
            html.Span(value),
        ],
        className="mb-1",
    )
