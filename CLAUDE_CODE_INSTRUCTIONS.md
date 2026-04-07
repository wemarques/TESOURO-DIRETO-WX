# Instruções para Claude Code — Setup do Projeto Tesouro Direto WX

## Contexto
Este projeto já possui documentação completa de planejamento e um scaffold pronto.
O zip `TESOURO-DIRETO-WX.zip` contém toda a estrutura de pastas, código-fonte
inicial, documentação, testes e configuração.

## Passo a passo para o Claude Code

### 1. Extrair o projeto na pasta local
```bash
cd C:\TESOURO-DIRETO-WX
# Se a pasta não existe, crie-a
# Extraia o conteúdo do zip TESOURO-DIRETO-WX.zip aqui
```

### 2. Inicializar o repositório Git
```bash
cd C:\TESOURO-DIRETO-WX
git init
git remote add origin https://github.com/wemarques/TESOURO-DIRETO-WX.git
git add .
git commit -m "feat: scaffold inicial do projeto com documentação completa"
git branch -M main
git push -u origin main
```

### 3. Criar ambiente virtual e instalar dependências
```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -e ".[dev]"
```

### 4. Rodar testes para validar o setup
```bash
pytest tests/ -v
```

### 5. Colocar o CSV de dados na pasta correta
```bash
# Copie o arquivo precotaxatesourodireto.csv para:
# C:\TESOURO-DIRETO-WX\data\raw\precotaxatesourodireto.csv
```

### 6. Executar pipeline de ingestão
```bash
python scripts/rodar_ingestao.py
```

### 7. Executar pipeline analítico
```bash
python scripts/rodar_analytics.py
```

## Estrutura dos arquivos criados

| Arquivo | O que é |
|---|---|
| `CLAUDE.md` | **Arquivo principal** — o Claude Code deve ler este primeiro |
| `README.md` | Documentação pública do repositório GitHub |
| `pyproject.toml` | Dependências e configuração Python |
| `.gitignore` | Ignora CSVs grandes, __pycache__, .venv |
| `docs/` | 6 documentos de planejamento e metodologia |
| `src/ingestao/validacao.py` | Validação em 3 camadas (física, estrutural, semântica) |
| `src/transformacao/padronizacao.py` | Limpeza e normalização do CSV |
| `src/transformacao/enriquecimento.py` | Variáveis derivadas e flags |
| `src/analytics/metricas.py` | Carry, RV, liquidez, duration |
| `src/analytics/score.py` | Fórmulas A, B, C de scoring |
| `src/analytics/ranking.py` | Ranking por célula analítica |
| `src/utils/constants.py` | Enums, mapas, pesos, paths |
| `src/utils/config.py` | Configuração centralizada |
| `tests/` | Testes para validação e padronização |
| `scripts/` | Scripts de execução e setup |

## O que implementar em seguida (Fase 2)

1. **Dashboard com Dash/Plotly** — `src/dashboard/app.py`
   - Visão geral com ranking por família
   - Gráfico de série temporal de taxas
   - Detalhamento por título
   - Metadados de última atualização

2. **Fórmula B** — já tem stub em `src/analytics/score.py`

3. **Pipeline automático** — `src/ingestao/monitor.py` + `download.py`

4. **Curva de referência** — `src/analytics/curva.py` (Nelson-Siegel-Svensson)
