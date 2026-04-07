"""Script para executar pipeline de ingestão de CSV."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.config import config
from src.utils.constants import DATA_RAW


def main():
    """Executa pipeline completo de ingestão."""
    print("\n🏛️  Tesouro Direto WX — Pipeline de Ingestão\n")

    # 1. Localizar CSV mais recente em data/raw/
    csvs = sorted(DATA_RAW.glob("*.csv"))
    if not csvs:
        print("  ✗ Nenhum CSV encontrado em data/raw/")
        print("    Coloque o arquivo precotaxatesourodireto.csv nessa pasta.")
        return

    # Priorizar o arquivo oficial de preços e taxas
    arquivo = next(
        (c for c in csvs if "precotaxatesourodireto" in c.name.lower()),
        csvs[-1],
    )
    print(f"  ✓ Arquivo encontrado: {arquivo.name}")

    # 2. Validar
    print("  → Validando...")
    from src.ingestao.validacao import validar_csv
    resultado = validar_csv(arquivo)

    if not resultado["aprovado"]:
        print(f"  ✗ Validação falhou: {resultado['erros']}")
        return

    print(f"  ✓ Validação OK — {resultado['linhas']} linhas, {resultado['colunas']} colunas")

    # 3. Padronizar
    print("  → Padronizando...")
    from src.transformacao.padronizacao import padronizar
    df = padronizar(arquivo)
    print(f"  ✓ Padronização OK — {len(df)} registros")

    # 4. Enriquecer
    print("  → Enriquecendo...")
    from src.transformacao.enriquecimento import enriquecer
    df = enriquecer(df)
    print(f"  ✓ Enriquecimento OK — {len(df.columns)} colunas")

    # 5. Salvar
    from src.utils.constants import DATA_ENRIQUECIDO
    saida = DATA_ENRIQUECIDO / "base_enriquecida.parquet"
    df.to_parquet(saida, index=False)
    print(f"  ✓ Salvo em {saida}")

    print("\n✅ Ingestão concluída com sucesso.\n")


if __name__ == "__main__":
    main()
