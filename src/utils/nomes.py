"""Nomes curtos dos titulos, no padrao do site do Tesouro Direto.

No Renda+ e no Educa+ o ano do nome NAO e o vencimento: e o ano em que os
pagamentos comecam. Renda+ paga 240 parcelas (20 anos) e Educa+ 60 (5 anos),
entao "Renda+ 2065" vence em 12/2084 e "Educa+ 2044" vence em 12/2048.
"""

from __future__ import annotations

import pandas as pd

_CURTOS = {
    "Tesouro Selic": ("Selic", 0),
    "Tesouro Prefixado": ("Prefixado", 0),
    "Tesouro Prefixado com Juros Semestrais": ("Prefixado Juros", 0),
    "Tesouro IPCA+": ("IPCA+", 0),
    "Tesouro IPCA+ com Juros Semestrais": ("IPCA+ Juros", 0),
    "Tesouro IGPM+ com Juros Semestrais": ("IGPM+ Juros", 0),
    "Tesouro Renda+ Aposentadoria Extra": ("Renda+", 19),
    "Tesouro Educa+": ("Educa+", 4),
}


def nome_curto(tipo_titulo: str, vencimento) -> str:
    """Ex.: ('Tesouro Renda+ Aposentadoria Extra', 2084-12-15) -> 'Renda+ 2065'."""
    rotulo, recuo = _CURTOS.get(tipo_titulo, (tipo_titulo.replace("Tesouro ", ""), 0))
    return f"{rotulo} {pd.Timestamp(vencimento).year - recuo}"
