"""Script para recalcular scores e rankings."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.constants import DATA_ENRIQUECIDO, DATA_PROCESSED, DATA_OUTPUTS


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

    # 3. Calcular scores
    print("  → Calculando scores...")
    from src.analytics.score import calcular_score_a, calcular_score_b
    df = calcular_score_a(df)
    df = calcular_score_b(df)

    # 4. Gerar ranking (usa score_a para posições, mas inclui score_b)
    print("  → Gerando rankings...")
    from src.analytics.ranking import gerar_ranking
    ranking = gerar_ranking(df)

    # Incluir score_b no ranking
    if "score_b" not in ranking.columns:
        snapshot_date = ranking["data_base"].iloc[0]
        score_b_map = df.loc[
            df["data_base"] == snapshot_date,
            ["tipo_titulo", "data_vencimento", "score_b"],
        ]
        ranking = ranking.merge(score_b_map, on=["tipo_titulo", "data_vencimento"], how="left")

    # 5. Salvar
    df.to_parquet(DATA_PROCESSED / "base_analitica.parquet", index=False)
    ranking.to_parquet(DATA_OUTPUTS / "ranking_atual.parquet", index=False)
    ranking.to_csv(DATA_OUTPUTS / "ranking_atual.csv", index=False)
    print(f"  ✓ Ranking salvo — {len(ranking)} títulos ranqueados (Score A + Score B)")

    print("\n✅ Analytics concluído.\n")


if __name__ == "__main__":
    main()
