"""
Construção de curvas de referência por grupo analítico.

Implementa o modelo Nelson-Siegel-Svensson (NSS) para ajuste
da estrutura a termo de juros por grupo analítico e data_base.

Referências:
- ANBIMA: Metodologia de Precificação de Títulos Públicos
- Svensson (1994): Estimating and Interpreting Forward Interest Rates
"""

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize

logger = logging.getLogger(__name__)

MIN_TITULOS_CURVA = 4  # Mínimo de títulos para ajustar curva


@dataclass
class ParametrosNSS:
    """Parâmetros estimados do modelo Nelson-Siegel-Svensson."""

    beta0: float  # Nível de longo prazo
    beta1: float  # Inclinação (slope)
    beta2: float  # Curvatura 1
    beta3: float  # Curvatura 2
    tau1: float  # Fator de decaimento 1
    tau2: float  # Fator de decaimento 2
    rmse: float  # Erro quadrático médio do ajuste
    n_pontos: int  # Quantidade de pontos usados


def nss_yield(t: np.ndarray, beta0: float, beta1: float, beta2: float,
              beta3: float, tau1: float, tau2: float) -> np.ndarray:
    """
    Calcula a taxa teórica pelo modelo Nelson-Siegel-Svensson.

    y(t) = β0 + β1 × [(1 - e^(-t/τ1)) / (t/τ1)]
              + β2 × [(1 - e^(-t/τ1)) / (t/τ1) - e^(-t/τ1)]
              + β3 × [(1 - e^(-t/τ2)) / (t/τ2) - e^(-t/τ2)]

    Args:
        t: Prazos em anos (array)
        beta0..beta3: Parâmetros do modelo
        tau1, tau2: Fatores de decaimento

    Returns:
        Array com taxas teóricas
    """
    t = np.asarray(t, dtype=float)
    # Evitar divisão por zero em t=0
    t_safe = np.maximum(t, 1e-6)

    x1 = t_safe / tau1
    x2 = t_safe / tau2

    term1 = (1 - np.exp(-x1)) / x1
    term2 = term1 - np.exp(-x1)
    term3 = (1 - np.exp(-x2)) / x2 - np.exp(-x2)

    return beta0 + beta1 * term1 + beta2 * term2 + beta3 * term3


def _objetivo_nss(params: np.ndarray, t: np.ndarray, y_obs: np.ndarray) -> float:
    """Função objetivo: soma dos quadrados dos resíduos."""
    beta0, beta1, beta2, beta3, tau1, tau2 = params
    if tau1 <= 0.01 or tau2 <= 0.01:
        return 1e10
    y_pred = nss_yield(t, beta0, beta1, beta2, beta3, tau1, tau2)
    return np.sum((y_obs - y_pred) ** 2)


def ajustar_nss(prazos: np.ndarray, taxas: np.ndarray) -> ParametrosNSS | None:
    """
    Ajusta o modelo NSS aos dados observados.

    Usa múltiplos pontos iniciais e seleciona o melhor ajuste.

    Args:
        prazos: Array de prazos em anos
        taxas: Array de taxas observadas (% a.a.)

    Returns:
        ParametrosNSS com os parâmetros estimados, ou None se falhar
    """
    if len(prazos) < MIN_TITULOS_CURVA:
        return None

    t = np.asarray(prazos, dtype=float)
    y = np.asarray(taxas, dtype=float)

    # Estimativas iniciais baseadas nos dados
    y_mean = np.mean(y)
    y_range = np.ptp(y) if np.ptp(y) > 0 else 1.0
    t_med = np.median(t)

    # Múltiplos pontos iniciais para evitar mínimos locais
    chutes = [
        [y_mean, -y_range, y_range, 0.0, max(t_med, 0.5), max(t_med * 2, 1.0)],
        [y_mean, y_range, -y_range, 0.0, 1.0, 5.0],
        [y[-1], y[0] - y[-1], 0.0, 0.0, 2.0, 8.0],
        [y_mean, 0.0, y_range, -y_range, 3.0, 10.0],
    ]

    # Bounds para os parâmetros
    bounds = [
        (y.min() - 5, y.max() + 5),   # beta0
        (-30, 30),                      # beta1
        (-30, 30),                      # beta2
        (-30, 30),                      # beta3
        (0.05, 50),                     # tau1
        (0.05, 50),                     # tau2
    ]

    melhor = None
    melhor_custo = float("inf")

    for x0 in chutes:
        try:
            res = minimize(
                _objetivo_nss,
                x0=x0,
                args=(t, y),
                method="L-BFGS-B",
                bounds=bounds,
                options={"maxiter": 2000, "ftol": 1e-12},
            )
            if res.success and res.fun < melhor_custo:
                melhor = res
                melhor_custo = res.fun
        except Exception:
            continue

    if melhor is None:
        return None

    b0, b1, b2, b3, t1, t2 = melhor.x
    y_pred = nss_yield(t, b0, b1, b2, b3, t1, t2)
    rmse = float(np.sqrt(np.mean((y - y_pred) ** 2)))

    return ParametrosNSS(
        beta0=b0, beta1=b1, beta2=b2, beta3=b3,
        tau1=t1, tau2=t2, rmse=rmse, n_pontos=len(t),
    )


def calcular_curva_por_grupo(
    df: pd.DataFrame, data_referencia: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """
    Ajusta curva NSS por grupo analítico e data_base.

    Calcula taxa_teorica, residuo_curva e rolldown para cada título.
    Grupos com menos de MIN_TITULOS_CURVA títulos ficam sem curva.

    Args:
        df: DataFrame com colunas anos_ate_vencimento, taxa_compra_manha,
            celula_analitica, grupo_analitico, data_base
        data_referencia: Se informado, só ajusta curvas para essa data
            (muito mais rápido). Se None, ajusta para todas as datas.

    Returns:
        DataFrame com colunas adicionais: taxa_teorica, residuo_curva,
        rolldown, curva_ajustada (bool)
    """
    df = df.copy()
    df["taxa_teorica"] = np.nan
    df["residuo_curva"] = np.nan
    df["rolldown"] = np.nan
    df["curva_ajustada"] = False

    # Filtrar apenas a data de referência se informada
    if data_referencia is not None:
        df_calc = df[df["data_base"] == data_referencia]
    else:
        df_calc = df

    grupos_processados = 0
    grupos_fallback = 0

    for (data, grupo_analitico), idx_grupo in df_calc.groupby(
        ["data_base", "grupo_analitico"]
    ).groups.items():
        sub = df.loc[idx_grupo]
        prazos = sub["anos_ate_vencimento"].values
        taxas = sub["taxa_compra_manha"].values

        # Filtrar NaN
        mask_valido = ~(np.isnan(prazos) | np.isnan(taxas)) & (prazos > 0)
        if mask_valido.sum() < MIN_TITULOS_CURVA:
            grupos_fallback += 1
            continue

        prazos_v = prazos[mask_valido]
        taxas_v = taxas[mask_valido]

        params = ajustar_nss(prazos_v, taxas_v)
        if params is None:
            grupos_fallback += 1
            continue

        # Calcular taxa teórica para todos os títulos do grupo
        taxa_teo = nss_yield(
            prazos, params.beta0, params.beta1, params.beta2,
            params.beta3, params.tau1, params.tau2,
        )
        df.loc[idx_grupo, "taxa_teorica"] = taxa_teo

        # Resíduo: observada - teórica (positivo = pagando mais que a curva)
        df.loc[idx_grupo, "residuo_curva"] = taxas - taxa_teo

        # Rolldown: benefício de 6 meses caminhando na curva
        prazos_menos_6m = np.maximum(prazos - 0.5, 0.01)
        taxa_teo_6m = nss_yield(
            prazos_menos_6m, params.beta0, params.beta1, params.beta2,
            params.beta3, params.tau1, params.tau2,
        )
        # Rolldown positivo = curva descendente naquele trecho = benefício
        df.loc[idx_grupo, "rolldown"] = taxa_teo - taxa_teo_6m

        df.loc[idx_grupo, "curva_ajustada"] = True
        grupos_processados += 1

    logger.info(
        "Curvas NSS ajustadas: %d grupos OK, %d fallback (< %d titulos)",
        grupos_processados, grupos_fallback, MIN_TITULOS_CURVA,
    )

    return df


def obter_curva_snapshot(
    df: pd.DataFrame, grupo_analitico: str, data_base: pd.Timestamp | None = None,
) -> dict | None:
    """
    Retorna os parâmetros da curva NSS para um grupo e data específicos.

    Útil para visualização no dashboard.

    Returns:
        Dict com parâmetros NSS e range de prazos, ou None se insuficiente.
    """
    if data_base is None:
        data_base = df["data_base"].max()

    sub = df[
        (df["data_base"] == data_base) & (df["grupo_analitico"] == grupo_analitico)
    ]

    prazos = sub["anos_ate_vencimento"].values
    taxas = sub["taxa_compra_manha"].values

    mask = ~(np.isnan(prazos) | np.isnan(taxas)) & (prazos > 0)
    if mask.sum() < MIN_TITULOS_CURVA:
        return None

    params = ajustar_nss(prazos[mask], taxas[mask])
    if params is None:
        return None

    # Gerar curva suave para plotagem
    t_min, t_max = prazos[mask].min(), prazos[mask].max()
    t_plot = np.linspace(max(t_min * 0.8, 0.1), t_max * 1.1, 100)
    y_plot = nss_yield(
        t_plot, params.beta0, params.beta1, params.beta2,
        params.beta3, params.tau1, params.tau2,
    )

    return {
        "params": params,
        "prazos_plot": t_plot,
        "taxas_plot": y_plot,
        "prazos_obs": prazos[mask],
        "taxas_obs": taxas[mask],
    }
