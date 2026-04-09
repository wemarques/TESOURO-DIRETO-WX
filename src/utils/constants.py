"""Constantes do projeto Tesouro Direto WX."""

from enum import Enum
from pathlib import Path

# === Caminhos ===
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DATA_RAW = DATA_DIR / "raw"
DATA_PADRONIZADO = DATA_DIR / "interim" / "padronizado"
DATA_ENRIQUECIDO = DATA_DIR / "interim" / "enriquecido"
DATA_PROCESSED = DATA_DIR / "processed"
DATA_OUTPUTS = DATA_DIR / "outputs"
DATA_AUDIT = DATA_DIR / "audit"


# === Schema do CSV oficial ===
COLUNAS_ORIGINAIS = [
    "Tipo Titulo",
    "Data Vencimento",
    "Data Base",
    "Taxa Compra Manha",
    "Taxa Venda Manha",
    "PU Compra Manha",
    "PU Venda Manha",
    "PU Base Manha",
]

MAPA_COLUNAS = {
    "Tipo Titulo": "tipo_titulo",
    "Data Vencimento": "data_vencimento",
    "Data Base": "data_base",
    "Taxa Compra Manha": "taxa_compra_manha",
    "Taxa Venda Manha": "taxa_venda_manha",
    "PU Compra Manha": "pu_compra_manha",
    "PU Venda Manha": "pu_venda_manha",
    "PU Base Manha": "pu_base_manha",
}

COLUNAS_NUMERICAS = [
    "taxa_compra_manha",
    "taxa_venda_manha",
    "pu_compra_manha",
    "pu_venda_manha",
    "pu_base_manha",
]

COLUNAS_DATA = ["data_vencimento", "data_base"]


# === Famílias de títulos ===
class FamiliaTitulo(str, Enum):
    SELIC = "SELIC"
    PRE = "PRE"
    PRE_JS = "PRE_JS"
    IPCA = "IPCA"
    IPCA_JS = "IPCA_JS"
    IGPM_JS = "IGPM_JS"
    EDUCA = "EDUCA"
    RENDA = "RENDA"


MAPA_FAMILIA = {
    "Tesouro Selic": FamiliaTitulo.SELIC,
    "Tesouro Prefixado": FamiliaTitulo.PRE,
    "Tesouro Prefixado com Juros Semestrais": FamiliaTitulo.PRE_JS,
    "Tesouro IPCA+": FamiliaTitulo.IPCA,
    "Tesouro IPCA+ com Juros Semestrais": FamiliaTitulo.IPCA_JS,
    "Tesouro IGPM+ com Juros Semestrais": FamiliaTitulo.IGPM_JS,
    "Tesouro Educa+": FamiliaTitulo.EDUCA,
    "Tesouro Renda+ Aposentadoria Extra": FamiliaTitulo.RENDA,
}


# === Grupos analíticos (comparabilidade) ===
class GrupoAnalitico(str, Enum):
    POS_FIXADO = "POS_FIXADO"
    NOMINAL_BULLET = "NOMINAL_BULLET"
    NOMINAL_CUPOM = "NOMINAL_CUPOM"
    REAL_BULLET = "REAL_BULLET"
    REAL_CUPOM = "REAL_CUPOM"
    PLANEJAMENTO = "PLANEJAMENTO"


FAMILIA_PARA_GRUPO = {
    FamiliaTitulo.SELIC: GrupoAnalitico.POS_FIXADO,
    FamiliaTitulo.PRE: GrupoAnalitico.NOMINAL_BULLET,
    FamiliaTitulo.PRE_JS: GrupoAnalitico.NOMINAL_CUPOM,
    FamiliaTitulo.IPCA: GrupoAnalitico.REAL_BULLET,
    FamiliaTitulo.IPCA_JS: GrupoAnalitico.REAL_CUPOM,
    FamiliaTitulo.IGPM_JS: GrupoAnalitico.REAL_CUPOM,
    FamiliaTitulo.EDUCA: GrupoAnalitico.PLANEJAMENTO,
    FamiliaTitulo.RENDA: GrupoAnalitico.PLANEJAMENTO,
}


# === Buckets de prazo ===
class BucketPrazo(str, Enum):
    CURTO = "CURTO"       # ≤ 2 anos
    INTER = "INTER"       # > 2 e ≤ 5 anos
    LONGO = "LONGO"       # > 5 e ≤ 15 anos
    ULTRA = "ULTRA"       # > 15 anos


LIMITES_BUCKET = {
    BucketPrazo.CURTO: (0, 2),
    BucketPrazo.INTER: (2, 5),
    BucketPrazo.LONGO: (5, 15),
    BucketPrazo.ULTRA: (15, float("inf")),
}


# === Pesos das fórmulas de score ===
PESOS_FORMULA_A = {
    "carry": 0.40,
    "rv": 0.40,
    "liquidez": 0.20,
}

PESOS_FORMULA_B = {
    "carry": 0.35,
    "rv": 0.30,
    "liquidez": 0.15,
    "risco": 0.20,
}

PESOS_FORMULA_C = {
    "carry": 0.30,
    "residuo_curva": 0.40,
    "rolldown": 0.15,
    "liquidez": 0.15,
}


# === Indicadores macro (valores de referencia, atualizar manualmente) ===
IPCA_ATUAL = 3.81  # IPCA acumulado 12 meses (% a.a.)


# === Fontes oficiais ===
URL_TESOURO_CKAN = (
    "https://www.tesourotransparente.gov.br/ckan/dataset/"
    "taxas-dos-titulos-ofertados-pelo-tesouro-direto"
)
URL_TESOURO_HISTORICO = (
    "https://www.tesourodireto.com.br/produtos/dados-sobre-titulos/"
    "historico-de-precos-e-taxas"
)
