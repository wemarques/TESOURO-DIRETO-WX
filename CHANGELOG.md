# Changelog — Tesouro Direto WX

Todas as alterações relevantes do projeto são documentadas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

## [2026-04-09]

### Adicionado
- Suporte a deploy no Railway: `Procfile`, `runtime.txt`, `requirements.txt`, `railway.toml`, `.env.example`
- `scripts/cron_atualizacao.py` para Railway Cron Job (lê `CRON_ENABLED`, executa pipeline ingestao+analytics, loga em stdout)
- `docs/deploy-railway.md` com guia passo a passo: criação do projeto, variáveis de ambiente, volume persistente, cron job, troubleshooting
- Função `_ensure_data_exists()` em `src/dashboard/app.py` que cria diretórios `data/` no boot e dispara `rodar_ingestao.py` + `rodar_analytics.py` no primeiro deploy
- `app.py` lê `PORT`, `HOST` e `DEBUG` de variáveis de ambiente para funcionar tanto local quanto em produção
- GitHub Action `.github/workflows/ci.yml` que roda pytest e ruff a cada push/pull-request na branch `main`. Usa `ubuntu-latest`, Python 3.11 e cache de pip
- Setup completo do Task Scheduler do Windows: `scripts/task_scheduler_setup.bat` (entry point para o agendador), `scripts/instalar_tarefa_windows.bat` e `scripts/desinstalar_tarefa_windows.bat` (helpers via `schtasks`), `docs/setup-task-scheduler.md` (guia passo a passo) (`67ac351`)
- Página `/calculadora` "Melhor Título do Dia" no dashboard com 3 perguntas (objetivo, perfil de risco, renda periódica), card de destaque do título recomendado e tabela de alternativas (`1f27c84`)
- Página `/guia` educativa com 5 seções em accordion: o que é Tesouro Direto, tipos de título, custos e tributação, métricas do dashboard, marcação a mercado (`1f27c84`)
- Tabela de ranking ganhou colunas `Variação 12M` (depois substituída por `Taxa 12M (pp)`) e `PU Compra (R$)` (`1f27c84`)
- Página de detalhamento do título individual ganhou cards com Min/Max 52 semanas, valorização 12M e do mês, IPCA atual e seletor de período (30d/6m/1a/5a/Máximo) (`1f27c84`)
- Constante `IPCA_ATUAL` em `src/utils/constants.py` (`1f27c84`)
- Card "Comparação 12 meses (taxa)" na página de título individual com taxa antiga, taxa hoje, variação em pp e ícone de efeito no preço (🛒 oportunidade / ⚠️ menos atrativo) (`5cd9c28`)
- Função `recomendar_titulo()` com cascata de 4 níveis de fallback que sempre retorna resultado (`7ef305d`)
- Função `build_calculadora_dataset()` que constrói dataset da calculadora a partir do snapshot completo do dia (60 títulos, incluindo SELIC) (`7ef305d`)
- Coluna "Amostra pequena" na tabela de ranking, com badge ✓ e estilo itálico/cinza para títulos cuja célula tem menos de 3 observações (`bb0a80c`)
- Flag `celula_pequena` em `src/analytics/ranking.py` para marcar (em vez de excluir) títulos de células pequenas (`bb0a80c`)

### Alterado
- `scripts/rodar_analytics.py` agora também publica `data/outputs/base_analitica.parquet` (consumido pelo dashboard), eliminando passo manual de cópia entre runs
- Imports reorganizados em `src/dashboard/app.py`, `src/ingestao/{download,monitor,registro}.py`, `src/utils/config.py`, `src/dashboard/layouts.py`, `src/analytics/score.py` e `src/dashboard/callbacks.py` para passar no `ruff check` (regras `I001` isort e `F401` unused-import)
- Quebras de linha em `src/ingestao/validacao.py` (assinatura `validar_estrutural`) e em chamadas `_stat_card`/`_info_row` em `src/dashboard/callbacks.py` para respeitar limite de 100 colunas

### Corrigido
- Detecção de `data_referencia` em `src/ingestao/download.py` usando `max()` de toda a coluna `data_base` via `csv.reader` em uma única passada, em vez de apenas primeira/última linha (`6ab2f37`)
- Substituição de em-dash (—) por hífen simples (-) nas mensagens de log de `agendar_atualizacao.py` e `registro.py` para evitar `UnicodeEncodeError` no console Windows (cp1252) (`8fa637b`)
- Coluna "Variação 12M" substituída por "Taxa 12M (pp)" com semântica neutra: pontos percentuais em vez de %, cores azul (subiu) / cinza (caiu) em vez de vermelho/verde, tooltip explicando relação inversa taxa/preço em renda fixa (`5cd9c28`)
- Calculadora "Melhor Título do Dia" não retorna mais "sem títulos" para nenhuma combinação. Implementado fallback em cascata e mudança para `df_calculadora` (60 títulos do snapshot completo) em vez de `df_ranking` (40 títulos filtrados) (`7ef305d`)
- Inconsistência entre ranking (40 títulos) e calculadora (60 títulos): agora ambos consomem o mesmo universo. Ranking mantém títulos de células pequenas com flag visual em vez de excluí-los. Tesouro Prefixado 2027 e Tesouro Selic agora aparecem em ambos (`bb0a80c`)

## [2026-04-07]

### Adicionado
- Scaffold inicial do projeto com documentação completa: `CLAUDE.md`, `README.md`, `pyproject.toml`, estrutura de pastas `src/`, `data/`, `docs/`, `tests/`, `scripts/`, `notebooks/`. Documentos metodológicos: `plano-de-trabalho.md`, `metodologia-operacional.md`, `politica-ingestao-csv.md`, `desenho-rotina-automatica.md`, `notas-pesquisa.md`, `dicionario-dados.md` (`5b2faa3`)
- Score B (ajustado por risco de duration) ativado no pipeline analytics, incluído no CSV de saída do ranking (`439c111`)
- Dashboard inicial com Dash/Plotly e dash-bootstrap-components: páginas Ranking, Séries Temporais e Título Individual; navbar; metadados de atualização; seletor de Score A vs Score B (`439c111`)
- Tooltips explicativos em todos os cabeçalhos da tabela de ranking, com texto dinâmico que muda conforme o score selecionado (`f5e7e78`)
- Coluna "Indexador" na tabela de ranking (Selic / Prefixado / IPCA / IGP-M) e linha "Indexador" no card de detalhamento do título individual (`7ed6002`)
- Score C com modelo Nelson-Siegel-Svensson em `src/analytics/curva.py`: ajuste por grupo analítico via `scipy.optimize.minimize`, taxa teórica, resíduo e rolldown de 6 meses. `calcular_score_c()` em `src/analytics/score.py`. Fallback automático para `score_a` quando curva não pode ser ajustada (< 4 títulos). Visualização interativa de curva NSS vs pontos observados na página de séries temporais (`3a42a67`)
- Pipeline automático de ingestão com API CKAN do Tesouro Transparente: `monitor.py` (descobre URL do CSV via API e compara hash SHA-256), `download.py` (retry com backoff exponencial 30s/120s/300s, rate limit 5s, fallback para URL direta, validação anti-HTML), `registro.py` (catálogo de ingestões e registro de incidentes em JSON). Pipeline `rodar_ingestao.py` refatorado com flags `--local` e `--forcar`. Agendador `scripts/agendar_atualizacao.py` para dias úteis às 20:00 com flag `--agora`. Dashboard exibe badge de ingestão com cor por frescor (`a4fab2b`)

### Corrigido
- `pyproject.toml` ajustado: `requires-python` de `>=3.12` para `>=3.11`, adicionada seção `[tool.setuptools.packages.find]` para resolver `import src`, adicionada dependência `pyarrow>=15.0` (`c7bee03`)
- Encoding do `subprocess.run` em `agendar_atualizacao.py` definido como UTF-8 com `errors="replace"` para evitar `UnicodeDecodeError` no Windows. Detecção de `data_referencia` em `download.py` usa `max(primeira, última linha)` em vez de só a última (`577d53f`)

## Convenções

- Cada entrada referencia o hash curto do commit entre parênteses
- Categorias seguem [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/): `Adicionado`, `Corrigido`, `Alterado`, `Removido`, `Depreciado`, `Segurança`
- Datas no formato `YYYY-MM-DD`
- Ordem cronológica reversa (mais recente primeiro)
