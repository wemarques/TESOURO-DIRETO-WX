"""Testes do módulo de dados do dashboard."""

import pandas as pd

from src.dashboard.dados import build_summary_stats


def _ranking_sample() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "familia_normalizada": ["SELIC", "SELIC", "IPCA"],
            "tipo_titulo": ["Tesouro Selic", "Tesouro Selic", "Tesouro IPCA+"],
            "data_vencimento": pd.to_datetime(
                ["2027-03-01", "2028-03-01", "2030-08-15"]
            ),
            "taxa_compra_manha": [0.5, 0.8, 6.0],
            "liquidez_norm": [0.9, 0.7, 0.4],
            "score_a": [0.6, 0.9, 0.95],
            "score_b": [0.5, 0.85, 0.9],
        }
    )


def test_summary_stats_modo_todas():
    stats = build_summary_stats(_ranking_sample(), "TODAS")
    assert stats["modo"] == "todas"
    assert stats["total"] == 3


def test_summary_stats_por_familia():
    stats = build_summary_stats(_ranking_sample(), "SELIC", "score_a")
    assert stats["modo"] == "familia"
    assert stats["total"] == 2
    assert "0.900" in stats["melhor_score_valor"]
    assert "2028" in stats["melhor_score_titulo"]


def test_summary_stats_nao_compara_familias_no_melhor_score():
    stats = build_summary_stats(_ranking_sample(), "SELIC", "score_a")
    assert "IPCA" not in stats["melhor_score_titulo"]
