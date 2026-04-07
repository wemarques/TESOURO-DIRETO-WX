"""
Validação de arquivos CSV do Tesouro Direto.

Executa três camadas de validação:
1. Física — arquivo legível, encoding, tamanho
2. Estrutural — schema, colunas obrigatórias, tipos
3. Semântica — coerência temporal, faixas plausíveis, duplicidades
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.utils.constants import COLUNAS_ORIGINAIS, DATA_AUDIT

logger = logging.getLogger(__name__)


def calcular_hash(caminho: Path) -> str:
    """Calcula SHA-256 do arquivo."""
    sha256 = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(8192), b""):
            sha256.update(bloco)
    return sha256.hexdigest()


def validar_fisico(caminho: Path) -> dict[str, Any]:
    """Validação física: arquivo existe, é legível, tem conteúdo."""
    erros = []

    if not caminho.exists():
        erros.append(f"Arquivo não encontrado: {caminho}")
        return {"ok": False, "erros": erros}

    if not caminho.suffix.lower() == ".csv":
        erros.append(f"Extensão inesperada: {caminho.suffix}")

    tamanho = caminho.stat().st_size
    if tamanho == 0:
        erros.append("Arquivo vazio")
        return {"ok": False, "erros": erros}

    file_hash = calcular_hash(caminho)

    return {
        "ok": len(erros) == 0,
        "erros": erros,
        "tamanho_bytes": tamanho,
        "hash_sha256": file_hash,
    }


def validar_estrutural(caminho: Path, separador: str = ";", encoding: str = "latin-1") -> dict[str, Any]:
    """Validação estrutural: schema, colunas, tipos."""
    erros = []
    alertas = []

    try:
        df = pd.read_csv(caminho, sep=separador, encoding=encoding, nrows=5)
    except Exception as e:
        erros.append(f"Falha ao ler CSV: {e}")
        return {"ok": False, "erros": erros, "alertas": alertas}

    colunas_presentes = set(df.columns)
    colunas_esperadas = set(COLUNAS_ORIGINAIS)
    faltantes = colunas_esperadas - colunas_presentes

    if faltantes:
        erros.append(f"Colunas obrigatórias ausentes: {faltantes}")

    duplicadas = [c for c in df.columns if list(df.columns).count(c) > 1]
    if duplicadas:
        erros.append(f"Colunas duplicadas: {set(duplicadas)}")

    # Ler arquivo completo para contagem
    try:
        df_full = pd.read_csv(caminho, sep=separador, encoding=encoding)
        linhas = len(df_full)
        colunas = len(df_full.columns)
    except Exception:
        linhas = -1
        colunas = -1
        alertas.append("Não foi possível contar linhas do arquivo completo")

    return {
        "ok": len(erros) == 0,
        "erros": erros,
        "alertas": alertas,
        "linhas": linhas,
        "colunas": colunas,
    }


def validar_semantico(
    caminho: Path,
    separador: str = ";",
    encoding: str = "latin-1",
    decimal: str = ",",
) -> dict[str, Any]:
    """Validação semântica: coerência de datas, faixas, duplicidades."""
    erros = []
    alertas = []

    try:
        df = pd.read_csv(caminho, sep=separador, encoding=encoding, decimal=decimal)
    except Exception as e:
        erros.append(f"Falha na leitura semântica: {e}")
        return {"ok": False, "erros": erros, "alertas": alertas}

    # Converter datas
    for col in ["Data Vencimento", "Data Base"]:
        if col in df.columns:
            try:
                df[col] = pd.to_datetime(df[col], format="%d/%m/%Y", dayfirst=True)
            except Exception:
                alertas.append(f"Falha ao converter datas em '{col}'")

    # Coerência temporal
    if "Data Vencimento" in df.columns and "Data Base" in df.columns:
        invalidos = df[df["Data Vencimento"] <= df["Data Base"]]
        if len(invalidos) > 0:
            alertas.append(
                f"{len(invalidos)} linhas com data_vencimento <= data_base"
            )

    # Verificar famílias reconhecidas
    from src.utils.constants import MAPA_FAMILIA

    if "Tipo Titulo" in df.columns:
        familias = df["Tipo Titulo"].unique()
        nao_mapeadas = [f for f in familias if f not in MAPA_FAMILIA]
        if nao_mapeadas:
            alertas.append(f"Famílias não reconhecidas: {nao_mapeadas}")

    # Missing em colunas críticas
    for col in COLUNAS_ORIGINAIS:
        if col in df.columns:
            n_missing = df[col].isna().sum()
            if n_missing > 0:
                alertas.append(f"{n_missing} valores ausentes em '{col}'")

    return {
        "ok": len(erros) == 0,
        "erros": erros,
        "alertas": alertas,
    }


def validar_csv(caminho: Path) -> dict[str, Any]:
    """
    Executa validação completa do CSV em 3 camadas.

    Returns:
        Dict com chaves: aprovado, erros, alertas, linhas, colunas, hash_sha256
    """
    resultado = {
        "aprovado": False,
        "erros": [],
        "alertas": [],
        "linhas": 0,
        "colunas": 0,
        "hash_sha256": "",
        "timestamp": datetime.now().isoformat(),
        "arquivo": str(caminho),
    }

    # 1. Físico
    fisico = validar_fisico(caminho)
    if not fisico["ok"]:
        resultado["erros"].extend(fisico["erros"])
        _registrar_auditoria(resultado)
        return resultado

    resultado["hash_sha256"] = fisico.get("hash_sha256", "")

    # 2. Estrutural
    estrutural = validar_estrutural(caminho)
    resultado["linhas"] = estrutural.get("linhas", 0)
    resultado["colunas"] = estrutural.get("colunas", 0)
    if not estrutural["ok"]:
        resultado["erros"].extend(estrutural["erros"])
        resultado["alertas"].extend(estrutural.get("alertas", []))
        _registrar_auditoria(resultado)
        return resultado

    resultado["alertas"].extend(estrutural.get("alertas", []))

    # 3. Semântico
    semantico = validar_semantico(caminho)
    resultado["alertas"].extend(semantico.get("alertas", []))
    if not semantico["ok"]:
        resultado["erros"].extend(semantico["erros"])
        _registrar_auditoria(resultado)
        return resultado

    resultado["aprovado"] = True
    _registrar_auditoria(resultado)

    logger.info(
        "CSV validado: %s — %d linhas, %d alertas",
        caminho.name,
        resultado["linhas"],
        len(resultado["alertas"]),
    )

    return resultado


def _registrar_auditoria(resultado: dict) -> None:
    """Salva log de validação em data/audit/."""
    DATA_AUDIT.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = DATA_AUDIT / f"validacao_{ts}.json"
    try:
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(resultado, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning("Falha ao registrar auditoria: %s", e)
