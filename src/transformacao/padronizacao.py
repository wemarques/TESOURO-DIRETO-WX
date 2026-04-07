"""
Padronização da base do Tesouro Direto.

Transforma o CSV bruto em base limpa com:
- Colunas renomeadas para snake_case
- Datas convertidas para datetime
- Números com ponto decimal
- Tipos corretos
"""

import logging
from pathlib import Path

import pandas as pd

from src.utils.config import config
from src.utils.constants import COLUNAS_DATA, COLUNAS_NUMERICAS, DATA_PADRONIZADO, MAPA_COLUNAS

logger = logging.getLogger(__name__)


def padronizar(caminho: Path) -> pd.DataFrame:
    """
    Lê CSV bruto e retorna DataFrame padronizado.

    Args:
        caminho: Path do CSV bruto em data/raw/

    Returns:
        DataFrame com colunas renomeadas, tipos corretos, datas convertidas.
    """
    cfg = config.ingestao

    # Ler CSV com configurações corretas
    df = pd.read_csv(
        caminho,
        sep=cfg.separador_csv,
        decimal=cfg.decimal_csv,
        encoding=cfg.encoding_csv,
    )

    logger.info("CSV lido: %d linhas × %d colunas", len(df), len(df.columns))

    # Renomear colunas
    df = df.rename(columns=MAPA_COLUNAS)

    # Limpar espaços em strings
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()

    # Converter datas
    for col in COLUNAS_DATA:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format=cfg.formato_data, dayfirst=True)

    # Garantir tipos numéricos
    for col in COLUNAS_NUMERICAS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Ordenar por data_base e tipo_titulo
    df = df.sort_values(["data_base", "tipo_titulo", "data_vencimento"]).reset_index(drop=True)

    # Salvar versão padronizada
    DATA_PADRONIZADO.mkdir(parents=True, exist_ok=True)
    saida = DATA_PADRONIZADO / "base_padronizada.parquet"
    df.to_parquet(saida, index=False)

    logger.info("Base padronizada salva: %s — %d registros", saida, len(df))

    return df
