"""Testes do módulo de validação de CSV."""

import tempfile
from pathlib import Path

import pytest


def _criar_csv_valido(path: Path) -> None:
    """Cria CSV mínimo válido para testes."""
    conteudo = (
        "Tipo Titulo;Data Vencimento;Data Base;"
        "Taxa Compra Manha;Taxa Venda Manha;"
        "PU Compra Manha;PU Venda Manha;PU Base Manha\n"
        "Tesouro Prefixado;01/01/2030;01/04/2026;"
        "13,87;13,85;650,50;651,00;650,75\n"
        "Tesouro IPCA+;15/05/2035;01/04/2026;"
        "7,51;7,49;2500,00;2510,00;2505,00\n"
    )
    path.write_text(conteudo, encoding="latin-1")


class TestValidacaoFisica:
    def test_arquivo_inexistente(self):
        from src.ingestao.validacao import validar_fisico
        result = validar_fisico(Path("/tmp/nao_existe.csv"))
        assert not result["ok"]

    def test_arquivo_valido(self, tmp_path):
        from src.ingestao.validacao import validar_fisico
        csv = tmp_path / "teste.csv"
        _criar_csv_valido(csv)
        result = validar_fisico(csv)
        assert result["ok"]
        assert "hash_sha256" in result


class TestValidacaoEstrutural:
    def test_csv_valido(self, tmp_path):
        from src.ingestao.validacao import validar_estrutural
        csv = tmp_path / "teste.csv"
        _criar_csv_valido(csv)
        result = validar_estrutural(csv)
        assert result["ok"]
        assert result["linhas"] == 2

    def test_csv_sem_colunas(self, tmp_path):
        from src.ingestao.validacao import validar_estrutural
        csv = tmp_path / "teste.csv"
        csv.write_text("col1;col2\n1;2\n", encoding="latin-1")
        result = validar_estrutural(csv)
        assert not result["ok"]


class TestValidacaoCompleta:
    def test_pipeline_completo(self, tmp_path):
        from src.ingestao.validacao import validar_csv
        csv = tmp_path / "teste.csv"
        _criar_csv_valido(csv)
        result = validar_csv(csv)
        assert result["aprovado"]
        assert result["linhas"] == 2
        assert len(result["hash_sha256"]) == 64
