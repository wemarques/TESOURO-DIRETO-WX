"""Testes do módulo de padronização."""

from pathlib import Path
import pytest


def _criar_csv_valido(path: Path) -> None:
    conteudo = (
        "Tipo Titulo;Data Vencimento;Data Base;"
        "Taxa Compra Manha;Taxa Venda Manha;"
        "PU Compra Manha;PU Venda Manha;PU Base Manha\n"
        "Tesouro Prefixado;01/01/2030;01/04/2026;"
        "13,87;13,85;650,50;651,00;650,75\n"
    )
    path.write_text(conteudo, encoding="latin-1")


class TestPadronizacao:
    def test_renomeia_colunas(self, tmp_path):
        from src.transformacao.padronizacao import padronizar
        csv = tmp_path / "teste.csv"
        _criar_csv_valido(csv)
        df = padronizar(csv)
        assert "tipo_titulo" in df.columns
        assert "Tipo Titulo" not in df.columns

    def test_converte_datas(self, tmp_path):
        from src.transformacao.padronizacao import padronizar
        import pandas as pd
        csv = tmp_path / "teste.csv"
        _criar_csv_valido(csv)
        df = padronizar(csv)
        assert pd.api.types.is_datetime64_any_dtype(df["data_base"])
