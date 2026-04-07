"""
Enriquecimento da base do Tesouro Direto.

Adiciona variáveis derivadas:
- Prazo remanescente (dias e anos)
- Família normalizada e grupo analítico
- Bucket de prazo
- Flags de estrutura (cupom, indexação, produto)
- Spread de compra/venda (proxy de liquidez)
- Chave única do título
"""

import logging

import pandas as pd

from src.utils.constants import (
    FAMILIA_PARA_GRUPO,
    LIMITES_BUCKET,
    MAPA_FAMILIA,
    BucketPrazo,
    DATA_ENRIQUECIDO,
)

logger = logging.getLogger(__name__)


def _classificar_bucket(anos: float) -> str:
    """Classifica prazo remanescente em bucket."""
    for bucket, (minimo, maximo) in LIMITES_BUCKET.items():
        if minimo < anos <= maximo:
            return bucket.value
    return BucketPrazo.ULTRA.value


def enriquecer(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enriquece base padronizada com variáveis derivadas.

    Args:
        df: DataFrame já padronizado (saída de padronizar())

    Returns:
        DataFrame enriquecido com variáveis adicionais.
    """
    df = df.copy()

    # Prazo remanescente
    df["dias_ate_vencimento"] = (df["data_vencimento"] - df["data_base"]).dt.days
    df["anos_ate_vencimento"] = df["dias_ate_vencimento"] / 365.25

    # Família normalizada
    df["familia_normalizada"] = df["tipo_titulo"].map(
        {k: v.value for k, v in MAPA_FAMILIA.items()}
    )

    # Grupo analítico
    familia_para_grupo_str = {k.value: v.value for k, v in FAMILIA_PARA_GRUPO.items()}
    df["grupo_analitico"] = df["familia_normalizada"].map(familia_para_grupo_str)

    # Bucket de prazo
    df["bucket_prazo"] = df["anos_ate_vencimento"].apply(_classificar_bucket)

    # Flags de estrutura
    df["flag_cupom"] = df["tipo_titulo"].str.contains("Juros Semestrais", case=False, na=False)
    df["flag_indexado_inflacao"] = df["tipo_titulo"].str.contains(
        "IPCA|IGPM", case=False, na=False
    )
    df["flag_pos_fixado"] = df["tipo_titulo"].str.contains("Selic", case=False, na=False)
    df["flag_produto_planejamento"] = df["tipo_titulo"].str.contains(
        "Educa|Renda", case=False, na=False
    )

    # Spread compra/venda (proxy de liquidez)
    df["spread_compra_venda"] = (
        (df["pu_compra_manha"] - df["pu_venda_manha"]).abs() / df["pu_base_manha"]
    )

    # Chave única do título
    df["chave_titulo"] = (
        df["familia_normalizada"] + "_" + df["data_vencimento"].dt.strftime("%Y%m%d")
    )

    # Célula analítica (para ranking)
    df["celula_analitica"] = df["grupo_analitico"] + "_" + df["bucket_prazo"]

    # Remover linhas com prazo negativo
    invalidos = df["dias_ate_vencimento"] <= 0
    if invalidos.any():
        logger.warning("Removendo %d linhas com prazo <= 0", invalidos.sum())
        df = df[~invalidos].reset_index(drop=True)

    # Salvar
    DATA_ENRIQUECIDO.mkdir(parents=True, exist_ok=True)
    saida = DATA_ENRIQUECIDO / "base_enriquecida.parquet"
    df.to_parquet(saida, index=False)

    logger.info(
        "Base enriquecida: %d registros, %d colunas, %d células analíticas",
        len(df),
        len(df.columns),
        df["celula_analitica"].nunique(),
    )

    return df
