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

    # 3. Calcular score
    print("  → Calculando scores...")
    from src.analytics.score import calcular_score_a
    df = calcular_score_a(df)

    # 4. Gerar ranking
    print("  → Gerando rankings...")
    from src.analytics.ranking import gerar_ranking
    ranking = gerar_ranking(df)

    # 5. Salvar
    df.to_parquet(DATA_PROCESSED / "base_analitica.parquet", index=False)
    ranking.to_parquet(DATA_OUTPUTS / "ranking_atual.parquet", index=False)
    ranking.to_csv(DATA_OUTPUTS / "ranking_atual.csv", index=False)
    print(f"  ✓ Ranking salvo — {len(ranking)} títulos ranqueados")

    print("\n✅ Analytics concluído.\n")


if __name__ == "__main__":
    main()
