# Deploy no Railway

Este guia descreve como publicar o **Tesouro Direto WX** no [Railway](https://railway.app),
um PaaS que detecta projetos Python automaticamente via Nixpacks.

## Arquivos do projeto

| Arquivo | Função |
|---|---|
| `Procfile` | Comando para iniciar o web service (`web: python -m src.dashboard.app`) |
| `runtime.txt` | Versão do Python (`python-3.11`) |
| `requirements.txt` | Dependências de produção (Railway usa por padrão) |
| `railway.toml` | Configuração específica do Railway: builder, healthcheck, restart policy |
| `.env.example` | Exemplo das variáveis de ambiente esperadas |

## Passo a passo

### 1. Criar conta

Acesse [railway.app](https://railway.app) e crie uma conta (pode logar com o GitHub).

### 2. Criar projeto

- No dashboard, clique em **New Project**
- Escolha **Deploy from GitHub repo**
- Autorize o Railway a acessar seu GitHub e selecione `wemarques/TESOURO-DIRETO-WX`
- Confirme o branch `main`

### 3. Configuração automática

Railway detecta automaticamente que é um projeto Python por causa do `requirements.txt`
e do `runtime.txt`. O `railway.toml` instrui o build via Nixpacks e define o
healthcheck na rota `/`.

### 4. Variáveis de ambiente

Vá em **Variables** e adicione:

| Variável | Valor | Descrição |
|---|---|---|
| `PORT` | (definida pelo Railway) | Porta interna do container |
| `HOST` | `0.0.0.0` | Bind em todas as interfaces |
| `DEBUG` | `false` | Desabilita modo debug do Dash em produção |
| `CRON_ENABLED` | `true` | Habilita o cron de atualização automática |

> **Nota:** o Railway define `PORT` automaticamente e injeta como variável de ambiente.
> O `app.py` lê esse valor com fallback para `8050` em desenvolvimento local.

### 5. Volume persistente para `data/`

Sem volume, o Railway recria o container a cada deploy e perde os CSVs e parquets
em `data/`. Para preservar:

- No serviço web, vá em **Settings** → **Volumes**
- Clique em **+ Add Volume**
- **Mount path:** `/app/data`
- **Size:** começar com 1 GB (suficiente; o CSV oficial tem ~14 MB)

Isso preserva todo o conteúdo de `data/` (raw, interim, processed, outputs, audit)
entre deploys e reinicializações.

### 6. Deploy automático

A cada push na branch `main`, o Railway dispara um novo deploy. Você pode
acompanhar em **Deployments**.

No primeiro boot, o `app.py` executa `_ensure_data_exists()` que:
1. Cria todos os subdiretórios em `data/`
2. Detecta que não há `ranking_atual.parquet`
3. Roda `scripts/rodar_ingestao.py` (baixa CSV oficial via API CKAN)
4. Roda `scripts/rodar_analytics.py` (calcula métricas, curvas e scores)

A partir do segundo deploy, com volume montado, os dados já estão lá.

### 7. Cron Job para atualização diária

Para manter os dados frescos sem precisar do Task Scheduler do Windows:

- No projeto Railway, clique em **+ New** → **Empty Service**
- Vá em **Settings** → **Service** e configure:
  - **Name:** `cron-atualizacao`
  - **Source:** mesmo repo do GitHub
- Em **Settings** → **Cron Schedule**, defina:
  - **Schedule:** `0 23 * * 1-5` (segunda a sexta às 23:00 UTC = 20:00 horário de Brasília)
  - **Command:** `python scripts/cron_atualizacao.py`
- Em **Variables**, adicione `CRON_ENABLED=true`
- Importante: o cron job precisa **montar o mesmo volume** que o web service em `/app/data`,
  caso contrário ele atualiza dados em um disco isolado e o dashboard não vê

### 8. Verificar funcionamento

Após o deploy, abra a URL pública gerada pelo Railway (algo como
`https://tesouro-direto-wx.up.railway.app`). Você deve ver:

- Dashboard carregando com a página de Ranking
- Badge **Ingestão: YYYY-MM-DD** no topo
- Páginas Series, Calculadora, Título Individual e Guia funcionais

Se algo falhar, verifique os logs em **Deployments** → última build → **View Logs**.

## Troubleshooting

### Build falhando por dependência

Garanta que o `requirements.txt` esteja sincronizado com o `pyproject.toml`. O
Railway usa `requirements.txt` por padrão.

### App roda mas exibe "Connection refused"

- Confirme que `HOST=0.0.0.0` está nas variáveis (não `127.0.0.1`)
- Confirme que o `app.run()` lê `PORT` de `os.environ`
- Veja o log para confirmar em qual porta o Dash está bindando

### Pipeline inicial trava no boot

- Verifique se a instância tem acesso à internet (Railway permite outbound HTTPS por padrão)
- Veja o log: o `_ensure_data_exists()` imprime cada etapa com prefixo `[boot]`
- Se o CKAN estiver fora, o download cai no fallback de URL direta (embutido em `download.py`)

### Cron não atualiza os dados que o web vê

Confirme que o cron service tem o **mesmo volume** montado em `/app/data` que o
web service. Sem isso, cada serviço escreve em seu próprio disco efêmero.

### Healthcheck falhando

O `railway.toml` define `healthcheckPath = "/"` com timeout de 300s. Se o
boot inicial demorar mais que isso (ex: pipeline grande na primeira vez),
aumente o timeout ou rode o pipeline manualmente antes via shell do Railway.
