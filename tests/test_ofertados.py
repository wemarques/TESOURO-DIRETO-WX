"""Testes da lista de titulos ofertados e do filtro do 'Melhor Titulo do Dia'."""

import pandas as pd

from src.dashboard.callbacks import recomendar_titulo
from src.utils.ofertados import (
    ARQUIVO_OFERTADOS,
    carregar_ofertados,
    marcar_disponibilidade,
)

CSV_OFICIAL = (
    "﻿Título;Rendimento anual do título;Investimento mínimo;"
    "Preço unitário de investimento;Vencimento do Título\r\n"
    "Tesouro Prefixado 2029;12,31%;R$ 7,74;R$ 774,74;01/01/2029\r\n"
    "Tesouro IPCA+ 2032;IPCA + 6,68%;R$ 32,72;R$ 3.272,73;15/08/2032\r\n"
    "Tesouro Renda+ Aposentadoria Extra 2030;IPCA + 6,61%;R$ 21,96;R$ 2.196,96;15/12/2049\r\n"
    "Tesouro Reserva 2036;SELIC;R$ 1,00;R$ 11,095665;01/01/2036\r\n"
)


def _ranking() -> pd.DataFrame:
    """Snapshot sintetico: o Prefixado 2027 tem o melhor score mas nao esta a venda."""
    return pd.DataFrame(
        {
            "tipo_titulo": [
                "Tesouro Prefixado",
                "Tesouro Prefixado",
                "Tesouro IPCA+",
                "Tesouro Renda+ Aposentadoria Extra",
            ],
            "data_vencimento": pd.to_datetime(
                ["2027-01-01", "2029-01-01", "2032-08-15", "2049-12-15"]
            ),
            "anos_ate_vencimento": [0.24, 2.24, 5.86, 23.2],
            "familia_normalizada": ["PRE", "PRE", "IPCA", "RENDA"],
            "bucket_prazo": ["CURTO", "INTER", "LONGO", "ULTRA"],
            "grupo_analitico": ["NOMINAL_BULLET", "NOMINAL_BULLET", "REAL_BULLET", "RENDA"],
            "score_a": [0.90, 0.60, 0.50, 0.40],
            "score_b": [0.90, 0.60, 0.50, 0.40],
            "score_c": [0.90, 0.60, 0.50, 0.40],
        }
    )


def _gravar_csv(tmp_path, conteudo: str = CSV_OFICIAL):
    caminho = tmp_path / "titulos_ofertados.csv"
    caminho.write_bytes(conteudo.encode("utf-8"))
    return caminho


def test_carrega_csv_oficial_com_bom_e_crlf(tmp_path):
    ofertados = carregar_ofertados(_gravar_csv(tmp_path))
    assert ("Tesouro Prefixado", pd.Timestamp("2029-01-01")) in ofertados
    assert ("Tesouro IPCA+", pd.Timestamp("2032-08-15")) in ofertados


def test_renda_casa_pelo_vencimento_e_nao_pelo_ano_do_nome(tmp_path):
    ofertados = carregar_ofertados(_gravar_csv(tmp_path))
    assert ("Tesouro Renda+ Aposentadoria Extra", pd.Timestamp("2049-12-15")) in ofertados


def test_tesouro_reserva_fica_fora_do_escopo(tmp_path):
    ofertados = carregar_ofertados(_gravar_csv(tmp_path))
    assert all("Reserva" not in tipo for tipo, _ in ofertados)
    assert len(ofertados) == 3


def test_arquivo_ausente_nao_filtra(tmp_path):
    assert carregar_ofertados(tmp_path / "nao_existe.csv") is None
    df = marcar_disponibilidade(_ranking(), None)
    assert df["disponivel_compra"].all()


def test_marca_titulo_fora_de_venda(tmp_path):
    df = marcar_disponibilidade(_ranking(), carregar_ofertados(_gravar_csv(tmp_path)))
    assert df["disponivel_compra"].tolist() == [False, True, True, True]


def test_melhor_titulo_ignora_titulo_fora_de_venda(tmp_path):
    df = marcar_disponibilidade(_ranking(), carregar_ofertados(_gravar_csv(tmp_path)))
    melhor, alternativas, *_ = recomendar_titulo("curto", "arrojado", "nao", df)
    assert melhor["data_vencimento"] != pd.Timestamp("2027-01-01")
    assert alternativas["disponivel_compra"].all()


def test_medio_prazo_exige_dois_anos():
    # Sem lista de ofertados: o Prefixado 2027 (0,24 ano) ainda e excluido pelo prazo.
    melhor, alternativas, *_ = recomendar_titulo("medio", "arrojado", "nao", _ranking())
    assert melhor["anos_ate_vencimento"] >= 2.0
    assert (alternativas["anos_ate_vencimento"] >= 2.0).all()


def test_lista_versionada_no_repositorio_e_valida():
    ofertados = carregar_ofertados(ARQUIVO_OFERTADOS)
    assert ofertados, "config/titulos_ofertados.csv ausente ou invalido"
    assert ("Tesouro Prefixado", pd.Timestamp("2027-01-01")) not in ofertados
