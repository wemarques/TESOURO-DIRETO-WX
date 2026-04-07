"""App principal do dashboard Tesouro Direto WX."""

from pathlib import Path

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, html, dcc

from src.dashboard.callbacks import registrar_callbacks
from src.dashboard.layouts import (
    metadados_card,
    navbar,
    pagina_ranking,
    pagina_series,
    pagina_titulo,
)

# === Carregar dados de data/outputs/ ===
OUTPUTS_DIR = Path(__file__).resolve().parents[2] / "data" / "outputs"

df_ranking = pd.read_parquet(OUTPUTS_DIR / "ranking_atual.parquet")
df_historico = pd.read_parquet(OUTPUTS_DIR / "base_analitica.parquet")

# Metadados
data_atualizacao = df_ranking["data_base"].max().strftime("%d/%m/%Y")
total_titulos = len(df_ranking)
total_registros = len(df_historico)
familias = sorted(df_ranking["familia_normalizada"].unique().tolist())
titulos_unicos = sorted(df_historico["tipo_titulo"].unique().tolist())
grupos_analiticos = sorted(df_historico["grupo_analitico"].unique().tolist())

# === App Dash ===
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    suppress_callback_exceptions=True,
    title="Tesouro Direto WX",
)

app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        navbar(),
        dbc.Container(
            metadados_card(data_atualizacao, total_titulos, total_registros),
            fluid=True,
        ),
        html.Div(id="page-content"),
    ]
)


# === Roteamento de paginas ===
@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname"),
)
def renderizar_pagina(pathname: str):
    if pathname == "/series":
        return pagina_series(familias, titulos_unicos, grupos_analiticos)
    if pathname == "/titulo":
        return pagina_titulo(titulos_unicos)
    return pagina_ranking(familias)


# === Registrar callbacks interativos ===
registrar_callbacks(app, df_ranking, df_historico)

server = app.server

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8050)
