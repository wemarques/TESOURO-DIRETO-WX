"""Monitoramento de fonte oficial para novos CSVs.

Consulta a API CKAN do Tesouro Transparente para detectar
se há um novo arquivo CSV disponível, comparando o hash SHA-256
do arquivo remoto com o último hash registrado localmente.
"""

import hashlib
import json
import logging
from dataclasses import dataclass

import requests

from src.utils.constants import DATA_AUDIT

logger = logging.getLogger(__name__)

CKAN_PACKAGE_URL = (
    "https://www.tesourotransparente.gov.br/ckan/api/3/action/package_show"
    "?id=taxas-dos-titulos-ofertados-pelo-tesouro-direto"
)

USER_AGENT = "TesouroDirectWX/1.0 (projeto-analitico)"
TIMEOUT = 60

HASH_FILE = DATA_AUDIT / "ultimo_hash.json"


@dataclass
class ResultadoMonitor:
    """Resultado da verificação de atualização."""

    tem_atualizacao: bool
    url_csv: str | None = None
    metadata_modified: str | None = None
    last_modified: str | None = None
    hash_anterior: str | None = None
    metodo: str = "ckan_api"
    mensagem: str = ""


def _ler_ultimo_hash() -> dict | None:
    """Lê o último hash registrado de data/audit/ultimo_hash.json."""
    if not HASH_FILE.exists():
        return None
    try:
        with open(HASH_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.warning("Falha ao ler %s", HASH_FILE)
        return None


def _descobrir_url_csv_ckan() -> dict:
    """Consulta API CKAN e retorna info do recurso CSV.

    Returns:
        Dict com url, metadata_modified, last_modified
    Raises:
        RuntimeError se não encontrar recurso CSV
    """
    resp = requests.get(
        CKAN_PACKAGE_URL,
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()

    if not data.get("success"):
        raise RuntimeError("API CKAN retornou success=false")

    recursos = data["result"].get("resources", [])
    csv_resource = None
    for r in recursos:
        if r.get("format", "").upper() == "CSV":
            csv_resource = r
            break

    if csv_resource is None:
        raise RuntimeError("Nenhum recurso CSV encontrado no dataset CKAN")

    return {
        "url": csv_resource["url"],
        "metadata_modified": data["result"].get("metadata_modified", ""),
        "last_modified": csv_resource.get("last_modified", ""),
    }


def calcular_hash_conteudo(conteudo: bytes) -> str:
    """Calcula SHA-256 de conteúdo em bytes."""
    return hashlib.sha256(conteudo).hexdigest()


def verificar_atualizacao() -> ResultadoMonitor:
    """Verifica se há novo CSV disponível no Tesouro Transparente.

    Fluxo:
    1. Consulta API CKAN para descobrir URL do CSV
    2. Faz HEAD/GET leve para obter o conteúdo
    3. Compara hash com último registrado
    4. Retorna resultado indicando se há atualização

    Returns:
        ResultadoMonitor com informações sobre a verificação
    """
    ultimo = _ler_ultimo_hash()
    hash_anterior = ultimo["hash_sha256"] if ultimo else None

    # Descobrir URL via CKAN
    try:
        info_ckan = _descobrir_url_csv_ckan()
        url_csv = info_ckan["url"]
        metodo = "ckan_api"
        logger.info("URL CSV via CKAN: %s", url_csv)
    except Exception as e:
        logger.warning("Falha na API CKAN: %s — usando fallback", e)
        url_csv = (
            "https://www.tesourotransparente.gov.br/ckan/dataset/"
            "df56aa42-484a-4a59-8184-7676580c81e3/resource/"
            "796d2059-14e9-44e3-80c9-2d9e30b405c1/download/"
            "precotaxatesourodireto.csv"
        )
        info_ckan = {"metadata_modified": "", "last_modified": ""}
        metodo = "fallback_direto"

    # Baixar conteúdo para calcular hash
    try:
        resp = requests.get(
            url_csv,
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
    except Exception as e:
        return ResultadoMonitor(
            tem_atualizacao=False,
            mensagem=f"Falha ao baixar CSV para verificacao: {e}",
            metodo=metodo,
        )

    hash_novo = calcular_hash_conteudo(resp.content)

    if hash_novo == hash_anterior:
        return ResultadoMonitor(
            tem_atualizacao=False,
            url_csv=url_csv,
            metadata_modified=info_ckan.get("metadata_modified"),
            last_modified=info_ckan.get("last_modified"),
            hash_anterior=hash_anterior,
            metodo=metodo,
            mensagem="Hash identico — sem atualizacao",
        )

    return ResultadoMonitor(
        tem_atualizacao=True,
        url_csv=url_csv,
        metadata_modified=info_ckan.get("metadata_modified"),
        last_modified=info_ckan.get("last_modified"),
        hash_anterior=hash_anterior,
        metodo=metodo,
        mensagem=f"Novo hash detectado: {hash_novo[:16]}...",
    )
