"""Coleta Selic, IPCA e Focus no Banco Central e publica data/outputs/macro.json."""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ingestao.macro import ler_macro, montar_snapshot, salvar_macro  # noqa: E402


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    snap = montar_snapshot(anterior=ler_macro())
    salvar_macro(snap)
    for chave in ("selic_meta", "ipca_12m", "focus_ipca_12m", "focus_selic_fim_ano_seguinte"):
        item = snap.get(chave) or {}
        print(f"  {chave:30s} {item.get('valor', '—')!s:>8}  ({item.get('data', 'sem dado')})")
    if snap["erros"]:
        print("  Falhas (valor anterior mantido):", *snap["erros"], sep="\n    ")
    # Falha parcial nao quebra o workflow; falha total sinaliza com exit 1
    return 1 if len(snap["erros"]) == 4 else 0


if __name__ == "__main__":
    raise SystemExit(main())
