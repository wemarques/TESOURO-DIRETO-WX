"""Calendario de dias uteis ANBIMA (feriados nacionais) e contagem du/252.

Os feriados sao gerados por regra (fixos + moveis pela Pascoa), sem tabela
externa: cobre qualquer ano, inclusive os vencimentos do Renda+ ate 2084.

Feriados ANBIMA = feriados nacionais bancarios:
- 01/01, 21/04, 01/05, 07/09, 12/10, 02/11, 15/11, 25/12
- 20/11 (Consciencia Negra, nacional a partir de 2024 — Lei 14.759/2023)
- Carnaval (segunda e terca), Sexta-feira Santa e Corpus Christi (moveis)
"""

from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache

import numpy as np
import pandas as pd

_FIXOS = [(1, 1), (4, 21), (5, 1), (9, 7), (10, 12), (11, 2), (11, 15), (12, 25)]


def _pascoa(ano: int) -> date:
    """Domingo de Pascoa (algoritmo de Meeus/Jones/Butcher)."""
    a = ano % 19
    b, c = divmod(ano, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    mes = (h + l_ - 7 * m + 114) // 31
    dia = (h + l_ - 7 * m + 114) % 31 + 1
    return date(ano, mes, dia)


def feriados_ano(ano: int) -> list[date]:
    """Feriados ANBIMA de um ano."""
    feriados = [date(ano, m, d) for m, d in _FIXOS]
    if ano >= 2024:
        feriados.append(date(ano, 11, 20))
    p = _pascoa(ano)
    feriados += [
        p - timedelta(days=48),  # segunda de Carnaval
        p - timedelta(days=47),  # terca de Carnaval
        p - timedelta(days=2),   # Sexta-feira Santa
        p + timedelta(days=60),  # Corpus Christi
    ]
    return sorted(feriados)


@lru_cache(maxsize=1)
def feriados_array(ano_ini: int = 2000, ano_fim: int = 2100) -> np.ndarray:
    """Array numpy datetime64[D] com todos os feriados no intervalo."""
    todos = [f for ano in range(ano_ini, ano_fim + 1) for f in feriados_ano(ano)]
    return np.array(todos, dtype="datetime64[D]")


def _to_d64(x) -> np.ndarray:
    return np.asarray(pd.to_datetime(x)).astype("datetime64[D]")


def dias_uteis(inicio, fim) -> np.ndarray:
    """Dias uteis entre ``inicio`` (inclusive) e ``fim`` (exclusive).

    E a contagem ANBIMA entre a data de liquidacao e a data do fluxo.
    Aceita escalares ou arrays (com broadcasting).
    """
    return np.busday_count(_to_d64(inicio), _to_d64(fim), holidays=feriados_array())


def e_dia_util(d) -> bool:
    """True se a data for dia util ANBIMA."""
    return bool(np.is_busday(_to_d64(d), holidays=feriados_array()))
