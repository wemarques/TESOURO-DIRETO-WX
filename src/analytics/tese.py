"""Painel de condicoes da tese de queda de taxa (Fase 4).

Transforma o "eu acredito que a taxa vai cair" do video em leituras
mensuraveis — sem virar previsao. Cada condicao e independente e explicavel;
o painel mostra quantas estao atendidas, nunca um veredito de compra.

1. Curva prefixada em queda: a taxa media dos Prefixados caiu em 30 e em 90 dias.
2. Focus espera Selic menor: Selic esperada no fim do ano seguinte < Selic meta atual.
3. Taxa do titulo alta no proprio historico: percentil da taxa atual nos
   ultimos 24 meses >= ``PERCENTIL_ALTO`` (espaco para cair).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.analytics.duration import TIPOS_NOMINAIS

PERCENTIL_ALTO = 0.80
JANELA_PERCENTIL_DIAS = 730


@dataclass(frozen=True)
class Condicao:
    nome: str
    atendida: bool | None  # None = sem dado suficiente
    detalhe: str


def _taxa_media_prefixados(df_historico: pd.DataFrame, data: pd.Timestamp) -> pd.Series:
    """Taxa de cada Prefixado na ultima data <= ``data`` (indexada por titulo)."""
    pre = df_historico[
        df_historico["tipo_titulo"].isin(TIPOS_NOMINAIS) & (df_historico["data_base"] <= data)
    ]
    if pre.empty:
        return pd.Series(dtype=float)
    dia = pre["data_base"].max()
    snap = pre[pre["data_base"] == dia]
    return snap.set_index(["tipo_titulo", "data_vencimento"])["taxa_compra_manha"]


def condicao_curva(df_historico: pd.DataFrame) -> Condicao:
    hoje = df_historico["data_base"].max()
    atual = _taxa_media_prefixados(df_historico, hoje)
    variacoes = {}
    for dias in (30, 90):
        antes = _taxa_media_prefixados(df_historico, hoje - pd.Timedelta(days=dias))
        comuns = atual.index.intersection(antes.index)  # mesmos titulos nas duas datas
        if len(comuns) >= 2:
            variacoes[dias] = float((atual[comuns] - antes[comuns]).mean())
    if len(variacoes) < 2:
        return Condicao("Curva prefixada em queda", None, "Histórico insuficiente.")
    atendida = variacoes[30] < 0 and variacoes[90] < 0
    return Condicao(
        "Curva prefixada em queda",
        atendida,
        f"Taxa média dos Prefixados: {variacoes[30]:+.2f} p.p. em 30 dias e "
        f"{variacoes[90]:+.2f} p.p. em 90 dias.",
    )


def condicao_focus(macro: dict) -> Condicao:
    selic = (macro.get("selic_meta") or {}).get("valor")
    focus = (macro.get("focus_selic_fim_ano_seguinte") or {}).get("valor")
    ano = macro.get("ano_focus_selic")
    if selic is None or focus is None:
        return Condicao("Focus espera Selic menor", None, "Expectativa Focus indisponível.")
    return Condicao(
        "Focus espera Selic menor",
        focus < selic,
        f"Mercado projeta Selic de {focus:.2f}% no fim de {ano} contra {selic:.2f}% hoje "
        f"({focus - selic:+.2f} p.p.).",
    )


def condicao_percentil(df_titulo: pd.DataFrame) -> Condicao:
    """``df_titulo``: historico de UM titulo (data_base, taxa_compra_manha)."""
    if df_titulo.empty:
        return Condicao("Taxa alta no próprio histórico", None, "Sem histórico.")
    hoje = df_titulo["data_base"].max()
    janela = df_titulo[df_titulo["data_base"] >= hoje - pd.Timedelta(days=JANELA_PERCENTIL_DIAS)]
    taxas = janela["taxa_compra_manha"].dropna()
    if len(taxas) < 60:
        return Condicao("Taxa alta no próprio histórico", None, "Menos de 60 observações.")
    atual = float(df_titulo.sort_values("data_base")["taxa_compra_manha"].iloc[-1])
    pct = float((taxas <= atual).mean())
    return Condicao(
        "Taxa alta no próprio histórico",
        pct >= PERCENTIL_ALTO,
        f"Taxa atual {atual:.2f}% está no percentil {pct * 100:.0f} dos últimos 24 meses "
        f"(mín. {taxas.min():.2f}%, máx. {taxas.max():.2f}%). "
        f"Critério: percentil ≥ {PERCENTIL_ALTO * 100:.0f}.",
    )


def avaliar_condicoes(
    df_historico: pd.DataFrame, df_titulo: pd.DataFrame, macro: dict
) -> list[Condicao]:
    """As tres condicoes da tese de queda de taxa, na ordem do painel."""
    return [condicao_curva(df_historico), condicao_focus(macro), condicao_percentil(df_titulo)]
