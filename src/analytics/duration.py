"""Fluxos de caixa, duration, convexidade e sensibilidade a taxa por titulo.

Convencoes (ANBIMA / Tesouro Direto), validadas contra os PUs publicados:

- Prazo em dias uteis / 252, calendario ANBIMA (``calendario.py``).
- Liquidacao: PU de COMPRA usa D+1 util; PU de VENDA usa D+0. Para metricas
  de risco usamos a liquidacao de compra (D+1), a de quem entra hoje.
- Fluxos por familia (valores relativos; escala nao afeta duration):

  ============  ===========================================================
  Familia       Fluxos
  ============  ===========================================================
  PRE  (LTN)    1000 no vencimento
  PRE_JS (NTN-F) cupom 48,80885 (10% a.a.) em 01/01 e 01/07 + 1000 no venc.
  IPCA (NTN-B P) 1 VNA no vencimento
  IPCA_JS (NTN-B) cupom (1,06^0,5 - 1) VNA semestral + 1 VNA no vencimento
  IGPM_JS (NTN-C) cupom (1,12^0,5 - 1) VNA semestral + 1 VNA no vencimento
  RENDA (NTN-B1) 240 parcelas mensais de VNA/240, a ultima no vencimento
  EDUCA         60 parcelas mensais de VNA/60, a ultima no vencimento
  SELIC (LFT)   1 VNA no vencimento (taxa cotada = agio/desagio sobre Selic)
  ============  ===========================================================

  Para titulos IPCA o "fator" calculado aqui e PU / VNA; para Prefixados e o
  proprio PU. ``vna_implicito`` explora isso para auditar a base.

Atencao com o Tesouro Selic: a taxa cotada e um spread sobre a Selic, e o
risco de juros do titulo e praticamente nulo. As metricas sao calculadas em
relacao ao spread (correto matematicamente), mas ``duration_risco`` = 0 para
SELIC — e essa que entra na penalidade do Score B.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.analytics.calendario import dias_uteis, feriados_array

logger = logging.getLogger(__name__)

CUPOM_NTNF = 48.80885  # 1000 * ((1,10)^0,5 - 1), truncado como na ANBIMA
CUPOM_NTNB = 1.06**0.5 - 1
CUPOM_NTNC = 1.12**0.5 - 1

# tipo_titulo canonico -> (familia, regra de fluxo)
_REGRAS = {
    "Tesouro Prefixado": "bullet_1000",
    "Tesouro Prefixado com Juros Semestrais": "ntnf",
    "Tesouro IPCA+": "bullet_1",
    "Tesouro IPCA+ com Juros Semestrais": "ntnb",
    "Tesouro IGPM+ com Juros Semestrais": "ntnc",
    "Tesouro Renda+ Aposentadoria Extra": "renda",
    "Tesouro Educa+": "educa",
    "Tesouro Selic": "bullet_1",
}
TIPOS_POS_FIXADOS = {"Tesouro Selic"}


def valor_presente(valor_futuro: float, taxa_pct: float, anos: float) -> float:
    """VP = VF / (1 + i)^t — a relacao inversa taxa x preco."""
    return valor_futuro / (1 + taxa_pct / 100) ** anos


def inflacao_implicita(taxa_nominal_pct: float, taxa_real_pct: float) -> float:
    """Inflacao implicita (breakeven) por Fisher, em % a.a.

    breakeven = (1 + i_nominal) / (1 + i_real) - 1
    """
    return ((1 + taxa_nominal_pct / 100) / (1 + taxa_real_pct / 100) - 1) * 100


def liquidacao(data_base) -> np.ndarray:
    """Data de liquidacao da compra: proximo dia util (D+1) apos ``data_base``."""
    d = np.asarray(pd.to_datetime(data_base)).astype("datetime64[D]")
    return np.busday_offset(d, 1, roll="forward", holidays=feriados_array())


def _datas_semestrais(vencimento: pd.Timestamp, ate: pd.Timestamp) -> list[pd.Timestamp]:
    datas, d = [], vencimento
    while d > ate:
        datas.append(d)
        d = d - pd.DateOffset(months=6)
    return datas[::-1]


def fluxos(tipo_titulo: str, vencimento, inicio=None) -> tuple[np.ndarray, np.ndarray]:
    """Datas e valores de todos os fluxos futuros (> ``inicio``) do titulo.

    Args:
        tipo_titulo: nome canonico (chave de ``MAPA_FAMILIA``).
        vencimento: data de vencimento (ultimo fluxo).
        inicio: so retorna fluxos estritamente posteriores; ``None`` = todos.

    Returns:
        (datas datetime64[D], valores float) em ordem cronologica.
    """
    regra = _REGRAS.get(tipo_titulo)
    if regra is None:
        raise ValueError(f"Tipo de titulo sem regra de fluxo: {tipo_titulo!r}")
    venc = pd.Timestamp(vencimento).normalize()
    corte = pd.Timestamp(inicio).normalize() if inicio is not None else pd.Timestamp.min

    if regra == "bullet_1000":
        datas, valores = [venc], [1000.0]
    elif regra == "bullet_1":
        datas, valores = [venc], [1.0]
    elif regra in ("ntnf", "ntnb", "ntnc"):
        cupom = {"ntnf": CUPOM_NTNF, "ntnb": CUPOM_NTNB, "ntnc": CUPOM_NTNC}[regra]
        principal = 1000.0 if regra == "ntnf" else 1.0
        # Gera o cronograma completo a partir do vencimento (o corte vem depois)
        limite = max(corte, venc - pd.DateOffset(years=60))
        datas = _datas_semestrais(venc, limite)
        valores = [cupom] * len(datas)
        valores[-1] += principal
    else:  # renda / educa: parcelas mensais iguais, a ultima no vencimento
        n = 240 if regra == "renda" else 60
        datas = [venc - pd.DateOffset(months=k) for k in range(n)][::-1]
        valores = [1.0 / n] * n

    datas = np.array(datas, dtype="datetime64[D]")
    valores = np.array(valores, dtype=float)
    mascara = datas > np.datetime64(corte.date()) if inicio is not None else slice(None)
    return datas[mascara], valores[mascara]


@dataclass(frozen=True)
class MetricasRisco:
    """Metricas de risco de taxa de um titulo numa data."""

    fator: float              # PU (prefixados) ou PU/VNA (indexados)
    duration_macaulay: float  # anos (du/252)
    duration_modificada: float
    convexidade: float

    def variacao_aprox(self, delta_pp: float, com_convexidade: bool = True) -> float:
        """Variacao % aproximada do PU para um choque de ``delta_pp`` p.p."""
        dy = delta_pp / 100
        var = -self.duration_modificada * dy
        if com_convexidade:
            var += 0.5 * self.convexidade * dy * dy
        return var


def _fator(valores: np.ndarray, anos: np.ndarray, taxa: float) -> float:
    return float((valores / (1 + taxa) ** anos).sum())


def metricas_risco(tipo_titulo: str, vencimento, data_base, taxa_pct: float) -> MetricasRisco:
    """Duration de Macaulay, modificada e convexidade (base du/252, liquidacao D+1)."""
    liq = liquidacao(data_base)
    datas, valores = fluxos(tipo_titulo, vencimento, inicio=pd.Timestamp(liq))
    if len(datas) == 0:
        return MetricasRisco(np.nan, np.nan, np.nan, np.nan)
    anos = dias_uteis(liq, datas) / 252
    i = taxa_pct / 100
    vp = valores / (1 + i) ** anos
    p = vp.sum()
    mac = float((anos * vp).sum() / p)
    conv = float((anos * (anos + 1) * vp).sum() / (p * (1 + i) ** 2))
    return MetricasRisco(float(p), mac, mac / (1 + i), conv)


def preco_relativo(tipo_titulo: str, vencimento, data_base, taxa_pct: float) -> float:
    """Fator de precificacao: PU (prefixados) ou PU/VNA (indexados)."""
    return metricas_risco(tipo_titulo, vencimento, data_base, taxa_pct).fator


def variacao_exata(
    tipo_titulo: str, vencimento, data_base, taxa_pct: float, delta_pp: float
) -> float:
    """Variacao % exata do PU (reprecificacao) para um choque de ``delta_pp`` p.p."""
    base = preco_relativo(tipo_titulo, vencimento, data_base, taxa_pct)
    choque = preco_relativo(tipo_titulo, vencimento, data_base, taxa_pct + delta_pp)
    return choque / base - 1


def vna_implicito(tipo_titulo: str, vencimento, data_base, taxa_pct: float, pu: float) -> float:
    """VNA implicito = PU / fator. Em titulos IPCA deve coincidir entre si no mesmo dia."""
    return pu / preco_relativo(tipo_titulo, vencimento, data_base, taxa_pct)


def decompor_retorno(
    tipo_titulo: str,
    vencimento,
    data0,
    taxa0_pct: float,
    pu0: float,
    data1,
    taxa1_pct: float,
    pu1: float,
) -> dict:
    """Separa o retorno entre duas datas em efeito-taxa e carrego (+ indexacao).

    - efeito_taxa: reprecificacao em ``data1`` da taxa antiga para a nova,
      com tudo o mais constante — o "ganho de marcacao a mercado".
    - carrego_indexacao: o restante (passagem do tempo a taxa antiga + correcao
      do VNA pelo IPCA/Selic nos indexados). Fecha a identidade
      (1 + total) = (1 + efeito_taxa) * (1 + carrego_indexacao).
    """
    f_antiga = preco_relativo(tipo_titulo, vencimento, data1, taxa0_pct)
    f_nova = preco_relativo(tipo_titulo, vencimento, data1, taxa1_pct)
    total = pu1 / pu0 - 1
    efeito_taxa = f_nova / f_antiga - 1
    carrego = (1 + total) / (1 + efeito_taxa) - 1
    return {
        "retorno_total": total,
        "efeito_taxa": efeito_taxa,
        "carrego_indexacao": carrego,
        "delta_taxa_pp": taxa1_pct - taxa0_pct,
    }


def calcular_duration(df: pd.DataFrame, coluna_taxa: str = "taxa_compra_manha") -> pd.DataFrame:
    """Acrescenta metricas de risco a cada linha (vetorizado por titulo).

    Colunas criadas: ``duration_macaulay``, ``duration_modificada``,
    ``convexidade``, ``duration_risco`` (0 para Tesouro Selic) e
    ``var_pct_taxa_menos_1pp`` / ``var_pct_taxa_mais_1pp`` (exatas; NaN no Selic,
    cujo spread nunca se move 1 p.p.).
    """
    df = df.copy()
    novas = [
        "duration_macaulay", "duration_modificada", "convexidade",
        "var_pct_taxa_menos_1pp", "var_pct_taxa_mais_1pp",
    ]
    for c in novas:
        df[c] = np.nan

    for (tipo, venc), grupo in df.groupby(["tipo_titulo", "data_vencimento"], sort=False):
        if tipo not in _REGRAS:
            logger.warning("Sem regra de fluxo para %s — duration ignorada", tipo)
            continue
        datas, valores = fluxos(tipo, venc)
        liq = liquidacao(grupo["data_base"].values)                      # (n,)
        anos = np.busday_count(
            liq[:, None], datas[None, :], holidays=feriados_array()
        ) / 252.0                                                        # (n, k)
        vivo = anos > 0
        i = (grupo[coluna_taxa].to_numpy(dtype=float) / 100)[:, None]    # (n, 1)

        def _pv(taxa):
            return np.where(vivo, valores[None, :] / (1 + taxa) ** anos, 0.0)

        vp = _pv(i)
        p = vp.sum(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            mac = (anos * vp).sum(axis=1) / p
            conv = (anos * (anos + 1) * vp).sum(axis=1) / (p * (1 + i[:, 0]) ** 2)
            menos = _pv(i - 0.01).sum(axis=1) / p - 1
            mais = _pv(i + 0.01).sum(axis=1) / p - 1

        idx = grupo.index
        df.loc[idx, "duration_macaulay"] = mac
        df.loc[idx, "duration_modificada"] = mac / (1 + i[:, 0])
        df.loc[idx, "convexidade"] = conv
        if tipo not in TIPOS_POS_FIXADOS:
            df.loc[idx, "var_pct_taxa_menos_1pp"] = menos
            df.loc[idx, "var_pct_taxa_mais_1pp"] = mais

    pos = df["tipo_titulo"].isin(TIPOS_POS_FIXADOS)
    df["duration_risco"] = df["duration_modificada"].where(~pos, 0.0)
    return df


TIPOS_IPCA = {
    "Tesouro IPCA+",
    "Tesouro IPCA+ com Juros Semestrais",
    "Tesouro Renda+ Aposentadoria Extra",
    "Tesouro Educa+",
}
TIPOS_NOMINAIS = {"Tesouro Prefixado", "Tesouro Prefixado com Juros Semestrais"}


def calcular_inflacao_implicita(
    df: pd.DataFrame, coluna_taxa: str = "taxa_compra_manha", folga_anos: float = 0.5
) -> pd.DataFrame:
    """Inflacao implicita (Fisher) de cada titulo IPCA contra a curva prefixada.

    Para cada data, a taxa nominal de referencia e interpolada (linear) na
    duration de Macaulay do titulo IPCA, usando os pontos (duration, taxa) dos
    Prefixados e Prefixados com Juros do mesmo dia. Fora do alcance da curva
    prefixada (+ ``folga_anos``) o valor fica NaN: extrapolar uma curva de ~6
    anos para um Renda+ de 46 anos de duration seria inventar numero.

    Requer ``duration_macaulay`` (ver ``calcular_duration``). Cria
    ``taxa_nominal_equivalente`` e ``inflacao_implicita`` (% a.a.).
    """
    df = df.copy()
    df["taxa_nominal_equivalente"] = np.nan
    df["inflacao_implicita"] = np.nan

    for _, dia in df.groupby("data_base"):
        nom = dia[dia["tipo_titulo"].isin(TIPOS_NOMINAIS)].dropna(
            subset=["duration_macaulay", coluna_taxa]
        )
        if len(nom) < 2:
            continue
        nom = nom.sort_values("duration_macaulay")
        x, y = nom["duration_macaulay"].to_numpy(), nom[coluna_taxa].to_numpy()
        reais = dia[dia["tipo_titulo"].isin(TIPOS_IPCA)]
        dur = reais["duration_macaulay"].to_numpy()
        dentro = (dur >= x.min() - folga_anos) & (dur <= x.max() + folga_anos)
        nominal = np.where(dentro, np.interp(dur, x, y), np.nan)
        df.loc[reais.index, "taxa_nominal_equivalente"] = nominal
        df.loc[reais.index, "inflacao_implicita"] = (
            (1 + nominal / 100) / (1 + reais[coluna_taxa].to_numpy() / 100) - 1
        ) * 100
    return df
