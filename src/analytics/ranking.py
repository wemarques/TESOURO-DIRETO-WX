"""
Ranking de títulos por célula analítica.

Gera ranking separado por grupo analítico + bucket de prazo,
respeitando a regra de que títulos de famílias diferentes
NUNCA são comparados diretamente.
"""

import logging
from datetime import datetime

import pandas as pd

from src.utils.config import config

logger = logging.getLogger(__name__)


def gerar_ranking(
    df: pd.DataFrame,
    coluna_score: str = "score_a",
    data_referencia: str | None = None,
) -> pd.DataFrame:
    """
    Gera ranking de títulos por célula analítica.

    Args:
        df: DataFrame com scores calculados
        coluna_score: Nome da coluna de score a usar
        data_referencia: Data-base do snapshot (None = mais recente)

    Returns:
        DataFrame com ranking, posição e metadados
    """
    if data_referencia is None:
        data_referencia = df["data_base"].max()
    else:
        data_referencia = pd.Timestamp(data_referencia)

    snapshot = df[df["data_base"] == data_referencia].copy()

    if snapshot.empty:
        logger.warning("Nenhum dado para data_referencia=%s", data_referencia)
        return pd.DataFrame()

    # Verificar mínimo de observações por célula
    min_obs = config.analytics.min_observacoes_celula
    contagem = snapshot.groupby("celula_analitica").size()
    celulas_validas = contagem[contagem >= min_obs].index

    # Filtrar apenas células com massa suficiente
    snapshot = snapshot[snapshot["celula_analitica"].isin(celulas_validas)]

    # Ranking por célula analítica
    snapshot["posicao_celula"] = snapshot.groupby("celula_analitica")[coluna_score].rank(
        ascending=False, method="min"
    )

    # Ranking global (informativo, NÃO para decisão)
    snapshot["posicao_global"] = snapshot[coluna_score].rank(
        ascending=False, method="min"
    )

    # Selecionar colunas do ranking
    colunas_ranking = [
        "data_base",
        "tipo_titulo",
        "data_vencimento",
        "anos_ate_vencimento",
        "familia_normalizada",
        "grupo_analitico",
        "bucket_prazo",
        "celula_analitica",
        "taxa_compra_manha",
        "taxa_venda_manha",
        "spread_compra_venda",
        "carry",
        "carry_norm",
        "rv_zscore",
        "rv_norm",
        "liquidez_norm",
        coluna_score,
        "posicao_celula",
        "posicao_global",
    ]

    # Manter apenas colunas existentes
    colunas_ranking = [c for c in colunas_ranking if c in snapshot.columns]

    resultado = (
        snapshot[colunas_ranking]
        .sort_values(["celula_analitica", "posicao_celula"])
        .reset_index(drop=True)
    )

    # Metadados
    resultado.attrs["data_referencia"] = str(data_referencia)
    resultado.attrs["formula"] = coluna_score
    resultado.attrs["timestamp"] = datetime.now().isoformat()
    resultado.attrs["celulas_ranqueadas"] = len(celulas_validas)
    resultado.attrs["titulos_ranqueados"] = len(resultado)

    logger.info(
        "Ranking gerado: %d títulos em %d células — data_ref=%s",
        len(resultado),
        len(celulas_validas),
        data_referencia,
    )

    return resultado
