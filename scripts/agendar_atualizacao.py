"""Agendamento automático de atualização de dados.

Roda o pipeline de ingestão + analytics automaticamente em dias úteis
às 20:00 (após horário típico de atualização do Tesouro).

Uso:
    python scripts/agendar_atualizacao.py           # inicia agendador
    python scripts/agendar_atualizacao.py --agora    # executa imediatamente
"""

import argparse
import logging
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path

import schedule

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.constants import DATA_AUDIT

LOG_FILE = DATA_AUDIT / "execucoes_agendadas.log"

# Feriados nacionais fixos (adicionar conforme necessário)
FERIADOS_FIXOS = {
    (1, 1),    # Confraternização Universal
    (4, 21),   # Tiradentes
    (5, 1),    # Dia do Trabalho
    (9, 7),    # Independência
    (10, 12),  # Nossa Senhora Aparecida
    (11, 2),   # Finados
    (11, 15),  # Proclamação da República
    (12, 25),  # Natal
}


def _configurar_log():
    """Configura logging para arquivo e console."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def _eh_dia_util(d: date | None = None) -> bool:
    """Verifica se a data é dia útil (segunda a sexta, exceto feriados)."""
    if d is None:
        d = date.today()
    if d.weekday() >= 5:  # Sábado=5, Domingo=6
        return False
    if (d.month, d.day) in FERIADOS_FIXOS:
        return False
    return True


def _ja_rodou_hoje() -> bool:
    """Verifica se o pipeline já rodou com sucesso hoje."""
    if not LOG_FILE.exists():
        return False
    hoje = date.today().isoformat()
    try:
        with open(LOG_FILE, encoding="utf-8") as f:
            for linha in f:
                if hoje in linha and "SUCESSO" in linha:
                    return True
    except OSError:
        pass
    return False


def executar_pipeline():
    """Executa o pipeline completo de ingestão + analytics."""
    logger = logging.getLogger(__name__)

    if not _eh_dia_util():
        logger.info("Nao e dia util - pulando execucao")
        return

    if _ja_rodou_hoje():
        logger.info("Pipeline ja rodou com sucesso hoje - pulando")
        return

    logger.info("Iniciando pipeline de atualizacao...")

    scripts_dir = Path(__file__).resolve().parent
    python = sys.executable

    # 1. Ingestão
    logger.info("Etapa 1: Ingestao")
    result = subprocess.run(
        [python, str(scripts_dir / "rodar_ingestao.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
        cwd=str(scripts_dir.parent),
    )

    if result.returncode != 0:
        logger.error("Ingestao falhou:\n%s", result.stderr or result.stdout)
        logger.error("FALHA - pipeline interrompido na ingestao")
        return

    logger.info("Ingestao concluida")

    # 2. Analytics
    logger.info("Etapa 2: Analytics")
    result = subprocess.run(
        [python, str(scripts_dir / "rodar_analytics.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        cwd=str(scripts_dir.parent),
    )

    if result.returncode != 0:
        logger.error("Analytics falhou:\n%s", result.stderr or result.stdout)
        logger.error("FALHA - pipeline interrompido no analytics")
        return

    logger.info("Analytics concluido")
    logger.info("SUCESSO - pipeline completo")


def main():
    parser = argparse.ArgumentParser(description="Agendador de atualizacao Tesouro Direto WX")
    parser.add_argument("--agora", action="store_true", help="Executar imediatamente")
    args = parser.parse_args()

    _configurar_log()
    logger = logging.getLogger(__name__)

    if args.agora:
        logger.info("Execucao imediata solicitada via --agora")
        executar_pipeline()
        return

    logger.info("Agendador iniciado - pipeline rodara as 20:00 em dias uteis")
    schedule.every().day.at("20:00").do(executar_pipeline)

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Agendador encerrado pelo usuario")


if __name__ == "__main__":
    main()
