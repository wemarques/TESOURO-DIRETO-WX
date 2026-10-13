# Changelog — Tesouro Direto WX

Todas as alterações relevantes do projeto são documentadas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

## [2026-10-13] — Metodologia v1.1.0 (marcação a mercado, Fase 1)

### Adicionado
- `src/analytics/calendario.py`: calendário ANBIMA por regra (feriados fixos, móveis pela Páscoa e 20/11 desde 2024) e contagem de dias úteis
- `src/analytics/duration.py`: fluxos de caixa por família, duration de Macaulay e modificada, convexidade, variação exata do PU para ±1 p.p., VNA implícito, inflação implícita (Fisher) e decomposição do retorno em efeito-taxa × carrego/indexação
- Colunas `duration_macaulay`, `duration_modificada`, `convexidade`, `var_pct_taxa_menos_1pp` e `var_pct_taxa_mais_1pp` na base analítica e no ranking
- `tests/test_duration.py`: âncoras do vídeo de marcação a mercado, PUs publicados no centavo, VNA implícito comum a todos os títulos IPCA e backtest do Renda+ 2065 (23/01/2025 → 10/07/2025)

- Ranking (Fase 2): colunas Duration, Duration mod., Convexidade, Δ PU se taxa −1pp / +1pp e Inflação implícita, com tooltips; ordenação por duration e por "ganho se taxa cair 1 p.p."; coluna Título fixa na rolagem horizontal
- Inflação implícita (Fisher) dos títulos IPCA contra a curva prefixada interpolada na mesma duration — só dentro do alcance da curva (sem extrapolar)
- `src/utils/nomes.py`: nomes curtos no padrão do Tesouro ("Renda+ 2065", "IPCA+ Juros 2060") no ranking e no gráfico

- `/titulo` (Fase 5): simulador de marcação a mercado — Δ taxa (−2 a +2 p.p.), horizonte e indexador projetado → PU de venda, retorno bruto, efeito-taxa, IR regressivo, IOF, custódia e retorno líquido; matriz Δ taxa × horizonte; aviso de degrau de IR quando faltam ≤ 30 dias
- `src/analytics/simulador.py`: simulação de compra hoje e venda ao Tesouro (taxa de venda, liquidação D+0), com cupons/parcelas recebidos e VNA projetado
- `/titulo`: "Efeito no preço" vira leitura dupla — quem já tinha o título (retorno em 12 meses separado em marcação e carrego, com cupons/parcelas recebidos) × quem entra hoje (quanto paga a mais ou a menos pela variação da taxa)

- Contexto macro (Fase 4): `src/ingestao/macro.py` + `scripts/rodar_macro.py` coletam Selic meta (SGS 432), IPCA 12 meses (SGS 13522) e Focus (IPCA 12 meses e Selic no fim do ano seguinte, API Olinda) em `data/outputs/macro.json`. Passo novo no workflow de ingestão, sem bloquear os dados do Tesouro se o BCB falhar; cada fonte que falha mantém o valor anterior
- `/titulo`: painel "Condições para a tese de queda de taxa" (curva prefixada em queda em 30 e 90 dias, Focus esperando Selic menor, taxa do título no percentil ≥ 80 dos últimos 24 meses), descritivo e sem veredito
- Simulador usa o IPCA esperado pelo Focus e a Selic meta do BCB como padrão

- Score D (marcação a mercado) no seletor do ranking: duration 45% + percentil da taxa em 24 meses 30% + resíduo da curva 15% + liquidez 10%, normalizado no grupo amplo (prefixados entre si; títulos de inflação entre si — exceção documentada à regra de comparabilidade). Sem Score D para o Tesouro Selic. Aviso de contexto ao selecioná-lo
- Coluna "Margem vs CDI 12m": quantos p.p. a taxa pode subir em 12 meses antes de render menos que o CDI esperado (média Selic atual × Focus, du/252); negativo = precisa cair para empatar
- Guia: Score D, duration e convexidade, margem vs CDI, inflação implícita e "faca de dois gumes" com o caso Renda+ 2065
- Workflow: coleta macro passa a rodar antes do analytics (alimenta Score D e margem)

### Corrigido
- `IPCA_ATUAL` estava em 3,81%; atualizado para 4,58% (IPCA 12 meses até 09/2026, SGS 13522). Adicionado `SELIC_META_REF` = 13,75% (SGS 432)
- Score B penalizava prazo e não duration: o Renda+/Educa+ era medido pela última parcela (ex.: 58 anos no Renda+ 2065, contra ~46 de duration real) e o Tesouro Selic recebia penalidade de juros que não tem. A penalidade passa a usar `duration_risco` (duration modificada; zero no Selic)

### Alterado
- Versão da metodologia: v1.0.0 → v1.1.0

### Corrigido
- "Melhor Título do Dia" sugeria títulos fora de venda (ex.: Tesouro Prefixado 2027, que só aceita resgate). CKAN e BRAPI publicam taxa de compra para todos os títulos, sem indicar disponibilidade
- Objetivo "Médio prazo (2-5 anos)" aceitava títulos do bucket curto (ex.: vencimento em 3 meses). Cada objetivo passa a ter prazo mínimo (`prazo_min_anos`), respeitado também quando a cascata expande buckets

### Adicionado
- `config/titulos_ofertados.csv`: lista oficial de títulos à venda (download "Baixar Lista" do Tesouro Direto, aba Investir)
- `src/utils/ofertados.py`: leitura da lista e coluna `disponivel_compra`, casando por tipo + vencimento (no Renda+/Educa+ o ano do nome não é o vencimento)
- Coluna "À venda" no ranking e marcação "(só resgate)" no seletor de título individual
- Testes `tests/test_ofertados.py`

## [2026-05-21]

### Corrigido
- Summary cards do ranking comparavam títulos de famílias diferentes (violava regra de comparabilidade). Cards passam a ser dinâmicos por família; em "Todas as famílias" exibem orientação em vez de "melhor score global"
- Dashboard não refletia parquets atualizados pelo cron sem reiniciar o processo

### Adicionado
- `src/dashboard/dados.py`: `EstadoDados`, recarga periódica de `data/outputs/`, `build_summary_stats()` por família
- Aviso legal no layout global e na página `/calculadora` (não constitui recomendação de investimento)
- Status bar com versão da metodologia (`v1.0.0`) e horário da carga em memória
- Variável `DASH_RELOAD_INTERVAL_MS` (padrão 5 min) documentada em `.env.example` e `docs/deploy-railway.md`
- `docs/checklist-pos-auditoria.md` com backlog P0/P1/P2 da auditoria
- Testes `tests/test_dashboard_dados.py`

### Alterado
- Calculadora: badge "Sugestão analítica do dia" em vez de "Recomendação do dia"
- `app.py` simplificado: boot via `ensure_data_exists()` + estado mutável compartilhado com callbacks

## [2026-04-09]

### Corrigido
- Dropdowns com fundo branco no mobile tornavam o texto invisível. Reforçados overrides em `src/dashboard/assets/style.css`:
  - `color-scheme: dark` global em `html`
  - Seletores nativos `input`, `select`, `textarea`, `button` forçados para o tema dark com `!important`
  - Cobertura ampla de seletores Dash: `.Select`, `.Select-control`, `.Select-menu-outer`, `.VirtualizedSelectOption`, `.dash-dropdown` (todos os estados: focado/aberto/hover/selecionado)
  - Media query `@media (max-width: 768px)` com reforço adicional para garantir fundo `#1A2736`
  - Fix de autofill do Chrome (webkit) para não virar branco

### Alterado
- **Redesign completo do dashboard** com tema "Financial Intelligence" (dark editorial inspirado em Bloomberg Terminal):
  - Novo `src/dashboard/assets/style.css` (~900 linhas) com design system completo: paleta dark (#0F1923/#1A2736), tipografia DM Sans + JetBrains Mono via Google Fonts, CSS variables, gradientes, transições, focus rings WCAG AA
  - Novo `src/dashboard/plotly_theme.py` com template `tdwx_dark` registrado como padrão e mapa de cores por família (`CORES_FAMILIA`)
  - Navbar customizada com logo "TD" + brand + 5 links + hamburger mobile (toggle via callback `toggle_menu_mobile`)
  - Status bar fina (substitui `metadados_card`) com bolinha pulsante verde/amarela/vermelha por frescor de ingestão
  - Página `/` (Ranking): page header, 4 summary cards (Melhor Score / Maior Taxa / Melhor Liquidez / Total), gráfico de barras com cores por família, tabela com hover dark
  - Página `/calculadora`: 3 question cards com ícones (🎯 📊 💰), result hero com badge "Recomendação do dia", taxa em destaque, fallback note estilizada
  - Página `/titulo`: grid 2 colunas (info card + chart), `tdwx-stats-grid` com 6 stat cards, card "Comparação 12 meses" com efeito no preço (🛒 / ⚠️)
  - Página `/series`: filtros + curva NSS com cores accent
  - Página `/guia`: accordion dark com `--bs-accordion-bg` overrides
  - Todos os charts plotly migrados de `plotly_white` para `tdwx_dark`
  - Layout responsivo: grid 12 col desktop → empilhado mobile, breakpoints 600px/768px/1024px/1200px
  - Skip-to-content link, `aria-label` no hamburger, `<main>` semântico

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
- `railway.toml`: `healthcheckTimeout` aumentado de 300 para 600 segundos para acomodar o pipeline inicial mais longo no primeiro deploy
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
