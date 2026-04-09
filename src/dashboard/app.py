"""App principal do dashboard Tesouro Direto WX."""

import os
import subprocess
import sys
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, dcc, html

from src.dashboard.callbacks import (
    build_calculadora_dataset,
    calcular_variacao_e_pu,
    registrar_callbacks,
)
from src.dashboard.layouts import (
    metadados_card,
    navbar,
    pagina_calculadora,
    pagina_guia,
    pagina_ranking,
    pagina_series,
    pagina_titulo,
)
from src.ingestao.registro import obter_ultima_ingestao
from src.utils.constants import (
    DATA_AUDIT,
    DATA_ENRIQUECIDO,
    DATA_OUTPUTS,
    DATA_PADRONIZADO,
    DATA_PROCESSED,
    DATA_RAW,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _ensure_data_exists():
    """Garante que diretorios e arquivos de dados existem.

    Em ambientes novos (ex: primeiro deploy no Railway), cria os
    diretorios necessarios e executa o pipeline de ingestao + analytics
    se ainda nao houver dados publicados.
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

    ranking_path = DATA_OUTPUTS / "ranking_atual.parquet"
    base_path = DATA_OUTPUTS / "base_analitica.parquet"
    if ranking_path.exists() and base_path.exists():
        return

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

    print("[boot] Pipeline inicial concluido")


# Garantir dados antes de carregar
_ensure_data_exists()

# === Carregar dados de data/outputs/ ===
df_ranking = pd.read_parquet(DATA_OUTPUTS / "ranking_atual.parquet")
df_historico = pd.read_parquet(DATA_OUTPUTS / "base_analitica.parquet")

# Pre-computar variacao 12M e pu_compra_atual no ranking
df_ranking = calcular_variacao_e_pu(df_ranking, df_historico)

# Dataset enriquecido para a calculadora (todos os titulos do dia)
df_calculadora = build_calculadora_dataset(df_historico)

# Metadados
data_atualizacao = df_ranking["data_base"].max().strftime("%d/%m/%Y")
total_titulos = len(df_ranking)
total_registros = len(df_historico)
familias = sorted(df_ranking["familia_normalizada"].unique().tolist())
titulos_unicos = sorted(df_historico["tipo_titulo"].unique().tolist())
grupos_analiticos = sorted(df_historico["grupo_analitico"].unique().tolist())

# Info da última ingestão (se disponível)
ultima_ingestao = obter_ultima_ingestao()
info_ingestao = {
    "data_ingestao": ultima_ingestao.get("data_ingestao", "")[:10] if ultima_ingestao else "",
    "metodo": ultima_ingestao.get("metodo_obtencao", "") if ultima_ingestao else "",
}

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
            metadados_card(data_atualizacao, total_titulos, total_registros, info_ingestao),
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
    if pathname == "/calculadora":
        return pagina_calculadora()
    if pathname == "/guia":
        return pagina_guia()
    return pagina_ranking(familias)


# === Registrar callbacks interativos ===
registrar_callbacks(app, df_ranking, df_historico, df_calculadora)

server = app.server

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    host = os.environ.get("HOST", "0.0.0.0")
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    app.run(debug=debug, host=host, port=port)
