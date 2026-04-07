"""
Fórmulas de score de oportunidade.

Implementa 3 fórmulas candidatas:
- A: Score base (carry + RV + liquidez)
- B: Score ajustado por risco (+ penalidade de duration)
- C: Score por resíduo de curva (fase madura)
"""

import logging

import pandas as pd

import numpy as np

from src.utils.constants import PESOS_FORMULA_A, PESOS_FORMULA_B, PESOS_FORMULA_C

logger = logging.getLogger(__name__)


def calcular_score_a(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fórmula A — Score base de oportunidade.

    Score_A = 0.40 × Carry_Norm + 0.40 × RV_Norm + 0.20 × Liquidez_Norm

    Requer colunas: carry_norm, rv_norm, liquidez_norm
    """
    df = df.copy()
    p = PESOS_FORMULA_A

    df["score_a"] = (
        p["carry"] * df["carry_norm"].fillna(0)
        + p["rv"] * df["rv_norm"].fillna(0)
        + p["liquidez"] * df["liquidez_norm"].fillna(0)
    )

    logger.info(
        "Score A calculado — média=%.3f, min=%.3f, max=%.3f",
        df["score_a"].mean(),
        df["score_a"].min(),
        df["score_a"].max(),
    )

    return df


def calcular_score_b(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fórmula B — Score ajustado por risco de taxa.

    Score_B = 0.35 × Carry + 0.30 × RV + 0.15 × Liquidez + 0.20 × Risco

    Risco_Norm = 1 - duration_norm (penaliza duration alta)
    Requer colunas: carry_norm, rv_norm, liquidez_norm, duration_norm
    """
    df = df.copy()
    p = PESOS_FORMULA_B

    df["risco_norm"] = 1 - df["duration_norm"].fillna(0.5)

    df["score_b"] = (
        p["carry"] * df["carry_norm"].fillna(0)
        + p["rv"] * df["rv_norm"].fillna(0)
        + p["liquidez"] * df["liquidez_norm"].fillna(0)
        + p["risco"] * df["risco_norm"].fillna(0)
    )

    logger.info(
        "Score B calculado — média=%.3f, min=%.3f, max=%.3f",
        df["score_b"].mean(),
        df["score_b"].min(),
        df["score_b"].max(),
    )

    return df


def _minmax_norm_group(series: pd.Series) -> pd.Series:
    """Normalização min-max dentro de um grupo para [0, 1]."""
    smin = series.min()
    smax = series.max()
    if smax == smin:
        return pd.Series(0.5, index=series.index)
    return (series - smin) / (smax - smin)


def calcular_score_c(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fórmula C — Score por resíduo de curva ajustada (Nelson-Siegel-Svensson).

    Score_C = 0.30 × Carry_Norm + 0.40 × Residuo_Curva_Norm
            + 0.15 × Rolldown_Norm + 0.15 × Liquidez_Norm

    Requer colunas: carry_norm, liquidez_norm, residuo_curva, rolldown, curva_ajustada
    Títulos sem curva ajustada recebem score_a como fallback.
    """
    df = df.copy()
    p = PESOS_FORMULA_C

    # Normalizar resíduo e rolldown por data_base (apenas onde curva foi ajustada)
    df["residuo_curva_norm"] = np.nan
    df["rolldown_norm"] = np.nan

    mask_curva = df["curva_ajustada"].fillna(False).astype(bool)

    for data, grupo in df[mask_curva].groupby("data_base"):
        idx = grupo.index
        df.loc[idx, "residuo_curva_norm"] = _minmax_norm_group(
            grupo["residuo_curva"].fillna(0)
        ).values
        df.loc[idx, "rolldown_norm"] = _minmax_norm_group(
            grupo["rolldown"].fillna(0)
        ).values

    # Score C onde há curva ajustada
    df["score_c"] = np.where(
        mask_curva,
        (
            p["carry"] * df["carry_norm"].fillna(0)
            + p["residuo_curva"] * df["residuo_curva_norm"].fillna(0)
            + p["rolldown"] * df["rolldown_norm"].fillna(0)
            + p["liquidez"] * df["liquidez_norm"].fillna(0)
        ),
        np.nan,
    )

    # Fallback: onde score_c é NaN, usar score_a
    fallback_mask = df["score_c"].isna()
    if fallback_mask.any():
        df.loc[fallback_mask, "score_c"] = df.loc[fallback_mask, "score_a"]
        n_fallback = fallback_mask.sum()
        logger.info("Score C fallback para score_a em %d registros", n_fallback)

    logger.info(
        "Score C calculado — média=%.3f, min=%.3f, max=%.3f",
        df["score_c"].mean(),
        df["score_c"].min(),
        df["score_c"].max(),
    )

    return df
