"""App principal do dashboard Tesouro Direto WX."""

import os
import subprocess
import sys
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, State, dcc, html

# Importacao registra o template plotly 'tdwx_dark' como padrao
from src.dashboard import plotly_theme  # noqa: F401
from src.dashboard.callbacks import (
    build_calculadora_dataset,
    calcular_variacao_e_pu,
    registrar_callbacks,
)
from src.dashboard.layouts import (
    navbar,
    pagina_calculadora,
    pagina_guia,
    pagina_ranking,
    pagina_series,
    pagina_titulo,
    status_bar,
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


def _build_summary_stats(df):
    """Calcula stats de resumo para os summary cards do ranking."""
    if df.empty:
        return {}

    melhor_score_row = df.loc[df["score_a"].idxmax()]
    maior_taxa_row = df.loc[df["taxa_compra_manha"].idxmax()]
    melhor_liq_row = df.loc[df["liquidez_norm"].idxmax()]

    return {
        "melhor_score_valor": f"{melhor_score_row['score_a']:.3f}",
        "melhor_score_titulo": (
            f"{melhor_score_row['tipo_titulo']} "
            f"{melhor_score_row['data_vencimento'].strftime('%Y')}"
        ),
        "maior_taxa_valor": f"{maior_taxa_row['taxa_compra_manha']:.2f}%",
        "maior_taxa_titulo": (
            f"{maior_taxa_row['tipo_titulo']} "
            f"{maior_taxa_row['data_vencimento'].strftime('%Y')}"
        ),
        "melhor_liquidez_valor": f"{melhor_liq_row['liquidez_norm']:.2f}",
        "melhor_liquidez_titulo": (
            f"{melhor_liq_row['tipo_titulo']} "
            f"{melhor_liq_row['data_vencimento'].strftime('%Y')}"
        ),
        "total": total_titulos,
    }


summary_stats = _build_summary_stats(df_ranking)

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
        html.A("Pular para o conteúdo", href="#main-content", className="skip-to-content"),
        navbar(),
        status_bar(data_atualizacao, total_titulos, total_registros, info_ingestao),
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
        return pagina_series(familias, titulos_unicos, grupos_analiticos)
    if pathname == "/titulo":
        return pagina_titulo(titulos_unicos)
    if pathname == "/calculadora":
        return pagina_calculadora()
    if pathname == "/guia":
        return pagina_guia()
    return pagina_ranking(familias, summary_stats)


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
registrar_callbacks(app, df_ranking, df_historico, df_calculadora)

server = app.server

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    host = os.environ.get("HOST", "0.0.0.0")
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    app.run(debug=debug, host=host, port=port)
