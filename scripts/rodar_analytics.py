"""Script para recalcular scores e rankings."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.constants import DATA_ENRIQUECIDO, DATA_PROCESSED, DATA_OUTPUTS

COLS_RISCO = [
    "duration_macaulay", "duration_modificada", "convexidade",
    "var_pct_taxa_menos_1pp", "var_pct_taxa_mais_1pp",
    "taxa_nominal_equivalente", "inflacao_implicita",
]
COLS_MARCACAO = ["score_d", "percentil_taxa_24m", "margem_cdi_12m_pp", "cdi_esperado_12m"]


def main():
    """Executa pipeline analítico completo."""
    print("\n🏛️  Tesouro Direto WX — Pipeline Analítico\n")

    import pandas as pd

    # 1. Carregar base enriquecida
    base = DATA_ENRIQUECIDO / "base_enriquecida.parquet"
    if not base.exists():
        print("  ✗ Base enriquecida não encontrada. Execute rodar_ingestao.py primeiro.")
        return

    df = pd.read_parquet(base)
    print(f"  ✓ Base carregada — {len(df)} registros")

    # 2. Calcular métricas
    print("  → Calculando métricas...")
    from src.analytics.metricas import calcular_metricas
    df = calcular_metricas(df)

    # 2b. Inflacao implicita (Fisher) dos titulos IPCA vs curva prefixada
    from src.analytics.duration import calcular_inflacao_implicita
    df = calcular_inflacao_implicita(df)

    # 3. Ajustar curvas NSS por grupo (apenas snapshot mais recente)
    print("  → Ajustando curvas Nelson-Siegel-Svensson...")
    from src.analytics.curva import calcular_curva_por_grupo
    data_mais_recente = df["data_base"].max()
    df = calcular_curva_por_grupo(df, data_referencia=data_mais_recente)
    n_curva = df["curva_ajustada"].sum()
    n_total = len(df[df["data_base"] == df["data_base"].max()])
    print(f"  ✓ Curvas ajustadas — {n_curva:,} registros com curva".replace(",", "."))

    # 4. Calcular scores
    print("  → Calculando scores...")
    from src.analytics.score import calcular_score_a, calcular_score_b, calcular_score_c
    df = calcular_score_a(df)
    df = calcular_score_b(df)
    df = calcular_score_c(df)

    # 4b. Score D (marcacao a mercado) e margem vs CDI — so no snapshot atual
    print("  → Calculando Score D e margem vs CDI...")
    from src.analytics.marcacao import calcular_margem_cdi, calcular_score_d
    from src.ingestao.macro import valores_macro
    snap = df[df["data_base"] == df["data_base"].max()]
    snap = calcular_margem_cdi(calcular_score_d(snap, df), valores_macro())
    for col in COLS_MARCACAO:
        df[col] = float("nan")
        df.loc[snap.index, col] = snap[col]

    # 5. Gerar ranking (usa score_a para posições, inclui score_b e score_c)
    print("  → Gerando rankings...")
    from src.analytics.ranking import gerar_ranking
    ranking = gerar_ranking(df)

    # Incluir score_b e score_c no ranking
    snapshot_date = ranking["data_base"].iloc[0]
    extras = df.loc[
        df["data_base"] == snapshot_date,
        ["tipo_titulo", "data_vencimento", "score_b", "score_c", *COLS_RISCO, *COLS_MARCACAO],
    ]
    for col in ["score_b", "score_c", *COLS_RISCO, *COLS_MARCACAO]:
        if col not in ranking.columns:
            ranking = ranking.merge(
                extras[["tipo_titulo", "data_vencimento", col]],
                on=["tipo_titulo", "data_vencimento"],
                how="left",
            )

    # 6. Salvar
    df.to_parquet(DATA_PROCESSED / "base_analitica.parquet", index=False)
    ranking.to_parquet(DATA_OUTPUTS / "ranking_atual.parquet", index=False)
    ranking.to_csv(DATA_OUTPUTS / "ranking_atual.csv", index=False)

    # Publicar base analitica em outputs/ para o dashboard consumir
    cols_dashboard = [
        "data_base", "tipo_titulo", "data_vencimento", "anos_ate_vencimento",
        "familia_normalizada", "grupo_analitico", "bucket_prazo", "celula_analitica",
        "taxa_compra_manha", "taxa_venda_manha", "pu_compra_manha", "pu_venda_manha",
        "spread_compra_venda", "carry", "rv_zscore", "liquidez_norm",
        "score_a", "score_b", "score_c",
        "duration_macaulay", "duration_modificada", "convexidade",
        "var_pct_taxa_menos_1pp", "var_pct_taxa_mais_1pp",
        "taxa_nominal_equivalente", "inflacao_implicita",
    ]
    cols_existentes = [c for c in cols_dashboard if c in df.columns]
    df[cols_existentes].to_parquet(DATA_OUTPUTS / "base_analitica.parquet", index=False)
    print(f"  ✓ Ranking salvo — {len(ranking)} títulos (Score A + B + C + D)")

    print("\n✅ Analytics concluído.\n")


if __name__ == "__main__":
    main()
