"""Testes do Score D e da margem vs CDI."""

import numpy as np
import pandas as pd
import pytest

from src.analytics.duration import calcular_duration
from src.analytics.marcacao import (
    calcular_score_d,
    cdi_esperado_12m,
    grupo_amplo,
    margem_vs_cdi,
)

DATA = pd.Timestamp("2026-10-07")


def _snapshot() -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "tipo_titulo": [
                "Tesouro Prefixado", "Tesouro Prefixado com Juros Semestrais",
                "Tesouro Renda+ Aposentadoria Extra", "Tesouro Educa+", "Tesouro Selic",
            ],
            "data_vencimento": pd.to_datetime(
                ["2029-01-01", "2037-01-01", "2084-12-15", "2048-12-15", "2031-03-01"]
            ),
            "data_base": [DATA] * 5,
            "taxa_compra_manha": [12.55, 12.90, 6.47, 6.63, 0.09],
            "liquidez_norm": [0.9, 0.5, 0.2, 0.3, 1.0],
        }
    )
    return calcular_duration(df)


def test_grupo_amplo():
    assert grupo_amplo("Tesouro Selic") == "pos"
    assert grupo_amplo("Tesouro Prefixado com Juros Semestrais") == "nominal"
    assert grupo_amplo("Tesouro Educa+") == "real"


def test_score_d_normaliza_no_grupo_amplo_e_ignora_selic():
    snap = _snapshot()
    d = calcular_score_d(snap, snap)  # historico curto => percentil neutro (0,5)
    sens = d.set_index("tipo_titulo")["sensibilidade_norm"]
    # Maior duration de cada grupo vira 1; nominal e real nao se misturam
    assert sens["Tesouro Prefixado com Juros Semestrais"] == 1.0
    assert sens["Tesouro Renda+ Aposentadoria Extra"] == 1.0
    assert sens["Tesouro Prefixado"] == 0.0 and sens["Tesouro Educa+"] == 0.0
    assert np.isnan(d.set_index("tipo_titulo").loc["Tesouro Selic", "score_d"])


def test_cdi_esperado_media_selic_e_focus():
    macro = {"selic_meta": {"valor": 13.75}, "focus_selic_fim_ano_seguinte": {"valor": 12.0}}
    assert cdi_esperado_12m(macro) == pytest.approx(12.775)
    assert cdi_esperado_12m({"selic_meta": {"valor": 13.75}}) == pytest.approx(13.65)


def _linha_pre(taxa=12.82, pu=534.42):
    return pd.Series(
        {
            "tipo_titulo": "Tesouro Prefixado", "data_vencimento": pd.Timestamp("2032-01-01"),
            "data_base": DATA, "taxa_compra_manha": taxa, "pu_compra_manha": pu,
            "taxa_venda_manha": np.nan,
        }
    )


def test_margem_zero_quando_taxa_igual_ao_cdi():
    assert margem_vs_cdi(_linha_pre(), cdi_aa_pct=12.82, indexador_aa_pct=0) == pytest.approx(
        0.0, abs=0.01
    )


def test_margem_positiva_quando_titulo_paga_mais_que_cdi():
    m = margem_vs_cdi(_linha_pre(), cdi_aa_pct=11.0, indexador_aa_pct=0)
    # ~1,8 p.p. de carry acima do CDI / duration ~4,6 => folga ~0,4 p.p.
    assert 0.3 < m < 0.5
    assert margem_vs_cdi(_linha_pre(), cdi_aa_pct=14.0, indexador_aa_pct=0) < 0
