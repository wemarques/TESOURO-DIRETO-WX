"""App principal do dashboard Tesouro Direto WX."""

import os
import subprocess
import sys
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html

# Importacao registra o template plotly 'tdwx_dark' como padrao
from src.dashboard import plotly_theme  # noqa: F401
from src.dashboard.callbacks import registrar_callbacks
from src.dashboard.dados import EstadoDados, intervalo_recarga_ms
from src.dashboard.layouts import (
    navbar,
    pagina_calculadora,
    pagina_guia,
    pagina_ranking,
    pagina_series,
    pagina_titulo,
    status_bar,
)
from src.utils.constants import (
    DATA_AUDIT,
    DATA_ENRIQUECIDO,
    DATA_OUTPUTS,
    DATA_PADRONIZADO,
    DATA_PROCESSED,
    DATA_RAW,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RANKING_PATH = DATA_OUTPUTS / "ranking_atual.parquet"
BASE_PATH = DATA_OUTPUTS / "base_analitica.parquet"


def _arquivos_publicados_disponiveis() -> bool:
    return RANKING_PATH.exists() and BASE_PATH.exists()


def _ensure_data_exists() -> bool:
    """Garante diretorios e, em ambiente novo, roda o pipeline inicial.

    Retorna True quando os parquets publicados existem; False permite
    o app subir em modo degradado.
    """
    diretorios = [
        DATA_RAW,
        DATA_PADRONIZADO,
        DATA_ENRIQUECIDO,
        DATA_PROCESSED,
        DATA_OUTPUTS,
        DATA_AUDIT,
    ]
    for d in diretorios:
        d.mkdir(parents=True, exist_ok=True)

    if _arquivos_publicados_disponiveis():
        return True

    print("[boot] Sem dados em data/outputs/ - executando pipeline inicial...")
    scripts_dir = PROJECT_ROOT / "scripts"
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}

    for script in ["rodar_ingestao.py", "rodar_analytics.py"]:
        print(f"[boot] Rodando {script}...")
        result = subprocess.run(
            [sys.executable, str(scripts_dir / script)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=900,
            env=env,
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"[boot] {script} falhou:\n{result.stderr}")
            raise RuntimeError(f"Pipeline inicial falhou em {script}")

    if _arquivos_publicados_disponiveis():
        print("[boot] Pipeline inicial concluido")
        return True

    print("[boot] Pipeline executado mas parquets ausentes - modo degradado.")
    return False


# === Carregar estado (recarregavel sem reiniciar via callback periodico) ===
_dados_ok = _ensure_data_exists()
estado = EstadoDados()
if _dados_ok:
    try:
        estado.recarregar()
    except Exception as exc:  # noqa: BLE001 - nao derrubar o app no boot
        print(f"[dashboard] Falha ao carregar dados iniciais: {exc} - modo degradado")
else:
    print("[dashboard] Subindo em modo degradado (sem dados publicados).")


# === App Dash ===
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    suppress_callback_exceptions=True,
    title="Tesouro Direto WX",
)

# index_string com lang=pt-BR + notranslate: impede o navegador (Chrome/Safari)
# de "traduzir" a pagina e corromper os textos PT-BR (e quebrar cliques no mobile).
app.index_string = """<!DOCTYPE html>
<html lang="pt-BR" translate="no">
    <head>
        {%metas%}
        <meta name="google" content="notranslate">
        {%favicon%}
        {%css%}
        <title>{%title%}</title>
    </head>
    <body class="notranslate">
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>"""

app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        html.A("Pular para o conteúdo", href="#main-content", className="skip-to-content"),
        navbar(),
        # Recarga periodica dos parquets publicados + store de metadados.
        dcc.Interval(id="reload-dados-interval", interval=intervalo_recarga_ms(), n_intervals=0),
        dcc.Store(id="dados-meta-store", data=estado.meta()),
        # Wrapper com id: o callback de recarga troca o conteudo da barra de status.
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
        return pagina_series(estado.familias, estado.titulos_unicos, estado.grupos_analiticos)
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
