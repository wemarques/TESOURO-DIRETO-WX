"""Lista oficial de titulos disponiveis para COMPRA no Tesouro Direto.

Nem o CSV historico do CKAN nem a BRAPI informam se um titulo ainda esta a
venda: os dois publicam taxa e PU de compra tambem para titulos que hoje so
aceitam resgate (ex.: Tesouro Prefixado 2027). Sem essa informacao o
"Melhor Titulo do Dia" sugeria titulos que o investidor nao consegue comprar.

Fonte: arquivo ``config/titulos_ofertados.csv``, que e o CSV baixado em
tesourodireto.com.br > Rendimento dos Titulos > aba "Investir" > "Baixar Lista".
Para atualizar, basta substituir o arquivo pelo download mais recente (o
formato original, com BOM e CRLF, e aceito sem edicao).

Chave de casamento: (tipo_titulo canonico, data_vencimento). O ano no nome
do titulo NAO serve de chave: no Renda+ e no Educa+ ele e o ano de inicio dos
pagamentos, nao o vencimento (ex.: "Renda+ 2030" vence em 15/12/2049).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pandas as pd

from src.utils.constants import MAPA_FAMILIA, PROJECT_ROOT

logger = logging.getLogger(__name__)

ARQUIVO_OFERTADOS = PROJECT_ROOT / "config" / "titulos_ofertados.csv"

COLUNA_TITULO = "Título"
COLUNA_VENCIMENTO = "Vencimento do Título"

# "Tesouro Renda+ Aposentadoria Extra 2030" -> "Tesouro Renda+ Aposentadoria Extra"
_ANO_FINAL = re.compile(r"\s+\d{4}\s*$")


def _ler_csv(caminho: Path) -> pd.DataFrame:
    """Le o CSV oficial tolerando BOM/UTF-8 e, por garantia, latin-1."""
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(caminho, sep=";", dtype=str, encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Nao foi possivel decodificar {caminho}")


def carregar_ofertados(
    caminho: Path | None = None,
) -> set[tuple[str, pd.Timestamp]] | None:
    """Retorna o conjunto {(tipo_titulo, data_vencimento)} a venda.

    Retorna ``None`` quando o arquivo nao existe ou nao pode ser lido, para o
    chamador degradar sem filtrar (comportamento anterior) em vez de quebrar.
    """
    caminho = caminho or ARQUIVO_OFERTADOS
    if not caminho.exists():
        logger.warning(
            "Lista de titulos ofertados ausente (%s): disponibilidade nao sera filtrada.",
            caminho,
        )
        return None

    try:
        df = _ler_csv(caminho)
        df.columns = [c.strip() for c in df.columns]
        if COLUNA_TITULO not in df.columns or COLUNA_VENCIMENTO not in df.columns:
            raise ValueError(f"colunas inesperadas: {list(df.columns)}")
    except Exception as exc:  # noqa: BLE001 - degrade controlado
        logger.error("Falha ao ler %s (%s): disponibilidade nao sera filtrada.", caminho, exc)
        return None

    ofertados: set[tuple[str, pd.Timestamp]] = set()
    for nome, venc in zip(df[COLUNA_TITULO], df[COLUNA_VENCIMENTO]):
        if pd.isna(nome) or pd.isna(venc):
            continue
        tipo = _ANO_FINAL.sub("", str(nome).strip())
        if tipo not in MAPA_FAMILIA:
            # Ex.: Tesouro Reserva — produto fora do escopo analitico do projeto.
            logger.info("Titulo ofertado fora do escopo analitico, ignorado: %s", nome)
            continue
        data = pd.to_datetime(str(venc).strip(), format="%d/%m/%Y", errors="coerce")
        if pd.isna(data):
            logger.warning("Vencimento invalido na lista de ofertados: %r", venc)
            continue
        ofertados.add((tipo, data.normalize()))

    if not ofertados:
        logger.error("Lista de ofertados vazia em %s: disponibilidade nao sera filtrada.", caminho)
        return None
    return ofertados


def marcar_disponibilidade(
    df: pd.DataFrame,
    ofertados: set[tuple[str, pd.Timestamp]] | None,
) -> pd.DataFrame:
    """Acrescenta a coluna booleana ``disponivel_compra`` ao DataFrame.

    Sem lista (``None``), todos ficam ``True`` — mesmo comportamento de antes
    da correcao. Titulos da lista ausentes dos dados geram aviso no log.
    """
    df = df.copy()
    if df.empty:
        df["disponivel_compra"] = pd.Series(dtype=bool)
        return df
    if ofertados is None:
        df["disponivel_compra"] = True
        return df

    chaves = list(
        zip(df["tipo_titulo"], pd.to_datetime(df["data_vencimento"]).dt.normalize())
    )
    df["disponivel_compra"] = [chave in ofertados for chave in chaves]

    faltando = ofertados - set(chaves)
    for tipo, venc in sorted(faltando):
        logger.warning(
            "Titulo ofertado sem dados no snapshot: %s %s", tipo, venc.strftime("%d/%m/%Y")
        )
    return df
