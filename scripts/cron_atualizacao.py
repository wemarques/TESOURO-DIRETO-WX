"""Cron job de atualizacao para Railway (ou outro PaaS).

Roda o pipeline completo (ingestao + analytics) e loga em stdout.
Railway captura stdout/stderr automaticamente como log do servico.

Ativar via variavel de ambiente CRON_ENABLED=true. Util para
desabilitar o cron sem remover o servico (em deploy de teste, por ex).

Uso (Railway Cron Job):
    schedule: 0 23 * * 1-5  (20h Brasilia = 23h UTC, seg-sex)
    command:  python scripts/cron_atualizacao.py
"""

import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _log(msg: str):
    """Loga mensagem com timestamp em stdout (capturado pelo Railway)."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def main():
    """Executa o pipeline completo de atualizacao."""
    cron_enabled = os.environ.get("CRON_ENABLED", "false").lower() == "true"
    if not cron_enabled:
        _log("CRON_ENABLED nao esta 'true' - pulando execucao")
        return 0

    _log("Iniciando cron de atualizacao...")

    # Etapa 1: Ingestao (download + validacao + padronizacao + enriquecimento)
    _log("Etapa 1/2: Ingestao")
    try:
        from scripts.rodar_ingestao import main as rodar_ingestao
        rodar_ingestao()
        _log("Ingestao concluida")
    except SystemExit:
        # argparse pode chamar sys.exit, ignoramos
        pass
    except Exception as e:
        _log(f"ERRO na ingestao: {e}")
        return 1

    # Etapa 2: Analytics (metricas + curvas + scores + ranking)
    _log("Etapa 2/2: Analytics")
    try:
        from scripts.rodar_analytics import main as rodar_analytics
        rodar_analytics()
        _log("Analytics concluido")
    except Exception as e:
        _log(f"ERRO no analytics: {e}")
        return 1

    _log("SUCESSO - cron concluido")
    return 0


if __name__ == "__main__":
    sys.exit(main())
