"""
Fórmulas de score de oportunidade.

Implementa 3 fórmulas candidatas:
- A: Score base (carry + RV + liquidez)
- B: Score ajustado por risco (+ penalidade de duration)
- C: Score por resíduo de curva (fase madura)
"""

import logging

import pandas as pd

from src.utils.constants import PESOS_FORMULA_A, PESOS_FORMULA_B

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


def calcular_score_c(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fórmula C — Score por resíduo de curva ajustada.

    Placeholder — requer implementação de curva Nelson-Siegel-Svensson
    em src/analytics/curva.py.
    """
    raise NotImplementedError(
        "Fórmula C requer curva teórica ajustada. "
        "Implemente src/analytics/curva.py primeiro."
    )
