"""Contexto macro do Banco Central (Fase 4): Selic, IPCA e expectativas Focus.

Fontes publicas, sem token:
- SGS (api.bcb.gov.br): 432 = Selic meta (% a.a.); 13522 = IPCA acumulado 12 meses.
- Focus / Olinda (olinda.bcb.gov.br):
  - ExpectativasMercadoInflacao12Meses: IPCA esperado para os proximos 12 meses
  - ExpectativasMercadoAnuais (Indicador='Selic'): Selic esperada no fim do ano

Saida: ``data/outputs/macro.json`` (commitado pelo workflow de ingestao, junto
com os parquets). Falha em uma fonte NAO derruba as outras: o valor anterior do
JSON e mantido e o erro fica registrado em ``erros``. O dashboard cai nas
constantes de referencia (``constants.py``) se o arquivo nao existir.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote

import requests

from src.utils.constants import DATA_OUTPUTS, IPCA_ATUAL, SELIC_META_REF

logger = logging.getLogger(__name__)

ARQUIVO_MACRO = DATA_OUTPUTS / "macro.json"

CONFIG = {
    "timeout_s": 30,
    "retry_delays_s": [3, 10],
    "user_agent": "TesouroDirectWX/1.0 (+macro-bcb)",
    "sgs_url": "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados/ultimos/{n}?formato=json",
    "olinda_url": "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/{recurso}",
    "serie_selic_meta": 432,
    "serie_ipca_12m": 13522,
}


def _get_json(url: str, params: dict | None = None) -> object:
    """GET com ate 3 tentativas para erros 5xx/rede (o SGS oscila com 502)."""
    ultimo_erro: Exception | None = None
    for tentativa, espera in enumerate(CONFIG["retry_delays_s"] + [None]):
        try:
            resp = requests.get(
                url,
                params=params,
                timeout=CONFIG["timeout_s"],
                headers={"User-Agent": CONFIG["user_agent"], "Accept": "application/json"},
            )
            if resp.status_code < 500:
                resp.raise_for_status()
                return resp.json()
            ultimo_erro = requests.HTTPError(f"{resp.status_code} em {url}")
        except (requests.ConnectionError, requests.Timeout) as exc:
            ultimo_erro = exc
        if espera is not None:
            logger.info("BCB indisponivel (tentativa %d), nova em %ss", tentativa + 1, espera)
            time.sleep(espera)
    raise ultimo_erro  # type: ignore[misc]


def _odata_url(recurso: str, params: dict) -> str:
    """Monta a URL OData do Olinda com espacos como %20 (o servidor recusa '+')."""
    seguros = "'(),"
    query = "&".join(f"{k}={quote(str(v), safe=seguros)}" for k, v in params.items())
    return CONFIG["olinda_url"].format(recurso=recurso) + "?" + query


def _num(valor) -> float:
    return float(str(valor).replace(",", "."))


def parse_sgs(payload: list[dict]) -> tuple[str, float]:
    """Ultimo ponto valido de uma serie SGS -> (data ISO, valor)."""
    pontos = [p for p in payload if p.get("valor") not in (None, "")]
    if not pontos:
        raise ValueError("SGS sem dados")
    ultimo = pontos[-1]
    data = datetime.strptime(ultimo["data"], "%d/%m/%Y").date().isoformat()
    return data, _num(ultimo["valor"])


def parse_focus(payload: dict, ano_referencia: int | None = None) -> tuple[str, float]:
    """Mediana mais recente de uma consulta Olinda (OData ``value``) -> (data, mediana).

    Para ``ExpectativasMercadoAnuais`` filtra pelo ``DataReferencia`` (ano).
    """
    itens = payload.get("value", []) if isinstance(payload, dict) else []
    if ano_referencia is not None:
        itens = [i for i in itens if str(i.get("DataReferencia")) == str(ano_referencia)]
    itens = [i for i in itens if i.get("Mediana") is not None]
    if not itens:
        raise ValueError("Focus sem dados")
    mais_recente = max(itens, key=lambda i: i.get("Data", ""))
    return str(mais_recente["Data"])[:10], _num(mais_recente["Mediana"])


def coletar_sgs(serie: int, n: int = 5) -> tuple[str, float]:
    return parse_sgs(_get_json(CONFIG["sgs_url"].format(serie=serie, n=n)))


def coletar_focus_ipca_12m() -> tuple[str, float]:
    params = {
        "$filter": "Indicador eq 'IPCA' and Suavizada eq 'S' and baseCalculo eq 0",
        "$orderby": "Data desc",
        "$top": "5",
        "$format": "json",
    }
    return parse_focus(_get_json(_odata_url("ExpectativasMercadoInflacao12Meses", params)))


def coletar_focus_selic_fim_ano(ano: int) -> tuple[str, float]:
    params = {
        "$filter": f"Indicador eq 'Selic' and DataReferencia eq '{ano}' and baseCalculo eq 0",
        "$orderby": "Data desc",
        "$top": "5",
        "$format": "json",
    }
    return parse_focus(
        _get_json(_odata_url("ExpectativasMercadoAnuais", params)), ano_referencia=ano
    )


def montar_snapshot(anterior: dict | None = None, hoje: date | None = None) -> dict:
    """Coleta todas as fontes; o que falhar mantem o valor de ``anterior``."""
    hoje = hoje or date.today()
    ano_seguinte = hoje.year + 1
    snap = dict(anterior or {})
    erros: list[str] = []

    coletas = {
        "selic_meta": lambda: coletar_sgs(CONFIG["serie_selic_meta"]),
        "ipca_12m": lambda: coletar_sgs(CONFIG["serie_ipca_12m"]),
        "focus_ipca_12m": coletar_focus_ipca_12m,
        "focus_selic_fim_ano_seguinte": lambda: coletar_focus_selic_fim_ano(ano_seguinte),
    }
    for chave, coletar in coletas.items():
        try:
            data_ref, valor = coletar()
            snap[chave] = {"valor": valor, "data": data_ref}
            logger.info("Macro %s = %.2f (%s)", chave, valor, data_ref)
        except Exception as exc:  # noqa: BLE001 - degrade controlado por fonte
            erros.append(f"{chave}: {exc}")
            logger.warning("Macro %s falhou (%s) — mantendo valor anterior", chave, exc)

    snap["ano_focus_selic"] = ano_seguinte if "focus_selic_fim_ano_seguinte" in snap else None
    snap["atualizado_em"] = datetime.now().isoformat(timespec="seconds")
    snap["erros"] = erros
    return snap


def ler_macro(caminho: Path = ARQUIVO_MACRO) -> dict:
    """Le o JSON publicado (vazio se nao existir ou estiver corrompido)."""
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def salvar_macro(snap: dict, caminho: Path = ARQUIVO_MACRO) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")


def valores_macro(snap: dict | None = None) -> dict:
    """Valores prontos para o app, com fallback nas constantes de referencia.

    Retorna ``{chave: {"valor", "data", "fonte"}}`` para selic_meta, ipca_12m,
    focus_ipca_12m e focus_selic_fim_ano_seguinte (os dois ultimos podem vir None).
    """
    snap = ler_macro() if snap is None else snap
    fallback = {
        "selic_meta": SELIC_META_REF,
        "ipca_12m": IPCA_ATUAL,
        "focus_ipca_12m": None,
        "focus_selic_fim_ano_seguinte": None,
    }
    out = {}
    for chave, padrao in fallback.items():
        item = snap.get(chave)
        if isinstance(item, dict) and item.get("valor") is not None:
            out[chave] = {"valor": float(item["valor"]), "data": item.get("data"), "fonte": "BCB"}
        else:
            out[chave] = {"valor": padrao, "data": None, "fonte": "referência manual"}
    out["ano_focus_selic"] = snap.get("ano_focus_selic")
    out["atualizado_em"] = snap.get("atualizado_em")
    return out
