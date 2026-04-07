"""
Métricas analíticas do Tesouro Direto.

Calcula:
- Carry normalizado por grupo
- Valor relativo (z-score intragrupo)
- Liquidez normalizada
- Duration aproximada (para Fórmula B)
"""

import logging

import numpy as np
import pandas as pd

from src.utils.config import config

logger = logging.getLogger(__name__)


def _winsorize(series: pd.Series, percentil: float = 0.05) -> pd.Series:
    """Winsoriza série nos percentis inferior e superior."""
    lower = series.quantile(percentil)
    upper = series.quantile(1 - percentil)
    return series.clip(lower=lower, upper=upper)


def _minmax_norm(series: pd.Series) -> pd.Series:
    """Normalização min-max para [0, 1]."""
    smin = series.min()
    smax = series.max()
    if smax == smin:
        return pd.Series(0.5, index=series.index)
    return (series - smin) / (smax - smin)


def calcular_benchmark_grupo(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula benchmark (mediana da taxa) por célula analítica e data_base."""
    benchmarks = (
        df.groupby(["data_base", "celula_analitica"])["taxa_compra_manha"]
        .median()
        .reset_index()
        .rename(columns={"taxa_compra_manha": "benchmark_grupo"})
    )
    return df.merge(benchmarks, on=["data_base", "celula_analitica"], how="left")


def calcular_carry(df: pd.DataFrame) -> pd.DataFrame:
    """Carry = taxa_compra - benchmark do grupo."""
    df = df.copy()
    df = calcular_benchmark_grupo(df)
    df["carry"] = df["taxa_compra_manha"] - df["benchmark_grupo"]
    return df


def calcular_rv_zscore(df: pd.DataFrame) -> pd.DataFrame:
    """Valor relativo via z-score intragrupo por data_base."""
    df = df.copy()

    def _zscore_grupo(grupo: pd.DataFrame) -> pd.Series:
        taxa = grupo["taxa_compra_manha"]
        media = taxa.mean()
        std = taxa.std()
        if std == 0 or pd.isna(std):
            return pd.Series(0.0, index=grupo.index)
        return (taxa - media) / std

    df["rv_zscore"] = df.groupby(["data_base", "celula_analitica"], group_keys=False).apply(
        _zscore_grupo
    )

    return df


def calcular_liquidez(df: pd.DataFrame) -> pd.DataFrame:
    """Liquidez normalizada baseada em spread compra/venda."""
    df = df.copy()
    limite = config.analytics.limite_spread_default
    df["liquidez_raw"] = 1 - (df["spread_compra_venda"] / limite).clip(upper=1)
    df["liquidez_raw"] = df["liquidez_raw"].clip(lower=0)
    return df


def calcular_duration_aprox(df: pd.DataFrame) -> pd.DataFrame:
    """Duration aproximada (anos até vencimento como proxy simples)."""
    df = df.copy()
    # Proxy simples: para títulos bullet, duration ≈ prazo
    # Para cupom, duration < prazo — aplicar fator de desconto
    fator_cupom = df["flag_cupom"].map({True: 0.75, False: 1.0})
    df["duration_aprox"] = df["anos_ate_vencimento"] * fator_cupom
    return df


def calcular_metricas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pipeline completo de cálculo de métricas.

    Args:
        df: DataFrame enriquecido

    Returns:
        DataFrame com todas as métricas calculadas e normalizadas
    """
    cfg = config.analytics

    df = calcular_carry(df)
    df = calcular_rv_zscore(df)
    df = calcular_liquidez(df)
    df = calcular_duration_aprox(df)

    # Normalizar por data_base
    for data, grupo in df.groupby("data_base"):
        mask = df["data_base"] == data

        # Carry normalizado (winsorize + minmax)
        carry_w = _winsorize(grupo["carry"], cfg.winsorize_percentil)
        df.loc[mask, "carry_norm"] = _minmax_norm(carry_w).values

        # RV normalizado (clip z-score para [0,1])
        rv_clipped = grupo["rv_zscore"].clip(-3, 3)
        df.loc[mask, "rv_norm"] = _minmax_norm(rv_clipped).values

        # Liquidez normalizada
        df.loc[mask, "liquidez_norm"] = _minmax_norm(grupo["liquidez_raw"]).values

        # Duration normalizada (para Fórmula B)
        dur_w = _winsorize(grupo["duration_aprox"], cfg.winsorize_percentil)
        df.loc[mask, "duration_norm"] = _minmax_norm(dur_w).values

    logger.info("Métricas calculadas para %d registros", len(df))

    return df
