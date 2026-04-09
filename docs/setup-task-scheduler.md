# Configurar Task Scheduler do Windows

Este guia mostra como configurar o Windows Task Scheduler para executar
automaticamente o pipeline de atualização do **Tesouro Direto WX** em dias
úteis às 20:00.

## Pré-requisitos

- Projeto instalado em `C:\TESOURO-DIRETO-WX`
- Ambiente virtual criado em `.venv`
- Dependências instaladas (`pip install -e ".[dev]"`)
- Arquivo `scripts\task_scheduler_setup.bat` presente

## Passo a passo

### 1. Abrir o Task Scheduler

- Pressione `Win + R`
- Digite `taskschd.msc` e pressione Enter
- Ou: Menu Iniciar -> "Agendador de Tarefas"

### 2. Criar nova tarefa

No painel direito, clique em **Criar Tarefa...** (não use "Criar Tarefa Básica",
pois ela não tem todas as opções avançadas necessárias).

### 3. Aba "Geral"

| Campo | Valor |
|---|---|
| Nome | `TesouroDirectoWX-Atualizacao` |
| Descrição | `Atualizacao diaria do pipeline Tesouro Direto WX` |
| Conta de usuário | A sua conta atual (clique em "Alterar Usuário ou Grupo" se necessário) |

**Marcar as seguintes opções:**

- [x] **Executar estando o usuário conectado ou não**
- [x] **Não armazenar senha**. Apenas recursos locais serão acessados.
  *(se o Windows pedir senha, forneça a senha da conta atual)*
- [x] **Executar com privilégios mais altos**
- Configurar para: **Windows 10** (ou versão mais recente)

### 4. Aba "Disparadores"

Clique em **Novo...** e configure:

| Campo | Valor |
|---|---|
| Iniciar a tarefa | `Em um agendamento` |
| Configurações | `Semanalmente` |
| Iniciar | Hoje, às `20:00:00` |
| Repetir a cada | `1` semana(s) |
| Dias da semana | Marcar **Segunda**, **Terça**, **Quarta**, **Quinta**, **Sexta** |

**Configurações avançadas:**
- [x] Habilitado

Clique em **OK**.

### 5. Aba "Ações"

Clique em **Novo...** e configure:

| Campo | Valor |
|---|---|
| Ação | `Iniciar um programa` |
| Programa/script | `C:\TESOURO-DIRETO-WX\scripts\task_scheduler_setup.bat` |
| Adicionar argumentos | *(deixar vazio)* |
| Iniciar em | `C:\TESOURO-DIRETO-WX` |

Clique em **OK**.

### 6. Aba "Condições"

**Desmarcar:**

- [ ] **Iniciar a tarefa somente se o computador estiver ligado na tomada**
- [ ] **Parar se o computador passar a usar a energia da bateria**

Manter marcado (opcional, se quiser que a internet esteja disponível):
- [x] Iniciar somente se a seguinte conexão de rede estiver disponível: `Qualquer conexão`

### 7. Aba "Configurações"

**Marcar:**

- [x] **Permitir que a tarefa seja executada por solicitação**
- [x] **Executar a tarefa o mais rápido possível após um início agendado ser perdido**
- [x] **Se a tarefa falhar, reiniciar a cada:** `15 minutos`, **Tentar reiniciar até:** `3 vezes`
- [x] **Interromper a tarefa se ela for executada por mais de:** `1 hora`

**Desmarcar:**

- [ ] **Se a tarefa em execução não for concluída quando solicitado, forçar a parada**
  *(deixar marcado para evitar travamentos eternos é OK também)*

### 8. Salvar

Clique em **OK**. Se solicitado, digite a senha da sua conta Windows.

## Verificar funcionamento

### Executar manualmente

No Task Scheduler, localize **TesouroDirectoWX-Atualizacao** na biblioteca,
clique com o botão direito e selecione **Executar**.

### Verificar log

Abra o arquivo `C:\TESOURO-DIRETO-WX\data\audit\task_scheduler.log` para
ver o resultado da execução.

Você também pode verificar:

- `data\audit\execucoes_agendadas.log` -- log do próprio script Python
- `data\audit\catalogo_ingestoes.json` -- registro da ingestão
- `data\audit\ultimo_hash.json` -- hash da última base baixada

### Verificar via linha de comando

```cmd
schtasks /Query /TN "TesouroDirectoWX-Atualizacao" /V /FO LIST
```

Para executar a tarefa imediatamente:

```cmd
schtasks /Run /TN "TesouroDirectoWX-Atualizacao"
```

Para desabilitar temporariamente:

```cmd
schtasks /Change /TN "TesouroDirectoWX-Atualizacao" /DISABLE
```

Para reabilitar:

```cmd
schtasks /Change /TN "TesouroDirectoWX-Atualizacao" /ENABLE
```

Para remover de vez:

```cmd
schtasks /Delete /TN "TesouroDirectoWX-Atualizacao" /F
```

## Comportamento esperado

- **Dias úteis às 20:00:** o pipeline executa automaticamente
- **Finais de semana e feriados:** o próprio script Python detecta e pula a execução
- **Já rodou hoje com sucesso:** a execução é pulada (proteção contra duplicidade)
- **PC desligado às 20:00:** a tarefa roda na próxima vez que o PC ligar (graças ao "Executar o mais rápido possível após um início agendado ser perdido")
- **Falha de rede:** o script tem 3 retries com backoff exponencial e fallback para URL direta

## Troubleshooting

### Tarefa não executa

1. Verifique se o usuário tem permissão para executar tarefas agendadas
2. Confira se o caminho do `.bat` está correto
3. Veja o histórico no Task Scheduler (aba "Histórico" da tarefa)
4. Confirme que o `.venv` existe em `C:\TESOURO-DIRETO-WX\.venv`

### Erro 0x1 (código de saída 1)

Indica que o script Python retornou erro. Verifique:

- `data\audit\task_scheduler.log` -- saída completa
- `data\audit\incidentes\` -- registros de falha
- Conexão com a internet
- Status do portal Tesouro Transparente

### Erro 0x2 (arquivo não encontrado)

O caminho do `.bat` está incorreto. Verifique se o arquivo
`C:\TESOURO-DIRETO-WX\scripts\task_scheduler_setup.bat` existe.

### Tarefa roda mas o dashboard não atualiza

O dashboard só lê os dados na inicialização. Após uma nova ingestão,
reinicie o app: `python -m src.dashboard.app`.
