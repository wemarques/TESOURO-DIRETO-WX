# Checklist pós-auditoria (devil's advocate)

Priorização das correções após revisão crítica do dashboard em produção
([tesouro-direto-wx-production.up.railway.app](https://tesouro-direto-wx-production.up.railway.app/)).

## P0 — Implementado

| Item | Problema | Solução |
|------|----------|---------|
| Summary cards globais | Comparavam Selic vs IPCA+ no topo do ranking | Cards dinâmicos por família; em "Todas" exibem hint + total |
| Linguagem de recomendação | "Recomendação do dia" sugeria assessoria | Badge "Sugestão analítica do dia" + subtítulo + aviso legal |
| Dados stale após cron | Parquets atualizados sem reiniciar o app | `dcc.Interval` + `EstadoDados.recarregar()` (padrão 5 min, env `DASH_RELOAD_INTERVAL_MS`) |
| Aviso legal | Ausência de disclaimer | `aviso_legal()` no layout global e na calculadora |

Arquivos principais: `src/dashboard/dados.py`, `src/dashboard/app.py`, `src/dashboard/layouts.py`, `src/dashboard/callbacks.py`.

## P1 — Parcial / próximos passos

| Item | Status | Notas |
|------|--------|-------|
| Versão metodologia na UI | Feito | Status bar exibe `config.versao_metodologia` e horário da carga em memória |
| `IPCA_ATUAL` hardcoded | Pendente | Expor fonte/data na UI ou buscar série automática |
| Score C para perfil "arrojado" | Pendente | Avisar quando `score_c` é NaN / curva não ajustada |
| Calculadora sem resultado vazio | Pendente | Hoje sempre há fallback nível 4 — considerar estado "sem match" |
| Headers de segurança (CSP, HSTS) | Pendente | Configurar no reverse proxy (Railway edge / CDN) |

## P2 — Backlog metodológico

| Item | Descrição |
|------|-----------|
| Backtest do ranking | Validar se score de ontem correlaciona com carry realizado |
| Otimizar `iterrows` | Vetorizar variação 12M em `dados.py` |
| Reduzir RAM | Carregar só snapshot + janela histórica no dashboard |
| Reload sob demanda | Botão "Atualizar dados" além do intervalo |

## Operação (Railway)

1. Cron e web service devem compartilhar volume em `/app/data`.
2. Variável opcional: `DASH_RELOAD_INTERVAL_MS=300000` (mínimo 60000).
3. Após deploy, confirmar status bar: data dos dados, ingestão, metodologia, memória.

## Referência

Auditoria original: sessão Cloud Agent maio/2026 (advogado do diabo sobre UX, metodologia e ops).
