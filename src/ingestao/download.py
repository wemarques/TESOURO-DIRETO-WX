"""Download de CSV oficial do Tesouro Transparente.

Implementa download robusto com retry, backoff exponencial,
rate limiting e fallback para URL direta.
"""

import csv
import hashlib
import io
import json
import logging
import time
from datetime import datetime

import requests

from src.utils.constants import DATA_AUDIT, DATA_RAW

logger = logging.getLogger(__name__)

USER_AGENT = "TesouroDirectWX/1.0 (projeto-analitico)"
TIMEOUT = 60
MIN_INTERVALO_REQUISICOES = 5  # segundos entre requisições ao mesmo domínio

RETRY_DELAYS = [30, 120, 300]  # backoff exponencial em segundos

FALLBACK_URL = (
    "https://www.tesourotransparente.gov.br/ckan/dataset/"
    "df56aa42-484a-4a59-8184-7676580c81e3/resource/"
    "796d2059-14e9-44e3-80c9-2d9e30b405c1/download/"
    "precotaxatesourodireto.csv"
)

HASH_FILE = DATA_AUDIT / "ultimo_hash.json"

# Controle de rate limiting
_ultima_requisicao: float = 0.0


def _rate_limit():
    """Garante intervalo mínimo entre requisições."""
    global _ultima_requisicao
    agora = time.time()
    espera = MIN_INTERVALO_REQUISICOES - (agora - _ultima_requisicao)
    if espera > 0:
        logger.debug("Rate limit: aguardando %.1fs", espera)
        time.sleep(espera)
    _ultima_requisicao = time.time()


def _validar_conteudo(conteudo: bytes) -> bool:
    """Valida que o conteúdo baixado é um CSV válido (não vazio, não HTML)."""
    if len(conteudo) < 100:
        logger.error("Arquivo muito pequeno (%d bytes)", len(conteudo))
        return False
    inicio = conteudo[:500].decode("latin-1", errors="replace").lower()
    if "<html" in inicio or "<!doctype" in inicio:
        logger.error("Conteudo e HTML, nao CSV")
        return False
    return True


def _baixar_com_retry(url: str) -> bytes | None:
    """Tenta baixar URL com retry e backoff exponencial.

    Returns:
        Conteúdo em bytes ou None se todas as tentativas falharem
    """
    for tentativa, delay in enumerate([0] + RETRY_DELAYS, start=1):
        if delay > 0:
            logger.info("Retry %d: aguardando %ds...", tentativa, delay)
            time.sleep(delay)

        _rate_limit()

        try:
            resp = requests.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=TIMEOUT,
            )
            if resp.status_code >= 500:
                logger.warning("Erro %d do servidor na tentativa %d", resp.status_code, tentativa)
                continue
            resp.raise_for_status()

            if not _validar_conteudo(resp.content):
                continue

            return resp.content

        except requests.exceptions.Timeout:
            logger.warning("Timeout na tentativa %d", tentativa)
        except requests.exceptions.RequestException as e:
            logger.warning("Erro na tentativa %d: %s", tentativa, e)

    return None


def _gerar_nome_arquivo(data_referencia: str) -> str:
    """Gera nome padronizado para o arquivo baixado."""
    data_ingestao = datetime.now().strftime("%Y-%m-%d")

    # Encontrar próxima versão
    padrao = f"tesouro_ckan_taxas_titulos_{data_referencia}_{data_ingestao}_v*.csv"
    existentes = list(DATA_RAW.glob(padrao))
    versao = len(existentes) + 1

    return f"tesouro_ckan_taxas_titulos_{data_referencia}_{data_ingestao}_v{versao:03d}.csv"


def _salvar_hash(hash_sha256: str, url_usada: str, tamanho: int, metodo: str):
    """Salva hash e metadados em data/audit/ultimo_hash.json."""
    HASH_FILE.parent.mkdir(parents=True, exist_ok=True)
    registro = {
        "hash_sha256": hash_sha256,
        "data_download": datetime.now().isoformat(),
        "url_usada": url_usada,
        "tamanho_bytes": tamanho,
        "metodo": metodo,
    }
    with open(HASH_FILE, "w", encoding="utf-8") as f:
        json.dump(registro, f, indent=2, ensure_ascii=False)
    logger.info("Hash registrado: %s...", hash_sha256[:16])


def baixar_csv(
    url: str | None = None, metodo: str = "ckan_api",
) -> dict | None:
    """Baixa CSV oficial do Tesouro Transparente.

    Args:
        url: URL do CSV (se None, usa fallback direto)
        metodo: Método de obtenção ("ckan_api" ou "fallback_direto")

    Returns:
        Dict com caminho, hash, tamanho e metadados, ou None se falhar
    """
    # Tentar URL principal
    conteudo = None
    url_usada = url or FALLBACK_URL

    if url:
        logger.info("Baixando via %s: %s", metodo, url)
        conteudo = _baixar_com_retry(url)

    # Fallback se URL principal falhou
    if conteudo is None and url != FALLBACK_URL:
        logger.warning("URL principal falhou — tentando fallback direto")
        url_usada = FALLBACK_URL
        metodo = "fallback_direto"
        conteudo = _baixar_com_retry(FALLBACK_URL)

    if conteudo is None:
        logger.error("Todas as tentativas de download falharam")
        return None

    # Calcular hash
    hash_sha256 = hashlib.sha256(conteudo).hexdigest()

    # Detectar data_referencia, contagem de linhas e colunas em uma unica
    # passada via csv.reader. A coluna data_base esta no indice 2.
    # O max() retorna a data mais recente, independente da ordenacao do CSV.
    data_referencia = datetime.now().strftime("%Y-%m-%d")
    linhas_brutas = 0
    colunas_brutas = 0
    try:
        texto = conteudo.decode("latin-1")
        leitor = csv.reader(io.StringIO(texto), delimiter=";")
        max_data_iso: str | None = None

        cabecalho = next(leitor, None)
        if cabecalho is not None:
            colunas_brutas = len(cabecalho)

        for linha in leitor:
            linhas_brutas += 1
            if len(linha) <= 2:
                continue
            data_raw = linha[2].strip()
            if not data_raw:
                continue
            try:
                d, m, y = data_raw.split("/")
                data_iso = f"{y}-{m.zfill(2)}-{d.zfill(2)}"
            except ValueError:
                continue
            if max_data_iso is None or data_iso > max_data_iso:
                max_data_iso = data_iso

        if max_data_iso:
            data_referencia = max_data_iso
        else:
            logger.warning("Nao foi possivel detectar data_referencia, usando hoje")
    except Exception as e:
        logger.warning("Erro ao processar CSV para metadados: %s", e)

    # Salvar arquivo
    nome = _gerar_nome_arquivo(data_referencia)
    caminho = DATA_RAW / nome
    caminho.write_bytes(conteudo)
    logger.info("CSV salvo: %s (%d bytes)", caminho, len(conteudo))

    # Registrar hash
    _salvar_hash(hash_sha256, url_usada, len(conteudo), metodo)

    return {
        "caminho": caminho,
        "nome_arquivo": nome,
        "hash_sha256": hash_sha256,
        "tamanho_bytes": len(conteudo),
        "url_usada": url_usada,
        "metodo": metodo,
        "data_referencia": data_referencia,
        "data_ingestao": datetime.now().isoformat(),
        "linhas_brutas": linhas_brutas,
        "colunas_brutas": colunas_brutas,
    }
