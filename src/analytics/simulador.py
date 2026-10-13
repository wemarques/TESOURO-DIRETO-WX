"""Simulador de cenarios de marcacao a mercado (Fase 5).

Para um titulo comprado hoje e vendido ao Tesouro apos ``horizonte_meses``,
com a taxa variando ``delta_pp`` ate la, estima:

- PU de venda (recompra pelo Tesouro, a taxa de VENDA, liquidacao D+0);
- fluxos recebidos no caminho (cupons/parcelas), sem reinvestimento;
- retorno bruto, IR regressivo, IOF (< 30 dias), custodia B3 e retorno liquido;
- decomposicao do ganho em efeito-taxa (marcacao) e carrego/indexacao.

Premissas (explicitas na tela): indexador projetado constante (IPCA ou Selic),
spread compra/venda de hoje mantido, custodia de 0,20% a.a. sobre o valor
medio, sem isencao de custodia do Selic ate R$ 10 mil. Isto e uma simulacao
educativa, nao recomendacao de investimento.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from src.analytics.calendario import dias_uteis, feriados_array
from src.analytics.duration import TIPOS_NOMINAIS, fluxos, liquidacao

CUSTODIA_AA = 0.0020
# IOF regressivo sobre o rendimento, por dia corrido (1..29); 0 a partir do 30o
_IOF = [96, 93, 90, 86, 83, 80, 76, 73, 70, 66, 63, 60, 56, 53, 50,
        46, 43, 40, 36, 33, 30, 26, 23, 20, 16, 13, 10, 6, 3]
DEGRAUS_IR = [(180, 0.225), (360, 0.20), (720, 0.175)]
ALIQUOTA_FINAL_IR = 0.15


def aliquota_ir(dias_corridos: int) -> float:
    """IR regressivo da renda fixa pelo prazo da aplicacao."""
    for limite, aliquota in DEGRAUS_IR:
        if dias_corridos <= limite:
            return aliquota
    return ALIQUOTA_FINAL_IR


def proximo_degrau_ir(dias_corridos: int) -> tuple[int, float] | None:
    """(dias que faltam, nova aliquota) ate o proximo degrau; None se ja e 15%."""
    for limite, _ in DEGRAUS_IR:
        if dias_corridos <= limite:
            return limite + 1 - dias_corridos, aliquota_ir(limite + 1)
    return None


def aliquota_iof(dias_corridos: int) -> float:
    """IOF regressivo sobre o rendimento (zero a partir de 30 dias)."""
    if dias_corridos < 1:
        return 1.0
    if dias_corridos >= 30:
        return 0.0
    return _IOF[dias_corridos - 1] / 100


def _proximo_dia_util(d: pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(
        np.busday_offset(np.datetime64(d.date()), 0, roll="forward", holidays=feriados_array())
    )


@dataclass(frozen=True)
class ResultadoSimulacao:
    """Resultado de um cenario (valores por 1 titulo)."""

    data_venda: pd.Timestamp
    dias_corridos: int
    pu_compra: float
    pu_venda: float
    fluxos_recebidos: float
    retorno_bruto: float          # fracao
    efeito_taxa: float            # fracao do PU atribuida a mudanca de taxa
    aliquota_ir: float
    iof: float                    # R$
    ir: float                     # R$
    custodia: float               # R$
    resultado_liquido: float      # R$
    retorno_liquido: float        # fracao
    retorno_liquido_aa: float     # fracao ao ano (base 365 dias corridos)

    def to_dict(self) -> dict:
        return asdict(self)


def _fator(valores, anos, taxa_pct):
    return float((valores / (1 + taxa_pct / 100) ** anos).sum())


def simular(
    tipo_titulo: str,
    vencimento,
    data_base,
    taxa_compra_pct: float,
    pu_compra: float,
    delta_pp: float,
    horizonte_meses: int,
    taxa_venda_pct: float | None = None,
    indexador_aa_pct: float = 0.0,
) -> ResultadoSimulacao:
    """Simula comprar hoje e vender ao Tesouro apos ``horizonte_meses``.

    Args:
        tipo_titulo, vencimento: identificam o titulo.
        data_base: data do preco de compra (liquidacao D+1).
        taxa_compra_pct, pu_compra: taxa e PU de compra de hoje.
        delta_pp: variacao da taxa ate a venda (p.p.; negativo = taxa cai).
        horizonte_meses: prazo ate a venda.
        taxa_venda_pct: taxa de venda de hoje (para manter o spread). Se None,
            assume spread zero.
        indexador_aa_pct: IPCA projetado (titulos IPCA) ou Selic projetada
            (Tesouro Selic), % a.a. Ignorado em prefixados.
    """
    venc = pd.Timestamp(vencimento)
    liq0 = pd.Timestamp(liquidacao(data_base))
    data_venda = _proximo_dia_util(liq0 + pd.DateOffset(months=horizonte_meses))
    if data_venda >= venc:
        raise ValueError("Horizonte alcanca o vencimento do titulo")
    spread = (taxa_venda_pct - taxa_compra_pct) if taxa_venda_pct is not None else 0.0
    taxa_saida = taxa_compra_pct + delta_pp + spread

    datas, valores = fluxos(tipo_titulo, venc)
    du0 = dias_uteis(liq0, datas) / 252
    du1 = dias_uteis(data_venda, datas) / 252
    vivos0, vivos1 = du0 > 0, du1 > 0

    indexado = tipo_titulo not in TIPOS_NOMINAIS  # IPCA, IGP-M e Selic corrigem o VNA
    g = (1 + indexador_aa_pct / 100) if indexado else 1.0

    def _vna_rel(ate) -> float:
        # crescimento do VNA (base 1 em liq0) — dias uteis, como a Selic/IPCA pro rata
        return g ** (dias_uteis(liq0, ate) / 252)

    # Escala: fatores em "unidade do titulo"; VNA0 implicito = PU / fator0
    f0 = _fator(valores[vivos0], du0[vivos0], taxa_compra_pct)
    vna0 = pu_compra / f0
    vna1 = vna0 * _vna_rel(data_venda)
    f1_saida = _fator(valores[vivos1], du1[vivos1], taxa_saida)
    f1_sem_choque = _fator(valores[vivos1], du1[vivos1], taxa_compra_pct + spread)
    pu_venda = vna1 * f1_saida
    efeito_taxa = f1_saida / f1_sem_choque - 1

    recebidos_mask = vivos0 & ~vivos1
    fluxos_recebidos = float(
        sum(vna0 * _vna_rel(pd.Timestamp(d)) * v
            for d, v in zip(datas[recebidos_mask], valores[recebidos_mask]))
    )

    dias = (data_venda - liq0).days
    rendimento = pu_venda + fluxos_recebidos - pu_compra
    iof = max(rendimento, 0) * aliquota_iof(dias)
    aliq = aliquota_ir(dias)
    ir = max(rendimento - iof, 0) * aliq
    custodia = CUSTODIA_AA * (dias / 365) * (pu_compra + pu_venda) / 2
    liquido = rendimento - iof - ir - custodia
    ret_liq = liquido / pu_compra
    ret_liq_aa = (1 + ret_liq) ** (365 / dias) - 1 if ret_liq > -1 else -1.0

    return ResultadoSimulacao(
        data_venda=data_venda,
        dias_corridos=dias,
        pu_compra=pu_compra,
        pu_venda=pu_venda,
        fluxos_recebidos=fluxos_recebidos,
        retorno_bruto=rendimento / pu_compra,
        efeito_taxa=efeito_taxa,
        aliquota_ir=aliq,
        iof=iof,
        ir=ir,
        custodia=custodia,
        resultado_liquido=liquido,
        retorno_liquido=ret_liq,
        retorno_liquido_aa=ret_liq_aa,
    )


def matriz_cenarios(
    deltas_pp: list[float],
    horizontes_meses: list[int],
    **kwargs,
) -> pd.DataFrame:
    """Retorno liquido (fracao) para cada (delta, horizonte); NaN se passar do vencimento."""
    linhas = []
    for d in deltas_pp:
        linha = {}
        for h in horizontes_meses:
            try:
                linha[h] = simular(delta_pp=d, horizonte_meses=h, **kwargs).retorno_liquido
            except ValueError:
                linha[h] = np.nan
        linhas.append(linha)
    return pd.DataFrame(linhas, index=deltas_pp)
