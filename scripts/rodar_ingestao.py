"""Script para executar pipeline completo de ingestão de CSV.

Fluxo:
1. Verificar se há atualização na fonte oficial (CKAN)
2. Baixar CSV com retry e fallback
3. Registrar metadados da carga
4. Validar integridade do arquivo
5. Padronizar schema
6. Enriquecer com variáveis derivadas
7. Publicar resultado em data/outputs/
8. Em caso de falha, manter última versão válida e registrar incidente

Uso:
    python scripts/rodar_ingestao.py              # verifica e baixa se novo
    python scripts/rodar_ingestao.py --forcar      # força reprocessamento local
    python scripts/rodar_ingestao.py --local       # usa CSV existente em data/raw/
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.constants import DATA_ENRIQUECIDO, DATA_RAW


def _localizar_csv_local() -> Path | None:
    """Localiza o CSV mais recente em data/raw/."""
    csvs = sorted(DATA_RAW.glob("*.csv"))
    if not csvs:
        return None
    return next(
        (c for c in csvs if "precotaxatesourodireto" in c.name.lower()),
        csvs[-1],
    )


def main():
    """Executa pipeline completo de ingestão."""
    parser = argparse.ArgumentParser(description="Pipeline de ingestao Tesouro Direto WX")
    parser.add_argument("--forcar", action="store_true", help="Forcar download mesmo sem atualizacao")
    parser.add_argument("--local", action="store_true", help="Usar CSV existente em data/raw/")
    args = parser.parse_args()

    print("\n  Tesouro Direto WX -- Pipeline de Ingestao\n")

    arquivo = None
    info_download = None

    if args.local:
        # Modo local: usar CSV existente
        arquivo = _localizar_csv_local()
        if not arquivo:
            print("  x Nenhum CSV encontrado em data/raw/")
            return
        print(f"  ok Modo local: {arquivo.name}")
    else:
        # Modo online: verificar atualizacao e baixar
        print("  -> Verificando atualizacao na fonte oficial...")
        from src.ingestao.monitor import verificar_atualizacao
        resultado_monitor = verificar_atualizacao()

        if not resultado_monitor.tem_atualizacao and not args.forcar:
            print(f"  ok {resultado_monitor.mensagem}")
            print("  -> Base ja esta atualizada. Use --forcar para reprocessar.")
            return

        if resultado_monitor.tem_atualizacao:
            print(f"  ok Atualizacao detectada via {resultado_monitor.metodo}")
        else:
            print("  -> Forcando download...")

        # Baixar
        print("  -> Baixando CSV...")
        from src.ingestao.download import baixar_csv
        info_download = baixar_csv(
            url=resultado_monitor.url_csv,
            metodo=resultado_monitor.metodo,
        )

        if info_download is None:
            print("  x Download falhou em todas as tentativas")
            from src.ingestao.registro import registrar_incidente
            registrar_incidente(
                "download_falhou",
                "Todas as tentativas de download falharam",
                {"url": resultado_monitor.url_csv, "metodo": resultado_monitor.metodo},
            )
            print("  -> Incidente registrado. Mantendo ultima versao valida.")
            return

        arquivo = info_download["caminho"]
        print(f"  ok Baixado: {info_download['nome_arquivo']} ({info_download['tamanho_bytes']:,} bytes)".replace(",", "."))

    # Validar
    print("  -> Validando...")
    from src.ingestao.validacao import validar_csv
    resultado = validar_csv(arquivo)

    if not resultado["aprovado"]:
        print(f"  x Validacao falhou: {resultado['erros']}")
        from src.ingestao.registro import registrar_incidente, registrar_carga
        if info_download:
            registrar_carga(info_download, "quarentena", f"Erros: {resultado['erros']}")
        registrar_incidente(
            "validacao_falhou",
            f"CSV nao passou na validacao: {resultado['erros']}",
            {"arquivo": str(arquivo)},
        )
        print("  -> Incidente registrado. Mantendo ultima versao valida.")
        return

    print(f"  ok Validacao OK -- {resultado['linhas']} linhas, {resultado['colunas']} colunas")

    # Registrar carga
    if info_download:
        from src.ingestao.registro import registrar_carga
        registrar_carga(info_download, "aprovado")
        print(f"  ok Carga registrada no catalogo")

    # Padronizar
    print("  -> Padronizando...")
    from src.transformacao.padronizacao import padronizar
    df = padronizar(arquivo)
    print(f"  ok Padronizacao OK -- {len(df)} registros")

    # Enriquecer
    print("  -> Enriquecendo...")
    from src.transformacao.enriquecimento import enriquecer
    df = enriquecer(df)
    print(f"  ok Enriquecimento OK -- {len(df.columns)} colunas")

    # Salvar base enriquecida
    saida = DATA_ENRIQUECIDO / "base_enriquecida.parquet"
    df.to_parquet(saida, index=False)
    print(f"  ok Salvo em {saida}")

    print("\n  Ingestao concluida com sucesso.\n")


if __name__ == "__main__":
    main()
