"""Testes da coleta macro (BCB) e do painel de condicoes da tese (Fase 4)."""

import pandas as pd
import pytest

from src.analytics.tese import condicao_curva, condicao_focus, condicao_percentil
from src.ingestao import macro as m


def test_parse_sgs_pega_ultimo_valor_valido():
    payload = [
        {"data": "02/11/2026", "valor": "13.75"},
        {"data": "03/11/2026", "valor": ""},
    ]
    assert m.parse_sgs(payload) == ("2026-11-02", 13.75)


def test_parse_focus_usa_data_mais_recente_e_filtra_ano():
    payload = {
        "value": [
            {"Data": "2026-10-02", "DataReferencia": "2027", "Mediana": 12.25},
            {"Data": "2026-10-09", "DataReferencia": "2027", "Mediana": 12.0},
            {"Data": "2026-10-09", "DataReferencia": "2028", "Mediana": 10.5},
        ]
    }
    assert m.parse_focus(payload, ano_referencia=2027) == ("2026-10-09", 12.0)


def test_odata_url_codifica_espaco_como_porcento_20():
    url = m._odata_url("Recurso", {"$filter": "Indicador eq 'IPCA'", "$top": 5})
    assert "Indicador%20eq%20'IPCA'" in url and "+" not in url


def test_falha_de_uma_fonte_mantem_valor_anterior(monkeypatch):
    monkeypatch.setattr(m, "coletar_sgs", lambda serie, n=5: ("2026-11-04", 13.75))
    monkeypatch.setattr(m, "coletar_focus_ipca_12m", lambda: (_ for _ in ()).throw(OSError("x")))
    monkeypatch.setattr(m, "coletar_focus_selic_fim_ano", lambda ano: ("2026-10-09", 12.0))
    anterior = {"focus_ipca_12m": {"valor": 4.4, "data": "2026-10-02"}}
    snap = m.montar_snapshot(anterior=anterior, hoje=pd.Timestamp("2026-10-13").date())
    assert snap["focus_ipca_12m"]["valor"] == 4.4  # mantido
    assert snap["focus_selic_fim_ano_seguinte"]["valor"] == 12.0
    assert snap["ano_focus_selic"] == 2027
    assert len(snap["erros"]) == 1


def test_valores_macro_cai_nas_constantes_sem_arquivo():
    v = m.valores_macro({})
    assert v["selic_meta"]["fonte"] == "referência manual"
    assert v["focus_ipca_12m"]["valor"] is None


# --- condicoes da tese -------------------------------------------------------

def _hist_prefixados(delta_por_dia: float) -> pd.DataFrame:
    datas = pd.bdate_range("2026-06-01", "2026-10-07")
    linhas = []
    for k, d in enumerate(datas):
        for venc, base in (("2029-01-01", 12.5), ("2032-01-01", 12.8)):
            linhas.append({
                "data_base": d, "tipo_titulo": "Tesouro Prefixado",
                "data_vencimento": pd.Timestamp(venc),
                "taxa_compra_manha": base + delta_por_dia * k,
            })
    return pd.DataFrame(linhas)


def test_curva_em_queda_atende_e_em_alta_nao():
    assert condicao_curva(_hist_prefixados(-0.01)).atendida is True
    assert condicao_curva(_hist_prefixados(+0.01)).atendida is False


def test_focus_compara_com_selic_atual():
    macro = {
        "selic_meta": {"valor": 13.75}, "focus_selic_fim_ano_seguinte": {"valor": 12.0},
        "ano_focus_selic": 2027,
    }
    c = condicao_focus(macro)
    assert c.atendida is True and "2027" in c.detalhe
    assert condicao_focus({"selic_meta": {"valor": 13.75}}).atendida is None


@pytest.mark.parametrize("taxa_hoje, esperado", [(7.9, True), (6.1, False)])
def test_percentil_da_taxa_no_historico(taxa_hoje, esperado):
    datas = pd.bdate_range("2025-01-01", "2026-10-06")
    taxas = [6.0 + (i % 20) / 10 for i in range(len(datas))]  # oscila entre 6,0% e 7,9%
    df = pd.DataFrame({"data_base": datas, "taxa_compra_manha": taxas})
    hoje = pd.DataFrame(
        {"data_base": [pd.Timestamp("2026-10-07")], "taxa_compra_manha": [taxa_hoje]}
    )
    df = pd.concat([df, hoje])
    assert condicao_percentil(df).atendida is esperado
