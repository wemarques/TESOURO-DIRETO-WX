"""Testes do simulador de marcacao a mercado (Fase 5)."""

import numpy as np
import pandas as pd
import pytest

from src.analytics.duration import decompor_retorno, variacao_exata
from src.analytics.simulador import (
    aliquota_iof,
    aliquota_ir,
    matriz_cenarios,
    proximo_degrau_ir,
    simular,
)

DATA = "2026-10-07"


@pytest.mark.parametrize(
    "dias, aliquota", [(1, 0.225), (180, 0.225), (181, 0.20), (360, 0.20),
                       (361, 0.175), (720, 0.175), (721, 0.15)],
)
def test_ir_regressivo(dias, aliquota):
    assert aliquota_ir(dias) == aliquota


def test_proximo_degrau_ir():
    assert proximo_degrau_ir(170) == (11, 0.20)
    assert proximo_degrau_ir(800) is None


def test_iof_regressivo():
    assert aliquota_iof(1) == 0.96
    assert aliquota_iof(29) == 0.03
    assert aliquota_iof(30) == 0.0


def test_prefixado_sem_choque_rende_a_taxa_contratada_bruta():
    """Sem mudanca de taxa e sem spread, o PU cresce a propria taxa (carrego puro)."""
    r = simular("Tesouro Prefixado", "2032-01-01", DATA, 12.82, 534.42, 0.0, 12)
    from src.analytics.calendario import dias_uteis

    du = dias_uteis("2026-10-08", r.data_venda)
    assert r.pu_venda / r.pu_compra == pytest.approx(1.1282 ** (du / 252), rel=1e-4)
    assert r.efeito_taxa == pytest.approx(0.0, abs=1e-12)


def test_choque_imediato_bate_com_variacao_exata():
    """Horizonte curto: o efeito-taxa converge para a reprecificacao exata."""
    r = simular("Tesouro Prefixado", "2032-01-01", DATA, 12.82, 534.42, -1.0, 1)
    exato = variacao_exata("Tesouro Prefixado", "2032-01-01", DATA, 12.82, -1.0)
    assert r.efeito_taxa == pytest.approx(exato, abs=0.002)


def test_liquido_desconta_ir_custodia_e_spread_de_venda():
    r = simular(
        "Tesouro Prefixado", "2032-01-01", DATA, 12.82, 534.42, 0.0, 12, taxa_venda_pct=12.94
    )
    sem_spread = simular("Tesouro Prefixado", "2032-01-01", DATA, 12.82, 534.42, 0.0, 12)
    assert r.pu_venda < sem_spread.pu_venda
    assert r.retorno_liquido == pytest.approx(
        (r.pu_venda - r.pu_compra - r.ir - r.iof - r.custodia) / r.pu_compra
    )
    assert r.aliquota_ir == 0.175  # 365 dias corridos


def test_titulo_com_cupom_soma_fluxos_recebidos():
    r = simular(
        "Tesouro IPCA+ com Juros Semestrais", "2060-08-15", DATA, 6.62, 4431.75, 0.0, 12,
        indexador_aa_pct=4.58,
    )
    assert r.fluxos_recebidos > 0  # cupons de fev e ago/2027


def test_horizonte_alem_do_vencimento_falha_e_vira_nan_na_matriz():
    with pytest.raises(ValueError):
        simular("Tesouro Prefixado", "2027-01-01", DATA, 13.25, 972.24, 0.0, 6)
    m = matriz_cenarios(
        [-1.0, 0.0], [1, 6], tipo_titulo="Tesouro Prefixado", vencimento="2027-01-01",
        data_base=DATA, taxa_compra_pct=13.25, pu_compra=972.24,
    )
    assert not np.isnan(m.loc[-1.0, 1]) and np.isnan(m.loc[-1.0, 6])
    assert m.loc[-1.0, 1] > m.loc[0.0, 1]  # queda de taxa rende mais


def test_decomposicao_inclui_parcelas_recebidas_do_educa():
    """Educa+ 2030 ja paga parcelas: o PU cai, mas quem tinha recebeu o dinheiro."""
    d = decompor_retorno(
        "Tesouro Educa+", "2030-12-15", "2026-01-07", 7.5, 4000.0, DATA, 6.84, 3532.61
    )
    assert d["fluxos_recebidos"] > 0
    sem = decompor_retorno(
        "Tesouro Educa+", "2030-12-15", "2026-01-07", 7.5, 4000.0, DATA, 6.84, 3532.61,
        incluir_fluxos=False,
    )
    assert d["retorno_total"] > sem["retorno_total"]
    assert d["efeito_taxa"] == sem["efeito_taxa"]
    assert pd.notna(d["carrego_indexacao"])
