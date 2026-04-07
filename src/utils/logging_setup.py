"""Configuração de logging do projeto."""

import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """Configura logging padrão do projeto."""
    fmt = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    logging.basicConfig(
        level=level,
        format=fmt,
        handlers=[logging.StreamHandler(sys.stdout)],
    )
