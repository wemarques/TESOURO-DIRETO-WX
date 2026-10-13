# Dicionário de Dados — Tesouro Direto WX

**Versão:** 1.0  
**Data:** 2026-04-06

## 1. Base bruta (CSV oficial)

| # | Coluna original | Nome padronizado | Tipo | Obrigatória | Descrição |
|---|---|---|---|---|---|
| 1 | `Tipo Titulo` | `tipo_titulo` | string | Sim | Família do título |
| 2 | `Data Vencimento` | `data_vencimento` | date | Sim | Data de vencimento |
| 3 | `Data Base` | `data_base` | date | Sim | Data de referência da observação |
| 4 | `Taxa Compra Manha` | `taxa_compra_manha` | float | Sim | Taxa de compra (% a.a.) |
| 5 | `Taxa Venda Manha` | `taxa_venda_manha` | float | Sim | Taxa de venda (% a.a.) |
| 6 | `PU Compra Manha` | `pu_compra_manha` | float | Sim | Preço unitário de compra (R$) |
| 7 | `PU Venda Manha` | `pu_venda_manha` | float | Sim | Preço unitário de venda (R$) |
| 8 | `PU Base Manha` | `pu_base_manha` | float | Sim | Preço unitário base (R$) |

### Convenções de leitura do CSV
- Separador: `;` (ponto-e-vírgula)
- Decimal: `,` (vírgula) → converter para `.`
- Encoding: UTF-8 ou Latin-1
- Datas: formato `DD/MM/YYYY` → converter para `YYYY-MM-DD`

## 2. Variáveis derivadas (camada enriquecida)

| Variável | Tipo | Cálculo | Finalidade |
|---|---|---|---|
| `dias_ate_vencimento` | int | `(data_vencimento - data_base).days` | Prazo remanescente |
| `anos_ate_vencimento` | float | `dias_ate_vencimento / 365.25` | Prazo em anos |
| `spread_compra_venda` | float | `abs(pu_compra - pu_venda) / pu_base` | Proxy de liquidez |
| `familia_normalizada` | enum | Mapeamento padronizado | Segmentação |
| `bucket_prazo` | enum | Curto/Intermediário/Longo/Ultralongo | Segmentação por prazo |
| `flag_cupom` | bool | True se "Juros Semestrais" no nome | Estrutura de fluxo |
| `flag_indexado_inflacao` | bool | True se IPCA+ ou IGPM+ | Tipo de indexação |
| `flag_pos_fixado` | bool | True se Selic | Tipo de indexação |
| `flag_produto_planejamento` | bool | True se Educa+ ou Renda+ | Produto temático |
| `chave_titulo` | string | `{tipo_titulo}_{data_vencimento}` | Identificador único do título |

### Métricas de risco de taxa (v1.1.0 — `src/analytics/duration.py`)

Calculadas sobre o fluxo de caixa de cada título, em dias úteis/252 (calendário ANBIMA) e liquidação D+1 (a mesma do PU de compra). Os PUs de Prefixado e Prefixado com Juros reproduzem os publicados pelo Tesouro no centavo; nos títulos IPCA o VNA implícito coincide entre todos os títulos do mesmo dia.

| Variável | Tipo | Cálculo | Finalidade |
|---|---|---|---|
| `duration_macaulay` | float | Σ tₖ·VPₖ / Σ VPₖ (anos) | Prazo médio ponderado dos fluxos |
| `duration_modificada` | float | Macaulay / (1 + i) | Variação % do PU por 1 p.p. de taxa (1ª ordem) |
| `convexidade` | float | Σ tₖ(tₖ+1)·VPₖ / [PU·(1+i)²] | Correção de 2ª ordem: ΔPU/PU ≈ −MD·Δi + ½·C·Δi² |
| `duration_risco` | float | `duration_modificada`; **0 no Tesouro Selic** | Penalidade do Score B (Selic não tem risco de juros) |
| `var_pct_taxa_menos_1pp` | float | Reprecificação exata com taxa −1 p.p. (NaN no Selic) | Ganho de marcação a mercado |
| `var_pct_taxa_mais_1pp` | float | Reprecificação exata com taxa +1 p.p. (NaN no Selic) | Perda de marcação a mercado |

Fluxos por família: Prefixado = 1000 no vencimento; Prefixado c/ Juros = cupom 48,80885 em 01/01 e 01/07; IPCA+ = 1 VNA no vencimento; IPCA+ c/ Juros = cupom (1,06^0,5−1) semestral; IGPM+ c/ Juros = cupom (1,12^0,5−1); Renda+ = 240 parcelas mensais de VNA/240 terminando no vencimento; Educa+ = 60 parcelas de VNA/60. **No Renda+ e no Educa+ `data_vencimento` é a última parcela** (o "Renda+ 2065" vence em 15/12/2084).

## 3. Famílias de títulos reconhecidas

| Família | Código interno | Indexador | Cupom | Grupo analítico |
|---|---|---|---|---|
| Tesouro Selic | `SELIC` | Selic | Não | Pós-fixado |
| Tesouro Prefixado | `PRE` | Nenhum (nominal) | Não | Nominal bullet |
| Tesouro Prefixado com Juros Semestrais | `PRE_JS` | Nenhum (nominal) | Sim | Nominal cupom |
| Tesouro IPCA+ | `IPCA` | IPCA | Não | Real bullet |
| Tesouro IPCA+ com Juros Semestrais | `IPCA_JS` | IPCA | Sim | Real cupom |
| Tesouro IGPM+ com Juros Semestrais | `IGPM_JS` | IGP-M | Sim | Real cupom (legado) |
| Tesouro Educa+ | `EDUCA` | IPCA | Programado | Planejamento |
| Tesouro Renda+ Aposentadoria Extra | `RENDA` | IPCA | Programado | Planejamento |

## 4. Buckets de prazo

| Bucket | Faixa (anos) | Código |
|---|---|---|
| Curto | ≤ 2 | `CURTO` |
| Intermediário | > 2 e ≤ 5 | `INTER` |
| Longo | > 5 e ≤ 15 | `LONGO` |
| Ultralongo | > 15 | `ULTRA` |

## 5. Validações obrigatórias

| Regra | Condição | Ação se falhar |
|---|---|---|
| Schema mínimo | 8 colunas obrigatórias presentes | Bloquear |
| Tipo numérico | Taxas e PU convertíveis para float | Flag |
| Coerência temporal | `data_vencimento > data_base` | Descartar linha |
| Família válida | `tipo_titulo` ∈ famílias reconhecidas | Flag "não mapeado" |
| Sem missing crítico | Nenhum NaN nas colunas obrigatórias | Bloquear linha |
| Volume plausível | Linhas do dia ± 30% da média recente | Alerta |
