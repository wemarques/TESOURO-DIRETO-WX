"""
Script de bootstrap do projeto Tesouro Direto WX.
Cria estrutura de diretórios e valida ambiente.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DIRETORIOS = [
    "data/raw",
    "data/interim/padronizado",
    "data/interim/enriquecido",
    "data/processed",
    "data/outputs",
    "data/audit",
    "data/audit/incidentes",
    "notebooks",
]


def criar_estrutura():
    """Cria diretórios do projeto e .gitkeep."""
    for d in DIRETORIOS:
        path = PROJECT_ROOT / d
        path.mkdir(parents=True, exist_ok=True)
        gitkeep = path / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()
        print(f"  ✓ {d}/")


def verificar_python():
    """Verifica versão mínima do Python."""
    v = sys.version_info
    if v.major < 3 or (v.major == 3 and v.minor < 12):
        print(f"  ⚠ Python {v.major}.{v.minor} detectado — recomendado 3.12+")
    else:
        print(f"  ✓ Python {v.major}.{v.minor}.{v.micro}")


def verificar_dependencias():
    """Verifica se dependências principais estão instaladas."""
    deps = ["pandas", "numpy", "plotly", "dash", "scipy"]
    for dep in deps:
        try:
            __import__(dep)
            print(f"  ✓ {dep}")
        except ImportError:
            print(f"  ✗ {dep} — instale com: pip install -e .")


if __name__ == "__main__":
    print("\n🏛️  Tesouro Direto WX — Setup do Projeto\n")

    print("1. Criando estrutura de diretórios...")
    criar_estrutura()

    print("\n2. Verificando Python...")
    verificar_python()

    print("\n3. Verificando dependências...")
    verificar_dependencias()

    print("\n✅ Setup concluído. Próximos passos:")
    print("   1. Coloque o CSV oficial em data/raw/")
    print("   2. Execute: python scripts/rodar_ingestao.py")
    print()
