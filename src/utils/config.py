"""Configuração global do projeto Tesouro Direto WX."""

from dataclasses import dataclass, field
from pathlib import Path

from src.utils.constants import (
    DATA_AUDIT,
    DATA_ENRIQUECIDO,
    DATA_OUTPUTS,
    DATA_PADRONIZADO,
    DATA_PROCESSED,
    DATA_RAW,
    PESOS_FORMULA_A,
)


@dataclass
class ConfigIngestao:
    """Configuração do pipeline de ingestão."""

    separador_csv: str = ";"
    decimal_csv: str = ","
    encoding_csv: str = "latin-1"
    formato_data: str = "%d/%m/%Y"
    diretorio_raw: Path = DATA_RAW
    diretorio_padronizado: Path = DATA_PADRONIZADO
    diretorio_audit: Path = DATA_AUDIT
    tolerancia_volume_pct: float = 0.30  # ± 30% da média


@dataclass
class ConfigAnalytics:
    """Configuração do motor analítico."""

    formula_ativa: str = "A"
    pesos: dict = field(default_factory=lambda: PESOS_FORMULA_A.copy())
    limite_spread_default: float = 0.01  # 1% de spread relativo
    min_observacoes_celula: int = 3  # Mínimo para calcular z-score
    winsorize_percentil: float = 0.05  # Cortar 5% de cada cauda


@dataclass
class ConfigDashboard:
    """Configuração do dashboard."""

    host: str = "127.0.0.1"
    port: int = 8050
    debug: bool = True
    diretorio_outputs: Path = DATA_OUTPUTS
    titulo: str = "Tesouro Direto WX — Oportunidades"


@dataclass
class Config:
    """Configuração central do projeto."""

    ingestao: ConfigIngestao = field(default_factory=ConfigIngestao)
    analytics: ConfigAnalytics = field(default_factory=ConfigAnalytics)
    dashboard: ConfigDashboard = field(default_factory=ConfigDashboard)
    versao_metodologia: str = "v1.0.0"


# Instância global
config = Config()
