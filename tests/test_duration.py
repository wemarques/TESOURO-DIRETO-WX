"""Testes do engine de duration (Fase 1 do plano de marcacao a mercado).

Valores de referencia: casos numericos do video "Como Ficar Rico com a
Marcacao a Mercado no Tesouro Direto" e PUs publicados pelo Tesouro (CKAN).
"""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from src.analytics.calendario import dias_uteis, e_dia_util, feriados_ano
from src.analytics.duration import (
    calcular_duration,
    decompor_retorno,
    fluxos,
    inflacao_implicita,
    metricas_risco,
    preco_relativo,
    valor_presente,
    variacao_exata,
    vna_implicito,
)

DATA = "2026-10-07"  # liquidacao de compra: 08/10/2026


# --- ancoras do video --------------------------------------------------------

@pytest.mark.parametrize(
    "taxa, anos, esperado",
    [(13.81, 1, 878.65), (20.0, 1, 833.33), (5.0, 1, 952.38), (13.81, 10, 274.28)],
)
def test_valor_presente_casos_do_video(taxa, anos, esperado):
    # o video trunca (878,657 -> 878,65); tolerancia de 1 centavo
    assert valor_presente(1000, taxa, anos) == pytest.approx(esperado, abs=0.01)


def test_inflacao_implicita_fisher():
    assert inflacao_implicita(13.81, 7.38) == pytest.approx(5.99, abs=0.005)


# --- calendario ANBIMA -------------------------------------------------------

def test_feriados_moveis_2026():
    f = feriados_ano(2026)
    for d in [date(2026, 2, 16), date(2026, 2, 17), date(2026, 4, 3), date(2026, 6, 4)]:
        assert d in f
    assert date(2026, 11, 20) in f  # Consciencia Negra (nacional desde 2024)
    assert date(2023, 11, 20) not in feriados_ano(2023)


def test_dias_uteis_pula_fim_de_semana_e_feriado():
    assert not e_dia_util("2026-04-03")  # Sexta-feira Santa
    assert dias_uteis("2026-04-02", "2026-04-07") == 2  # qui, (sex feriado), seg


# --- reproducao de PUs publicados (centavos) ---------------------------------

def test_pu_prefixado_reproduz_tesouro():
    assert preco_relativo("Tesouro Prefixado", "2029-01-01", DATA, 12.55) == pytest.approx(
        770.39, abs=0.01
    )


def test_pu_prefixado_juros_semestrais_reproduz_tesouro():
    pu = preco_relativo("Tesouro Prefixado com Juros Semestrais", "2037-01-01", DATA, 12.90)
    assert pu == pytest.approx(874.46, abs=0.01)


def test_vna_implicito_igual_em_todos_os_titulos_ipca():
    """Mesmo dia => mesmo VNA. Valida fluxos de NTN-B, NTN-B P, Renda+ e Educa+."""
    casos = [
        ("Tesouro IPCA+", "2029-05-15", 6.91, 4004.26),
        ("Tesouro IPCA+", "2050-08-15", 6.62, 1040.62),
        ("Tesouro IPCA+ com Juros Semestrais", "2060-08-15", 6.62, 4431.75),
        ("Tesouro Renda+ Aposentadoria Extra", "2084-12-15", 6.47, 251.09),
        ("Tesouro Educa+", "2048-12-15", 6.63, 1356.40),
    ]
    vnas = [vna_implicito(t, v, DATA, i, pu) for t, v, i, pu in casos]
    assert max(vnas) - min(vnas) < 0.05 * 10  # < R$ 0,50 num VNA de ~R$ 4.750
    assert np.mean(vnas) == pytest.approx(4753.63, abs=0.5)


# --- fluxos -----------------------------------------------------------------

def test_fluxos_renda_e_educa():
    datas, valores = fluxos("Tesouro Renda+ Aposentadoria Extra", "2084-12-15")
    assert len(datas) == 240 and str(datas[0]) == "2065-01-15"
    assert valores.sum() == pytest.approx(1.0)
    datas, _ = fluxos("Tesouro Educa+", "2048-12-15")
    assert len(datas) == 60 and str(datas[0]) == "2044-01-15"


def test_fluxos_respeitam_data_inicial():
    datas, _ = fluxos("Tesouro Educa+", "2030-12-15", inicio=pd.Timestamp("2026-10-08"))
    assert str(datas[0]) == "2026-10-15" and len(datas) == 51


# --- duration e sensibilidade -------------------------------------------------

def test_duration_renda_2065_na_faixa_do_video():
    m = metricas_risco("Tesouro Renda+ Aposentadoria Extra", "2084-12-15", DATA, 6.47)
    assert 45 < m.duration_macaulay < 47
    assert m.duration_modificada == pytest.approx(m.duration_macaulay / 1.0647)


def test_aproximacao_linear_subestima_alta_e_superestima_queda():
    t, v, i = "Tesouro Renda+ Aposentadoria Extra", "2084-12-15", 6.47
    m = metricas_risco(t, v, DATA, i)
    exato_queda, exato_alta = variacao_exata(t, v, DATA, i, -1), variacao_exata(t, v, DATA, i, 1)
    assert exato_queda > m.variacao_aprox(-1, com_convexidade=False)
    assert exato_alta > m.variacao_aprox(1, com_convexidade=False)
    # convexidade aproxima bem melhor que o linear
    assert abs(m.variacao_aprox(-1) - exato_queda) < abs(
        m.variacao_aprox(-1, com_convexidade=False) - exato_queda
    )


def test_bullet_duration_igual_prazo():
    m = metricas_risco("Tesouro Prefixado", "2029-01-01", DATA, 12.55)
    assert m.duration_macaulay == pytest.approx(dias_uteis("2026-10-08", "2029-01-01") / 252)


def test_calcular_duration_vetorizado_bate_com_escalar_e_trata_selic():
    df = pd.DataFrame(
        {
            "tipo_titulo": ["Tesouro Renda+ Aposentadoria Extra", "Tesouro Selic"],
            "data_vencimento": pd.to_datetime(["2084-12-15", "2031-03-01"]),
            "data_base": pd.to_datetime([DATA, DATA]),
            "taxa_compra_manha": [6.47, 0.09],
        }
    )
    out = calcular_duration(df)
    m = metricas_risco("Tesouro Renda+ Aposentadoria Extra", "2084-12-15", DATA, 6.47)
    assert out.loc[0, "duration_modificada"] == pytest.approx(m.duration_modificada)
    assert out.loc[0, "var_pct_taxa_menos_1pp"] == pytest.approx(
        variacao_exata("Tesouro Renda+ Aposentadoria Extra", "2084-12-15", DATA, 6.47, -1)
    )
    assert out.loc[1, "duration_risco"] == 0.0
    assert np.isnan(out.loc[1, "var_pct_taxa_menos_1pp"])


# --- caso real do video: Renda+ 2065, 23/01/2025 -> 10/07/2025 ----------------

def test_backtest_renda_2065_decomposicao():
    """Taxa 7,49% -> 7,08% e PU R$ 132,82 -> R$ 169,03 (base CKAN).

    O ganho total (+27,3%) separa-se em efeito-taxa (marcacao) e carrego +
    IPCA. O carrego tem de bater com a variacao do VNA implicito (medida em
    outro titulo, o IPCA+ 2029) mais o carrego real a taxa antiga.
    """
    t, v = "Tesouro Renda+ Aposentadoria Extra", "2084-12-15"
    d = decompor_retorno(t, v, "2025-01-23", 7.49, 132.82, "2025-07-10", 7.08, 169.03)
    assert d["retorno_total"] == pytest.approx(169.03 / 132.82 - 1)
    assert (1 + d["efeito_taxa"]) * (1 + d["carrego_indexacao"]) == pytest.approx(
        1 + d["retorno_total"]
    )
    assert 0.18 < d["efeito_taxa"] < 0.22  # queda de 0,41 p.p. com duration ~47

    vna0 = vna_implicito("Tesouro IPCA+", "2029-05-15", "2025-01-23", 7.90, 3179.82)
    vna1 = vna_implicito("Tesouro IPCA+", "2029-05-15", "2025-07-10", 7.85, 3394.10)
    du = dias_uteis("2025-01-24", "2025-07-11")
    carrego_esperado = (vna1 / vna0) * 1.0749 ** (du / 252) - 1
    assert d["carrego_indexacao"] == pytest.approx(carrego_esperado, abs=0.002)
