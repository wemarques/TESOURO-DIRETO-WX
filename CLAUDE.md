# CLAUDE.md — Tesouro Direto WX

## Visão Geral do Projeto

Sistema analítico para **identificação de oportunidades de investimento em títulos do Tesouro Direto brasileiro**. O projeto consome dados históricos oficiais (CSV) de preços e taxas, aplica um framework quantitativo de scoring multifatorial e entrega resultados via dashboard interativo e relatórios analíticos.

**Repositório:** https://github.com/wemarques/TESOURO-DIRETO-WX  
**Pasta local:** `C:\TESOURO-DIRETO-WX`  
**Stack principal:** Python 3.12+ | Pandas | Plotly/Dash | Git

---

## Arquitetura do Projeto

```
TESOURO-DIRETO-WX/
├── CLAUDE.md                          # ← ESTE ARQUIVO (leia sempre)
├── README.md                          # Documentação pública do repositório
├── .gitignore
├── pyproject.toml                     # Dependências e configuração do projeto
│
├── docs/                              # Documentação metodológica e operacional
│   ├── plano-de-trabalho.md           # Plano de trabalho completo
│   ├── metodologia-operacional.md     # Fórmulas, segmentação, validação
│   ├── politica-ingestao-csv.md       # Regras de coleta, versionamento, auditoria
│   ├── desenho-rotina-automatica.md   # Pipeline de ingestão → publicação
│   ├── notas-pesquisa.md              # Referências acadêmicas e institucionais
│   └── dicionario-dados.md            # Schema oficial da base analítica
│
├── data/                              # Dados (NÃO versionar CSVs grandes)
│   ├── raw/                           # CSV bruto oficial — IMUTÁVEL
│   ├── interim/
│   │   ├── padronizado/               # Dados limpos e tipados
│   │   └── enriquecido/               # Dados com prazo, flags, buckets
│   ├── processed/                     # Métricas, curvas, scores, rankings
│   ├── outputs/                       # Datasets publicáveis para dashboard
│   └── audit/                         # Logs, hashes, inventários de carga
│
├── src/                               # Código-fonte principal
│   ├── __init__.py
│   ├── ingestao/                      # Pipeline de ingestão de CSV
│   │   ├── __init__.py
│   │   ├── monitor.py                 # Verificar disponibilidade de novo CSV
│   │   ├── download.py                # Capturar CSV oficial
│   │   ├── registro.py                # Metadados, hash, inventário
│   │   └── validacao.py               # Validação física, estrutural, semântica
│   │
│   ├── transformacao/                 # Padronização e enriquecimento
│   │   ├── __init__.py
│   │   ├── padronizacao.py            # Normalizar colunas, tipos, datas
│   │   └── enriquecimento.py          # Prazo, buckets, flags, chaves
│   │
│   ├── analytics/                     # Motor analítico
│   │   ├── __init__.py
│   │   ├── curva.py                   # Construção de curvas de referência
│   │   ├── metricas.py                # Carry, RV, liquidez, duration aprox
│   │   ├── score.py                   # Fórmulas A, B, C de oportunidade
│   │   └── ranking.py                 # Ranking por célula analítica
│   │
│   ├── dashboard/                     # Interface visual
│   │   ├── __init__.py
│   │   ├── app.py                     # App principal (Dash/Plotly ou React)
│   │   ├── layouts.py                 # Layouts das páginas
│   │   └── callbacks.py               # Interatividade
│   │
│   └── utils/                         # Utilitários compartilhados
│       ├── __init__.py
│       ├── config.py                  # Configurações globais
│       ├── logging_setup.py           # Setup de logs
│       └── constants.py               # Constantes do projeto
│
├── tests/                             # Testes automatizados
│   ├── test_validacao.py
│   ├── test_padronizacao.py
│   ├── test_metricas.py
│   └── test_score.py
│
├── notebooks/                         # Exploração e protótipos
│   └── 01_exploracao_inicial.ipynb
│
└── scripts/                           # Scripts operacionais
    ├── rodar_ingestao.py              # Executar pipeline de ingestão
    ├── rodar_analytics.py             # Recalcular scores e rankings
    └── setup_projeto.py               # Bootstrap inicial do projeto
```

---

## Contexto de Negócio

### O que o sistema faz
1. **Ingere** CSV oficial do Tesouro Transparente / Tesouro Direto
2. **Valida** integridade física, estrutural e semântica
3. **Padroniza** colunas, tipos, datas, decimais
4. **Enriquece** com prazo remanescente, flags de família, buckets
5. **Calcula** métricas (carry, valor relativo, liquidez, duration aprox)
6. **Pontua** via score multifatorial (3 fórmulas candidatas)
7. **Publica** dashboard e relatórios com dados validados

### Regra de ouro
> **Oportunidade ≠ taxa mais alta.** Oportunidade = carry + valor relativo na curva + liquidez + ajuste por risco de taxa, comparado APENAS dentro de títulos da mesma família e bucket.

---

## Dados: Schema da Base

### Colunas do CSV oficial (`precotaxatesourodireto.csv`)

| Coluna original | Tipo | Descrição |
|---|---|---|
| `Tipo Titulo` | string | Família do título (ex: "Tesouro IPCA+") |
| `Data Vencimento` | date | Data de vencimento do título |
| `Data Base` | date | Data de referência da observação |
| `Taxa Compra Manha` | float | Taxa de compra (% a.a.) |
| `Taxa Venda Manha` | float | Taxa de venda (% a.a.) |
| `PU Compra Manha` | float | Preço unitário de compra (R$) |
| `PU Venda Manha` | float | Preço unitário de venda (R$) |
| `PU Base Manha` | float | Preço unitário base (R$) |

### Volume da base
- **169.478 registros** | período 2004-12-31 a 2026-04-02
- **8 famílias**: Selic, Prefixado, Prefixado c/ Juros, IPCA+, IPCA+ c/ Juros, IGPM+, Educa+, Renda+
- **60 títulos** no snapshot mais recente

### Variáveis derivadas (criadas pelo sistema)

| Variável | Cálculo |
|---|---|
| `dias_ate_vencimento` | `data_vencimento - data_base` em dias |
| `anos_ate_vencimento` | `dias_ate_vencimento / 365.25` |
| `spread_compra_venda` | `abs(pu_compra - pu_venda) / pu_base` |
| `familia_normalizada` | Enum padronizado da família |
| `bucket_prazo` | Curto (≤2a), Intermediário (2-5a), Longo (5-15a), Ultralongo (>15a) |
| `flag_cupom` | True se tem juros semestrais |
| `flag_indexado_inflacao` | True se IPCA+ ou IGPM+ |
| `flag_pos_fixado` | True se Selic |
| `flag_produto_planejamento` | True se Educa+ ou Renda+ |

---

## Framework Analítico: 3 Fórmulas de Score

### Fórmula A — Score Base (implementar primeiro)
```
Score_A = 0.40 × Carry_Norm + 0.40 × RV_Norm + 0.20 × Liquidez_Norm
```
- **Carry** = Taxa_Compra − Benchmark_Grupo
- **RV** = z-score da taxa dentro do grupo analítico
- **Liquidez** = 1 − min(1, Spread_Relativo / Limite_Spread_Grupo)

### Fórmula B — Score Ajustado por Risco
```
Score_B = 0.35 × Carry_Norm + 0.30 × RV_Norm + 0.15 × Liquidez_Norm + 0.20 × Risco_Norm
```
- **Risco_Norm** = 1 − Penalidade (duration + convexidade + DV01)

### Fórmula C — Score por Resíduo de Curva (fase madura)
```
Score_C = 0.30 × Carry_Norm + 0.40 × Residuo_Curva_Norm + 0.15 × Rolldown_Norm + 0.15 × Liquidez_Norm
```
- Requer curva teórica ajustada (Nelson-Siegel-Svensson)

---

## Segmentação: Regras de Comparabilidade

**NUNCA** comparar diretamente títulos de famílias diferentes. O ranking opera por **célula analítica**:

| Grupo Analítico | Benchmark de Carry | Observação |
|---|---|---|
| Tesouro Selic | Taxa Selic | Oportunidade = spread sobre Selic |
| Prefixado bullet | Curva nominal do bucket | Comparação por taxa nominal |
| Prefixado c/ cupom | Curva nominal ajustada por duration | Considerar fluxo |
| IPCA+ bullet | Curva real do bucket | Comparação em termos reais |
| IPCA+ c/ cupom | Curva real ajustada | Maior convexidade |
| Educa+ / Renda+ | Curva real + política própria | Tratamento específico |

---

## Pipeline de Ingestão: Regras Críticas

1. CSV bruto vai para `data/raw/` — **NUNCA alterar**
2. Nomenclatura: `{fonte}_{conjunto}_{data_ref}_{data_ingestao}_{versao}.csv`
3. Todo arquivo gera hash SHA-256 e registro em `data/audit/`
4. Validações obrigatórias ANTES de publicar:
   - Leitura OK, schema OK, tipagem OK
   - `data_vencimento > data_base`
   - Família reconhecida no dicionário
   - Volume compatível com histórico
5. Se validação falhar → **quarentena**, mantém última versão válida
6. Dashboard só consome de `data/outputs/` (camada publicada)

---

## Convenções de Código

### Python
- **Formatação:** Black + isort
- **Linting:** Ruff
- **Tipos:** Type hints em todas as funções públicas
- **Docstrings:** Google style
- **Encoding numérico:** Ponto decimal (nunca vírgula)
- **Datas:** `datetime.date` ou `pd.Timestamp`, formato ISO
- **Nomes de variáveis:** snake_case, português para domínio, inglês para técnico

### Git
- Branch principal: `main`
- Commits em português, formato: `tipo: descrição curta`
  - `feat:` nova funcionalidade
  - `fix:` correção
  - `docs:` documentação
  - `refactor:` refatoração
  - `test:` testes
  - `data:` mudança em dados ou schema
- Todo commit deve ter entrada correspondente no `CHANGELOG.md` com data, categoria (`Adicionado` / `Corrigido` / `Alterado`) e descrição clara da mudança.

### Logs
- Toda operação de ingestão gera log com: horário, duração, status, hash
- Toda falha gera registro em `data/audit/incidentes/`
- Dashboard exibe: data última atualização, versão da carga, status

---

## Prioridade de Implementação

### Fase 1 — Fundação (AGORA)
- [x] Estrutura de pastas e repositório
- [ ] `src/ingestao/validacao.py` — ler e validar CSV
- [ ] `src/transformacao/padronizacao.py` — normalizar schema
- [ ] `src/transformacao/enriquecimento.py` — variáveis derivadas
- [ ] `src/utils/config.py` + `constants.py`
- [ ] Testes básicos

### Fase 2 — Analytics
- [ ] `src/analytics/metricas.py` — carry, spread, z-score
- [ ] `src/analytics/score.py` — Fórmula A
- [ ] `src/analytics/ranking.py` — ranking por célula

### Fase 3 — Dashboard
- [ ] `src/dashboard/app.py` — interface Dash/Plotly
- [ ] Visão por família, ranking, série temporal
- [ ] Metadados de auditoria visíveis

### Fase 4 — Maturidade
- [ ] Fórmulas B e C
- [ ] Curva Nelson-Siegel-Svensson
- [ ] Pipeline automático com agendamento
- [ ] Alertas e monitoramento

---

## Referências Institucionais

| Fonte | URL | Uso |
|---|---|---|
| Tesouro Transparente (CKAN) | https://www.tesourotransparente.gov.br/ckan/organization/codip | Fonte primária de CSV |
| Tesouro Direto — Histórico | https://www.tesourodireto.com.br/produtos/dados-sobre-titulos/historico-de-precos-e-taxas | Auditoria e conferência |
| ANBIMA — Precificação | https://www.anbima.com.br/data/files/A0/02/CC/70/8FEFC8104606BDC8B82BA2A8/Metodologias%20ANBIMA%20de%20Precificacao%20Titulos%20Publicos.pdf | Referência metodológica |
| V-Lab NYU — Fixed Income | https://vlab.stern.nyu.edu/docs/fixedIncome | Fundamentos teóricos |
