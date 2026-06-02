"""Adapter da BRAPI para o Tesouro Direto (fonte primaria do snapshot diario).

Papel no pipeline (modo hibrido):
- BRAPI  -> snapshot ATUAL de todos os titulos ofertados (esta camada).
- CKAN   -> backbone historico + fallback (modulos monitor.py/download.py).

Endpoint base: https://brapi.dev/api/v2/treasury
- /list                 -> titulos ofertados (paginado) JA com taxas/precos atuais.
- /indicators           -> snapshot de simbolos especificos (ate 20 por chamada).
- /indicators/history   -> serie diaria por simbolo (usado em backfill/fallback).

Identificador canonico = `symbol` (slug, ex.: tesouro-selic-01032031).
Nunca dependemos do nome textual (bondType) para classificar: derivamos o
tipo canonico por indexer+couponType, com o nome so como atalho.

Token: SEMPRE via variavel de ambiente BRAPI_TOKEN. Nunca hardcoded.
Plano: Tesouro detalhado exige plano Pro. Sem token, so 3 titulos de sandbox.
"""

import json
import logging
import os
import time
from datetime import datetime

import pandas as pd
import requests

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIG  (ajustar aqui — nada de numero magico espalhado pela logica)
# ============================================================================
CONFIG = {
    "base_url": "https://brapi.dev/api/v2/treasury",
    "token_env": "BRAPI_TOKEN",            # nome da variavel de ambiente
    "timeout_s": 30,                       # timeout explicito por requisicao
    "page_limit": 100,                     # itens/pagina no /list (cobre ~60 titulos numa pagina)
    "max_paginas": 50,                     # trava de seguranca contra loop de paginacao
    "max_simbolos_por_chamada": 20,        # limite do /indicators
    "intervalo_min_s": 1.0,                # rate limit local entre requisicoes
    "retry_delays_s": [5, 15, 45],         # backoff exponencial p/ 429 e 5xx
    "user_agent": "TesouroDirectWX/1.0 (+brapi-adapter)",
    "prefixo_cache_raw": "brapi_snapshot",  # prefixo do arquivo cru em data/raw/
    # 3 titulos liberados no sandbox (sem token) — usados no teste isolado
    "simbolos_sandbox": [
        "tesouro-selic-01032031",
        "tesouro-prefixado-com-juros-semestrais-01012037",
        "tesouro-ipca-com-juros-semestrais-15082060",
    ],
}

# Contrato BRAPI -> tipo_titulo canonico.
# IMPORTANTE: estas strings PRECISAM ser identicas as chaves de
# constants.MAPA_FAMILIA, senao familia_normalizada vira NaN no enriquecimento.
_TIPOS_CANONICOS = {
    "Tesouro Selic",
    "Tesouro Prefixado",
    "Tesouro Prefixado com Juros Semestrais",
    "Tesouro IPCA+",
    "Tesouro IPCA+ com Juros Semestrais",
    "Tesouro IGPM+ com Juros Semestrais",
    "Tesouro Educa+",
    "Tesouro Renda+ Aposentadoria Extra",
}

# Fallback estavel por (indexer, couponType) — indep. da grafia do bondType.
_MAPA_INDEXER_CUPOM = {
    ("selic", "zero"): "Tesouro Selic",
    ("prefixado", "zero"): "Tesouro Prefixado",
    ("prefixado", "semestral"): "Tesouro Prefixado com Juros Semestrais",
    ("ipca", "zero"): "Tesouro IPCA+",
    ("ipca", "semestral"): "Tesouro IPCA+ com Juros Semestrais",
    ("igpm", "semestral"): "Tesouro IGPM+ com Juros Semestrais",
}

# rateInfo.rateType -> natureza da taxa (resolve o erro real x nominal x spread).
_MAPA_TIPO_TAXA = {
    "spreadOverSelic": "spread_selic",       # pos-fixado (Selic)
    "nominalAnnualRate": "nominal",          # Prefixado
    "realAnnualRateOverIpca": "real",        # IPCA+
    "realAnnualRateOverIgpm": "real",        # IGPM+
}


# ============================================================================
# Cliente HTTP
# ============================================================================
_ultima_requisicao_ts = 0.0


def _token_() -> str | None:
    """Le o token Pro da BRAPI da variavel de ambiente (nunca hardcoded)."""
    return os.getenv(CONFIG["token_env"]) or None


def _montar_headers_() -> dict:
    """Headers padrao; adiciona Authorization Bearer se houver token."""
    headers = {"User-Agent": CONFIG["user_agent"], "Accept": "application/json"}
    token = _token_()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _rate_limit_():
    """Garante intervalo minimo entre requisicoes ao dominio."""
    global _ultima_requisicao_ts
    espera = CONFIG["intervalo_min_s"] - (time.time() - _ultima_requisicao_ts)
    if espera > 0:
        time.sleep(espera)
    _ultima_requisicao_ts = time.time()


def _request_brapi_(path: str, params: dict | None = None) -> dict | None:
    """GET em /treasury{path} com timeout, retry/backoff e tratamento de erro.

    Retorna o JSON (dict) em caso de sucesso, ou None se esgotar tentativas.
    401/403 (token) nao sao retentados — retry nao resolve credencial.
    """
    url = f"{CONFIG['base_url']}{path}"
    tentativas = [0] + CONFIG["retry_delays_s"]

    for i, delay in enumerate(tentativas, start=1):
        if delay > 0:
            logger.info("BRAPI retry %d: aguardando %ds...", i, delay)
            time.sleep(delay)
        _rate_limit_()

        try:
            resp = requests.get(
                url, params=params, headers=_montar_headers_(),
                timeout=CONFIG["timeout_s"],
            )
        except requests.exceptions.Timeout:
            logger.warning("BRAPI timeout em %s (tentativa %d)", path, i)
            continue
        except requests.exceptions.RequestException as e:
            logger.warning("BRAPI erro de rede em %s: %s", path, e)
            continue

        # Credencial/plano: nao adianta retentar.
        if resp.status_code in (401, 403):
            logger.error(
                "BRAPI %d em %s — token ausente/invalido ou plano sem acesso "
                "(Tesouro detalhado exige Pro). Verifique %s.",
                resp.status_code, path, CONFIG["token_env"],
            )
            return None

        # Rate limit / erro de servidor: retentavel com backoff.
        if resp.status_code == 429 or resp.status_code >= 500:
            logger.warning("BRAPI %d em %s — retentavel", resp.status_code, path)
            continue

        try:
            data = resp.json()
        except ValueError:
            logger.warning("BRAPI resposta nao-JSON em %s (status %d)", path, resp.status_code)
            continue

        # Envelope de erro da BRAPI: {"error": true, "code": "...", "message": "..."}
        if isinstance(data, dict) and data.get("error"):
            logger.error(
                "BRAPI erro logico em %s: %s (%s)",
                path, data.get("message"), data.get("code"),
            )
            if resp.status_code == 400:
                return None  # parametro invalido nao melhora com retry
            continue

        if resp.status_code == 200:
            return data

        logger.warning("BRAPI status inesperado %d em %s", resp.status_code, path)

    return None


def _paginar_lista_(params: dict) -> list[dict]:
    """Percorre /list seguindo pagination.hasNextPage e acumula os results."""
    resultados: list[dict] = []
    pagina = 1
    while pagina <= CONFIG["max_paginas"]:
        p = dict(params, page=pagina, limit=CONFIG["page_limit"])
        data = _request_brapi_("/list", p)
        if not data:
            break
        lote = data.get("results", []) or []
        resultados.extend(lote)
        pag = data.get("pagination") or {}
        if not pag.get("hasNextPage") or not lote:
            break
        pagina += 1
    return resultados


def listar_titulos(indexer: str | None = None, coupon_type: str | None = None) -> list[dict]:
    """Lista titulos ofertados (com taxas/precos atuais), opcionalmente filtrados."""
    params: dict = {}
    if indexer:
        params["indexer"] = indexer
    if coupon_type:
        params["couponType"] = coupon_type
    return _paginar_lista_(params)


def buscar_indicadores(symbols: list[str]) -> list[dict]:
    """Snapshot atual de simbolos especificos (batched em lotes de 20)."""
    lote_max = CONFIG["max_simbolos_por_chamada"]
    resultados: list[dict] = []
    for ini in range(0, len(symbols), lote_max):
        grupo = symbols[ini:ini + lote_max]
        data = _request_brapi_("/indicators", {"symbols": ",".join(grupo)})
        if data:
            resultados.extend(data.get("results", []) or [])
    return resultados


# ============================================================================
# Normalizacao BRAPI -> schema canonico do pipeline
# ============================================================================
def _mapear_tipo_titulo_(
    bond_type: str | None, indexer: str | None, coupon_type: str | None
) -> str:
    """Deriva o tipo_titulo canonico (chave de MAPA_FAMILIA).

    Ordem: produtos de planejamento pelo nome -> nome ja canonico ->
    fallback estavel por (indexer, couponType) -> nome bruto (sinalizado).
    """
    bt = (bond_type or "").strip()
    if "Educa" in bt:
        return "Tesouro Educa+"
    if "Renda" in bt:
        return "Tesouro Renda+ Aposentadoria Extra"
    if bt in _TIPOS_CANONICOS:
        return bt
    canonico = _MAPA_INDEXER_CUPOM.get(((indexer or "").lower(), (coupon_type or "").lower()))
    if canonico:
        return canonico
    logger.warning(
        "BRAPI tipo nao mapeado: bondType=%r indexer=%r cupom=%r",
        bond_type, indexer, coupon_type,
    )
    return bt


def _classificar_tipo_taxa_(rate_info: dict | None) -> str:
    """spread_selic | nominal | real | desconhecido (a partir de rateInfo.rateType)."""
    rate_type = (rate_info or {}).get("rateType")
    return _MAPA_TIPO_TAXA.get(rate_type, "desconhecido")


def normalizar_resultados_(results: list[dict], fonte: str = "brapi") -> pd.DataFrame:
    """Converte uma lista de results da BRAPI no schema canonico do pipeline.

    Colunas de saida compativeis com enriquecer(): tipo_titulo, data_vencimento,
    data_base, taxa_*_manha, pu_*_manha. Extras: slug, indexer, coupon_type,
    tipo_taxa, duration_days, fonte.
    """
    linhas = []
    for r in results:
        linhas.append({
            "slug": r.get("symbol"),                       # id canonico (estavel)
            "tipo_titulo": _mapear_tipo_titulo_(
                r.get("bondType"), r.get("indexer"), r.get("couponType")),
            "indexer": r.get("indexer"),
            "coupon_type": r.get("couponType"),
            "tipo_taxa": _classificar_tipo_taxa_(r.get("rateInfo")),
            "data_base": r.get("baseDate"),
            "data_vencimento": r.get("maturityDate"),
            "duration_days": r.get("durationDays"),
            # taxas indicativas em % a.a. (mesma escala do CSV CKAN)
            "taxa_compra_manha": r.get("buyRate"),
            "taxa_venda_manha": r.get("sellRate"),
            # PUs indicativos (BRAPI nao separa "manha"; usamos o indicativo do dia)
            "pu_compra_manha": r.get("buyPrice"),
            "pu_venda_manha": r.get("sellPrice"),
            "pu_base_manha": r.get("basePrice"),
            "fonte": fonte,
        })

    df = pd.DataFrame(linhas)
    if df.empty:
        return df

    # Tipos: datas -> datetime; taxas/PU -> float.
    for col in ("data_base", "data_vencimento"):
        df[col] = pd.to_datetime(df[col], format="%Y-%m-%d", errors="coerce")
    for col in ("taxa_compra_manha", "taxa_venda_manha",
                "pu_compra_manha", "pu_venda_manha", "pu_base_manha"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.sort_values(["data_base", "tipo_titulo", "data_vencimento"]).reset_index(drop=True)
    return df


def _cachear_raw_(payload: object, base_date: str | None) -> None:
    """Salva a resposta crua em data/raw/ com timestamp (auditoria/replay)."""
    from src.utils.constants import DATA_RAW  # import tardio: facilita teste isolado
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%dT%H%M%S")
    ref = base_date or "sem-data"
    caminho = DATA_RAW / f"{CONFIG['prefixo_cache_raw']}_{ref}_{ts}.json"
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
    logger.info("BRAPI raw cacheado: %s", caminho)


def coletar_snapshot_brapi() -> pd.DataFrame | None:
    """Snapshot atual de TODOS os titulos ofertados (driver diario do modo hibrido).

    Pagina o /list (ja traz taxas/precos), cacheia o cru em data/raw/ e devolve
    o DataFrame normalizado. Em falha, retorna None para degrade controlado
    (o orquestrador segue com a base CKAN/ultima processada).
    """
    if not _token_():
        logger.warning(
            "BRAPI sem %s — em producao isso limita a 3 titulos sandbox.",
            CONFIG["token_env"],
        )
    try:
        results = listar_titulos()
    except Exception as e:  # noqa: BLE001 — degrade controlado, nunca quebrar o pipeline
        logger.error("BRAPI falhou ao coletar snapshot: %s", e)
        return None

    if not results:
        logger.error("BRAPI retornou snapshot vazio — mantendo fonte de fallback.")
        return None

    base_date = results[0].get("baseDate")
    _cachear_raw_(results, base_date)
    df = normalizar_resultados_(results, fonte="brapi")
    logger.info("BRAPI snapshot normalizado: %d titulos, data_base=%s", len(df), base_date)
    return df


# ============================================================================
# Mesclagem hibrida: CKAN (historico) + BRAPI (snapshot atual)
# ============================================================================
_CHAVE_MERGE = ["tipo_titulo", "data_vencimento", "data_base"]


def mesclar_com_ckan_(df_ckan: pd.DataFrame, df_brapi: pd.DataFrame) -> pd.DataFrame:
    """Une o historico do CKAN com o snapshot da BRAPI.

    Regra: nas datas em que as duas fontes coincidem (mesmo titulo+venc+data_base),
    a BRAPI vence (fonte primaria do dia). Datas que so existem no CKAN viram
    historico; a data mais nova da BRAPI entra como linha extra. Retorna no
    schema que enriquecer() espera (colunas extras da BRAPI seguem como metadados).
    """
    if df_brapi is None or df_brapi.empty:
        return df_ckan
    ck = df_ckan.copy()
    if "fonte" not in ck.columns:
        ck["fonte"] = "ckan"
    # BRAPI primeiro -> keep="first" faz a BRAPI prevalecer no conflito.
    combinado = pd.concat([df_brapi, ck], ignore_index=True)
    combinado = combinado.drop_duplicates(subset=_CHAVE_MERGE, keep="first")
    combinado = combinado.sort_values(_CHAVE_MERGE).reset_index(drop=True)
    logger.info(
        "Merge CKAN+BRAPI: %d (ckan) + %d (brapi) -> %d linhas (%d da brapi).",
        len(df_ckan), len(df_brapi), len(combinado),
        int((combinado["fonte"] == "brapi").sum()),
    )
    return combinado


# ============================================================================
# Teste isolado (rodar antes de integrar ao batch completo)
#   python -m src.ingestao.brapi
# Bate no sandbox (3 titulos, sem token) e mostra o schema normalizado.
# ============================================================================
def _testar_brapi() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    print("\n  BRAPI -- teste isolado (sandbox: 3 titulos, sem token)\n")

    results = buscar_indicadores(CONFIG["simbolos_sandbox"])
    if not results:
        print(
            "  x Sandbox nao retornou nada. Sem rede ou API fora? "
            "Com token Pro, teste coletar_snapshot_brapi()."
        )
        return

    df = normalizar_resultados_(results, fonte="brapi-sandbox")
    print(f"  ok {len(df)} titulos normalizados\n")

    cols = ["slug", "tipo_titulo", "tipo_taxa", "data_base",
            "data_vencimento", "taxa_compra_manha", "pu_compra_manha"]
    with pd.option_context("display.width", 160, "display.max_columns", None):
        print(df[cols].to_string(index=False))

    print("\n  Conferencias:")
    print(f"   - colunas: {list(df.columns)}")
    print(f"   - dtypes data_base/venc: {df['data_base'].dtype} / {df['data_vencimento'].dtype}")
    print(f"   - tipos de taxa presentes: {sorted(df['tipo_taxa'].unique())}")
    sem_familia = df[~df["tipo_titulo"].isin(_TIPOS_CANONICOS)]
    print(f"   - titulos com tipo NAO canonico (deveria ser 0): {len(sem_familia)}")
    print("\n  Esperado: tipo_taxa 'spread_selic' p/ Selic e 'real' p/ IPCA+.\n")


if __name__ == "__main__":
    _testar_brapi()
