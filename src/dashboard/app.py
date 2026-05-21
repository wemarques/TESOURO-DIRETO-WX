"""App principal do dashboard Tesouro Direto WX."""

import os

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html

# Importacao registra o template plotly 'tdwx_dark' como padrao
from src.dashboard import plotly_theme  # noqa: F401
from src.dashboard.callbacks import registrar_callbacks
from src.dashboard.dados import EstadoDados, ensure_data_exists, intervalo_recarga_ms
from src.dashboard.layouts import (
    aviso_legal,
    navbar,
    pagina_calculadora,
    pagina_guia,
    pagina_ranking,
    pagina_series,
    pagina_titulo,
    status_bar,
)

ensure_data_exists()

estado = EstadoDados()
estado.recarregar()

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
        dcc.Interval(
            id="reload-dados-interval",
            interval=intervalo_recarga_ms(),
            n_intervals=0,
        ),
        dcc.Store(id="dados-meta-store", data=estado.meta()),
        html.A("Pular para o conteúdo", href="#main-content", className="skip-to-content"),
        navbar(),
        html.Div(
            status_bar(
                estado.data_atualizacao,
                estado.total_titulos,
                estado.total_registros,
                estado.info_ingestao,
                versao_metodologia=estado.versao_metodologia,
                carregado_em=estado.carregado_em,
            ),
            id="tdwx-status-bar",
        ),
        aviso_legal(compact=True),
        html.Main(html.Div(id="page-content"), id="main-content"),
    ]
)


# === Roteamento de paginas ===
@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname"),
)
def renderizar_pagina(pathname: str):
    if pathname == "/series":
        return pagina_series(
            estado.familias, estado.titulos_unicos, estado.grupos_analiticos
        )
    if pathname == "/titulo":
        return pagina_titulo(estado.titulos_unicos)
    if pathname == "/calculadora":
        return pagina_calculadora()
    if pathname == "/guia":
        return pagina_guia()
    return pagina_ranking(estado.familias)


# === Toggle hamburger menu mobile ===
@app.callback(
    Output("tdwx-nav-links", "className"),
    Input("tdwx-hamburger-btn", "n_clicks"),
    State("tdwx-nav-links", "className"),
    prevent_initial_call=True,
)
def toggle_menu_mobile(n_clicks, current_class):
    if not current_class:
        return "tdwx-nav-links"
    if "show" in current_class:
        return "tdwx-nav-links"
    return "tdwx-nav-links show"


# === Registrar callbacks interativos ===
registrar_callbacks(app, estado)

server = app.server

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    host = os.environ.get("HOST", "0.0.0.0")
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    app.run(debug=debug, host=host, port=port)
