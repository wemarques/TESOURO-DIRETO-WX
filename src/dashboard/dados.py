"""Carga e recarga dos datasets publicados consumidos pelo dashboard."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from src.ingestao.registro import obter_ultima_ingestao
from src.utils.config import config
from src.utils.constants import (
    DATA_AUDIT,
    DATA_ENRIQUECIDO,
    DATA_OUTPUTS,
    DATA_PADRONIZADO,
    DATA_PROCESSED,
    DATA_RAW,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Brasilia (UTC-3, sem horario de verao desde 2019)
BRT = timezone(timedelta(hours=-3))


def calcular_variacao_e_pu(
    df_ranking: pd.DataFrame, df_historico: pd.DataFrame
) -> pd.DataFrame:
    """Acrescenta colunas taxa_12m_atras, taxa_pp_12m e pu_compra_atual ao ranking."""
    df = df_ranking.copy()
    df["taxa_12m_atras"] = float("nan")
    df["taxa_pp_12m"] = float("nan")
    df["pu_compra_atual"] = float("nan")

    data_max = df_historico["data_base"].max()
    data_12m = data_max - pd.Timedelta(days=365)

    for idx, row in df.iterrows():
        hist = df_historico[
            (df_historico["tipo_titulo"] == row["tipo_titulo"])
            & (df_historico["data_vencimento"] == row["data_vencimento"])
        ].sort_values("data_base")

        if hist.empty:
            continue

        atual = hist.iloc[-1]
        if "pu_compra_manha" in atual.index and pd.notna(atual["pu_compra_manha"]):
            df.at[idx, "pu_compra_atual"] = float(atual["pu_compra_manha"])

        hist_antes = hist[hist["data_base"] <= data_12m]
        if hist_antes.empty:
            hist_antes = hist.iloc[[0]]
        if not hist_antes.empty:
            taxa_antiga = hist_antes.iloc[-1]["taxa_compra_manha"]
            taxa_atual = atual["taxa_compra_manha"]
            df.at[idx, "taxa_12m_atras"] = float(taxa_antiga)
            df.at[idx, "taxa_pp_12m"] = float(taxa_atual - taxa_antiga)

    return df


def build_calculadora_dataset(df_historico: pd.DataFrame) -> pd.DataFrame:
    """Dataset do snapshot mais recente para a calculadora (todos os titulos do dia)."""
    data_max = df_historico["data_base"].max()
    snapshot = df_historico[df_historico["data_base"] == data_max].copy()

    snapshot["pu_compra_atual"] = snapshot["pu_compra_manha"]

    snapshot["posicao_celula"] = (
        snapshot.groupby("celula_analitica")["score_a"]
        .rank(ascending=False, method="min")
        .astype(float)
    )
    snapshot["posicao_global"] = (
        snapshot["score_a"].rank(ascending=False, method="min").astype(float)
    )

    data_12m = data_max - pd.Timedelta(days=365)
    snapshot["taxa_12m_atras"] = float("nan")
    snapshot["taxa_pp_12m"] = float("nan")

    for idx, row in snapshot.iterrows():
        hist = df_historico[
            (df_historico["tipo_titulo"] == row["tipo_titulo"])
            & (df_historico["data_vencimento"] == row["data_vencimento"])
            & (df_historico["data_base"] <= data_12m)
        ].sort_values("data_base")
        if hist.empty:
            continue
        taxa_antiga = float(hist.iloc[-1]["taxa_compra_manha"])
        snapshot.at[idx, "taxa_12m_atras"] = taxa_antiga
        snapshot.at[idx, "taxa_pp_12m"] = float(
            row["taxa_compra_manha"] - taxa_antiga
        )

    return snapshot.reset_index(drop=True)


def ensure_data_exists() -> None:
    """Garante diretórios e pipeline inicial se outputs ainda não existirem."""
    diretorios = [
        DATA_RAW,
        DATA_PADRONIZADO,
        DATA_ENRIQUECIDO,
        DATA_PROCESSED,
        DATA_OUTPUTS,
        DATA_AUDIT,
    ]
    for d in diretorios:
        d.mkdir(parents=True, exist_ok=True)

    ranking_path = DATA_OUTPUTS / "ranking_atual.parquet"
    base_path = DATA_OUTPUTS / "base_analitica.parquet"
    if ranking_path.exists() and base_path.exists():
        return

    print("[boot] Sem dados em data/outputs/ - executando pipeline inicial...")
    scripts_dir = PROJECT_ROOT / "scripts"
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}

    for script in ["rodar_ingestao.py", "rodar_analytics.py"]:
        print(f"[boot] Rodando {script}...")
        result = subprocess.run(
            [sys.executable, str(scripts_dir / script)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=900,
            env=env,
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"[boot] {script} falhou:\n{result.stderr}")
            raise RuntimeError(f"Pipeline inicial falhou em {script}")

    print("[boot] Pipeline inicial concluido")


def build_summary_stats(
    df: pd.DataFrame,
    familia: str,
    score_col: str = "score_a",
) -> dict:
    """Estatísticas de resumo comparáveis apenas dentro da família selecionada."""
    if df.empty:
        return {"modo": "vazio", "total": 0}

    total_snapshot = len(df)

    if familia == "TODAS":
        return {"modo": "todas", "total": total_snapshot}

    df_fam = df[df["familia_normalizada"] == familia]
    if df_fam.empty:
        return {"modo": "vazio", "total": 0, "familia": familia}

    col_score = score_col if score_col in df_fam.columns else "score_a"
    df_ord = df_fam.sort_values(col_score, ascending=False, na_position="last")
    melhor_score_row = df_ord.iloc[0]
    maior_taxa_row = df_fam.loc[df_fam["taxa_compra_manha"].idxmax()]
    melhor_liq_row = df_fam.loc[df_fam["liquidez_norm"].idxmax()]

    return {
        "modo": "familia",
        "familia": familia,
        "melhor_score_valor": f"{melhor_score_row[col_score]:.3f}",
        "melhor_score_titulo": (
            f"{melhor_score_row['tipo_titulo']} "
            f"{melhor_score_row['data_vencimento'].strftime('%Y')}"
        ),
        "maior_taxa_valor": f"{maior_taxa_row['taxa_compra_manha']:.2f}%",
        "maior_taxa_titulo": (
            f"{maior_taxa_row['tipo_titulo']} "
            f"{maior_taxa_row['data_vencimento'].strftime('%Y')}"
        ),
        "melhor_liquidez_valor": f"{melhor_liq_row['liquidez_norm']:.2f}",
        "melhor_liquidez_titulo": (
            f"{melhor_liq_row['tipo_titulo']} "
            f"{melhor_liq_row['data_vencimento'].strftime('%Y')}"
        ),
        "total": len(df_fam),
    }


@dataclass
class EstadoDados:
    """Estado mutável dos DataFrames em memória (recarregável sem reiniciar o app)."""

    df_ranking: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_historico: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_calculadora: pd.DataFrame = field(default_factory=pd.DataFrame)
    data_atualizacao: str = "—"
    total_titulos: int = 0
    total_registros: int = 0
    familias: list[str] = field(default_factory=list)
    titulos_unicos: list[str] = field(default_factory=list)
    titulos_detalhados: list[dict] = field(default_factory=list)
    grupos_analiticos: list[str] = field(default_factory=list)
    info_ingestao: dict = field(default_factory=dict)
    carregado_em: datetime | None = None
    versao_metodologia: str = config.versao_metodologia

    def recarregar(self) -> None:
        """Relê parquets de ``data/outputs/`` e reconstrói datasets derivados."""
        df_ranking = pd.read_parquet(DATA_OUTPUTS / "ranking_atual.parquet")
        df_historico = pd.read_parquet(DATA_OUTPUTS / "base_analitica.parquet")

        df_ranking = calcular_variacao_e_pu(df_ranking, df_historico)
        df_calculadora = build_calculadora_dataset(df_historico)

        ultima_ingestao = obter_ultima_ingestao()
        info_ingestao = {
            "data_ingestao": (
                ultima_ingestao.get("data_ingestao", "")[:10] if ultima_ingestao else ""
            ),
            "metodo": ultima_ingestao.get("metodo_obtencao", "") if ultima_ingestao else "",
        }

        self.df_ranking = df_ranking
        self.df_historico = df_historico
        self.df_calculadora = df_calculadora
        self.data_atualizacao = df_ranking["data_base"].max().strftime("%d/%m/%Y")
        self.total_titulos = len(df_ranking)
        self.total_registros = len(df_historico)
        self.familias = sorted(df_ranking["familia_normalizada"].unique().tolist())
        self.titulos_unicos = sorted(df_historico["tipo_titulo"].unique().tolist())
        # So titulos ofertados HOJE (snapshot = ranking_atual), nao o historico inteiro.
        _det = (
            df_ranking[["tipo_titulo", "data_vencimento"]]
            .drop_duplicates()
            .sort_values(["tipo_titulo", "data_vencimento"])
        )
        self.titulos_detalhados = [
            {
                "label": f"{r.tipo_titulo} {pd.Timestamp(r.data_vencimento):%d/%m/%Y}",
                "value": f"{r.tipo_titulo}||{pd.Timestamp(r.data_vencimento):%Y-%m-%d}",
            }
            for r in _det.itertuples(index=False)
        ]
        self.grupos_analiticos = sorted(df_historico["grupo_analitico"].unique().tolist())
        self.info_ingestao = info_ingestao
        self.carregado_em = datetime.now(BRT)

    def meta(self) -> dict:
        """Metadados serializáveis para ``dcc.Store``."""
        return {
            "carregado_em": (
                self.carregado_em.isoformat(timespec="seconds")
                if self.carregado_em
                else None
            ),
            "data_atualizacao": self.data_atualizacao,
            "total_titulos": self.total_titulos,
            "versao_metodologia": self.versao_metodologia,
        }


def intervalo_recarga_ms() -> int:
    """Intervalo do ``dcc.Interval`` em ms (env ``DASH_RELOAD_INTERVAL_MS``, padrão 5 min)."""
    raw = os.environ.get("DASH_RELOAD_INTERVAL_MS", "300000")
    try:
        valor = int(raw)
    except ValueError:
        valor = 300000
    return max(valor, 60_000)
