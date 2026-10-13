"""Score D (marcacao a mercado) e margem de taxa contra o CDI.

Score D responde a uma pergunta diferente dos Scores A/B/C: "se a taxa cair,
qual titulo mais se beneficia?". Por isso premia duration (o Score B penaliza)
e so faz sentido sob uma tese explicita de queda de taxa — ver o painel de
condicoes em /titulo (``tese.py``). Nao e recomendacao.

Score_D = 0,45 x sensibilidade + 0,30 x percentil_taxa + 0,15 x residuo_curva + 0,10 x liquidez

- sensibilidade: duration modificada normalizada (min-max) dentro do GRUPO AMPLO
  (nominal = Prefixados; real = IPCA+, Renda+, Educa+, IGPM+). Excecao
  documentada a regra "nunca comparar familias": para a pergunta de
  marcacao, Renda+ x Educa+ x IPCA+ e exatamente a comparacao que importa, e
  todos respondem a mesma taxa real. Nominal e real nao se misturam.
- percentil_taxa: posicao da taxa atual nos ultimos 24 meses (0 a 1).
- residuo_curva: componente do Score C (0,5 quando nao ha curva).
- Tesouro Selic fica sem Score D (nao tem risco de juros).

Margem vs CDI (``margem_cdi_12m_pp``): quantos p.p. a taxa do titulo pode SUBIR
em 12 meses antes de o titulo render menos que o CDI esperado no periodo
(retorno bruto, mesmo IR para os dois). Negativo = a taxa precisa CAIR isso
para empatar com o CDI. E a pergunta do video — "o ganho compensa?" — em numero.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from src.analytics.calendario import dias_uteis
from src.analytics.duration import TIPOS_NOMINAIS, liquidacao
from src.analytics.simulador import simular
from src.utils.constants import PESOS_FORMULA_D

logger = logging.getLogger(__name__)

GRUPO_NOMINAL = TIPOS_NOMINAIS
GRUPO_POS = {"Tesouro Selic"}
JANELA_PERCENTIL_DIAS = 730
SPREAD_CDI_SELIC = 0.10  # CDI ~ Selic meta - 0,10 p.p.


def grupo_amplo(tipo_titulo: str) -> str:
    if tipo_titulo in GRUPO_POS:
        return "pos"
    return "nominal" if tipo_titulo in GRUPO_NOMINAL else "real"


def percentil_taxa(df_historico: pd.DataFrame, snapshot: pd.DataFrame) -> pd.Series:
    """Percentil (0-1) da taxa atual de cada titulo do snapshot nos ultimos 24 meses."""
    hoje = snapshot["data_base"].max()
    janela = df_historico[
        df_historico["data_base"] >= hoje - pd.Timedelta(days=JANELA_PERCENTIL_DIAS)
    ]
    grupos = janela.groupby(["tipo_titulo", "data_vencimento"])["taxa_compra_manha"]
    hist = {k: v.dropna().to_numpy() for k, v in grupos}
    out = []
    for tipo, venc, taxa in zip(
        snapshot["tipo_titulo"], snapshot["data_vencimento"], snapshot["taxa_compra_manha"]
    ):
        serie = hist.get((tipo, venc))
        out.append(np.nan if serie is None or len(serie) < 60 else float((serie <= taxa).mean()))
    return pd.Series(out, index=snapshot.index)


def _minmax(s: pd.Series) -> pd.Series:
    if s.max() == s.min():
        return pd.Series(0.5, index=s.index)
    return (s - s.min()) / (s.max() - s.min())


def calcular_score_d(snapshot: pd.DataFrame, df_historico: pd.DataFrame) -> pd.DataFrame:
    """Acrescenta ``percentil_taxa_24m``, ``sensibilidade_norm`` e ``score_d``.

    Requer no snapshot: tipo_titulo, data_vencimento, data_base, taxa_compra_manha,
    duration_modificada, liquidez_norm e (opcional) residuo_curva_norm.
    """
    df = snapshot.copy()
    p = PESOS_FORMULA_D
    df["grupo_amplo"] = df["tipo_titulo"].map(grupo_amplo)
    df["percentil_taxa_24m"] = percentil_taxa(df_historico, df)
    df["sensibilidade_norm"] = np.nan
    for grupo, idx in df.groupby("grupo_amplo").groups.items():
        if grupo == "pos":
            continue
        df.loc[idx, "sensibilidade_norm"] = _minmax(df.loc[idx, "duration_modificada"])

    residuo = (
        df["residuo_curva_norm"] if "residuo_curva_norm" in df.columns
        else pd.Series(np.nan, index=df.index)
    )
    df["score_d"] = (
        p["sensibilidade"] * df["sensibilidade_norm"]
        + p["percentil_taxa"] * df["percentil_taxa_24m"].fillna(0.5)
        + p["residuo_curva"] * residuo.fillna(0.5)
        + p["liquidez"] * df["liquidez_norm"].fillna(0)
    )
    df.loc[df["grupo_amplo"] == "pos", "score_d"] = np.nan
    return df


def cdi_esperado_12m(macro: dict) -> float:
    """CDI medio esperado nos proximos 12 meses (% a.a.).

    Media entre a Selic meta atual e a Selic esperada pelo Focus no fim do ano
    seguinte (aproximacao linear do caminho), menos 0,10 p.p. Sem Focus, usa a
    Selic atual.
    """
    selic = (macro.get("selic_meta") or {}).get("valor")
    focus = (macro.get("focus_selic_fim_ano_seguinte") or {}).get("valor")
    base = selic if focus is None else (selic + focus) / 2
    return base - SPREAD_CDI_SELIC


def margem_vs_cdi(
    linha: pd.Series, cdi_aa_pct: float, indexador_aa_pct: float, horizonte_meses: int = 12
) -> float:
    """Variacao de taxa (p.p.) que zera a vantagem sobre o CDI no horizonte.

    Busca por bissecao o delta em que o retorno bruto do titulo iguala o do CDI.
    """
    kwargs = dict(
        tipo_titulo=linha["tipo_titulo"],
        vencimento=linha["data_vencimento"],
        data_base=linha["data_base"],
        taxa_compra_pct=float(linha["taxa_compra_manha"]),
        pu_compra=float(linha["pu_compra_manha"]),
        taxa_venda_pct=(
            float(linha["taxa_venda_manha"]) if pd.notna(linha.get("taxa_venda_manha")) else None
        ),
        indexador_aa_pct=indexador_aa_pct,
        horizonte_meses=horizonte_meses,
    )
    try:
        r0 = simular(delta_pp=0.0, **kwargs)
    except ValueError:
        return np.nan
    # CDI capitaliza por dia util (du/252), como o titulo
    du = dias_uteis(liquidacao(linha["data_base"]), r0.data_venda)
    alvo = (1 + cdi_aa_pct / 100) ** (du / 252) - 1

    def excesso(delta):
        return simular(delta_pp=delta, **kwargs).retorno_bruto - alvo

    lo, hi = -10.0, 10.0
    if excesso(lo) * excesso(hi) > 0:
        return np.nan
    for _ in range(50):
        meio = (lo + hi) / 2
        if excesso(meio) > 0:
            lo = meio
        else:
            hi = meio
    return (lo + hi) / 2


def calcular_margem_cdi(snapshot: pd.DataFrame, macro: dict) -> pd.DataFrame:
    """Acrescenta ``margem_cdi_12m_pp`` (NaN no Selic e em titulos que vencem antes)."""
    df = snapshot.copy()
    cdi = cdi_esperado_12m(macro)
    ipca = (macro.get("focus_ipca_12m") or {}).get("valor") or (
        (macro.get("ipca_12m") or {}).get("valor") or 0.0
    )
    df["margem_cdi_12m_pp"] = np.nan
    df["cdi_esperado_12m"] = cdi
    for idx, linha in df.iterrows():
        if linha["tipo_titulo"] in GRUPO_POS or pd.isna(linha.get("pu_compra_manha")):
            continue
        indexador = 0.0 if linha["tipo_titulo"] in TIPOS_NOMINAIS else ipca
        df.at[idx, "margem_cdi_12m_pp"] = margem_vs_cdi(linha, cdi, indexador)
    return df
