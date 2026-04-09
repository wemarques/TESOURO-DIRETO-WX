"""Registro de metadados de ingestão (hash, inventário, log).

Mantém catálogo de todas as cargas realizadas e registra
incidentes em caso de falha.
"""

import json
import logging
from datetime import datetime

from src.utils.constants import DATA_AUDIT

logger = logging.getLogger(__name__)

CATALOGO_FILE = DATA_AUDIT / "catalogo_ingestoes.json"
INCIDENTES_DIR = DATA_AUDIT / "incidentes"


def _carregar_catalogo() -> list[dict]:
    """Carrega catálogo existente ou retorna lista vazia."""
    if not CATALOGO_FILE.exists():
        return []
    try:
        with open(CATALOGO_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.warning("Falha ao ler catalogo, iniciando novo")
        return []


def _salvar_catalogo(catalogo: list[dict]):
    """Salva catálogo em disco."""
    CATALOGO_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CATALOGO_FILE, "w", encoding="utf-8") as f:
        json.dump(catalogo, f, indent=2, ensure_ascii=False)


def registrar_carga(info_download: dict, status_validacao: str, observacoes: str = "") -> dict:
    """Registra uma nova ingestão no catálogo.

    Args:
        info_download: Dict retornado por download.baixar_csv()
        status_validacao: "aprovado", "quarentena" ou "falha"
        observacoes: Notas adicionais

    Returns:
        Entrada registrada no catálogo
    """
    catalogo = _carregar_catalogo()

    dataset_id = f"ingestao_{len(catalogo) + 1:04d}"

    entrada = {
        "dataset_id": dataset_id,
        "fonte": "tesouro_transparente_ckan",
        "url_origem": info_download.get("url_usada", ""),
        "nome_arquivo_original": "precotaxatesourodireto.csv",
        "nome_arquivo_interno": info_download.get("nome_arquivo", ""),
        "data_referencia": info_download.get("data_referencia", ""),
        "data_ingestao": info_download.get("data_ingestao", datetime.now().isoformat()),
        "hash_sha256": info_download.get("hash_sha256", ""),
        "tamanho_bytes": info_download.get("tamanho_bytes", 0),
        "linhas_brutas": info_download.get("linhas_brutas", 0),
        "colunas_brutas": info_download.get("colunas_brutas", 0),
        "status_validacao": status_validacao,
        "metodo_obtencao": info_download.get("metodo", ""),
        "observacoes": observacoes,
    }

    catalogo.append(entrada)
    _salvar_catalogo(catalogo)

    logger.info("Carga registrada: %s - status=%s", dataset_id, status_validacao)
    return entrada


def registrar_incidente(tipo_erro: str, mensagem: str, detalhes: dict | None = None):
    """Registra um incidente de falha no pipeline.

    Args:
        tipo_erro: Categoria do erro (ex: "download_falhou", "validacao_falhou")
        mensagem: Descrição do erro
        detalhes: Informações adicionais
    """
    INCIDENTES_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now()
    nome = f"incidente_{timestamp.strftime('%Y%m%d_%H%M%S')}_{tipo_erro}.json"

    incidente = {
        "timestamp": timestamp.isoformat(),
        "tipo_erro": tipo_erro,
        "mensagem": mensagem,
        "detalhes": detalhes or {},
        "acao_tomada": "mantida_ultima_versao_valida",
    }

    caminho = INCIDENTES_DIR / nome
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(incidente, f, indent=2, ensure_ascii=False)

    logger.error("Incidente registrado: %s - %s", tipo_erro, mensagem)
    return caminho


def obter_ultima_ingestao() -> dict | None:
    """Retorna a última ingestão bem-sucedida do catálogo.

    Returns:
        Dict da última entrada com status "aprovado", ou None
    """
    catalogo = _carregar_catalogo()
    for entrada in reversed(catalogo):
        if entrada.get("status_validacao") == "aprovado":
            return entrada
    return None
