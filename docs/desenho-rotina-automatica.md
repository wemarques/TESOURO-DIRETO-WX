# Desenho Operacional da Rotina Automática de Ingestão por CSV

**Projeto:** Identificação de Oportunidades em Títulos do Tesouro Direto Brasileiro  
**Autor:** Manus AI  
**Data:** 2026-04-06

## 1. Finalidade

Este documento descreve o **desenho operacional da rotina automática** para capturar arquivos CSV oficiais, validar a integridade dos dados, atualizar a base analítica do projeto e refletir as alterações no **dashboard** e nos **relatórios derivados**. O objetivo é estabelecer uma arquitetura de operação clara, auditável e escalável, sem ainda implementar código ou infraestrutura de produção.

A lógica central da rotina é simples: **detectar novo arquivo oficial, validar a carga, transformar os dados, recalcular métricas, atualizar produtos analíticos e registrar auditoria**. O uso de CSV como fonte primária é compatível com o portal oficial do Tesouro Transparente, que disponibiliza o conjunto “Taxas dos Títulos Ofertados pelo Tesouro Direto” em formato CSV [1], bem como com a página do Tesouro Direto dedicada ao histórico de preços e taxas [2].

## 2. Objetivo operacional da rotina

A rotina automática deve garantir que o projeto opere com o dado oficial mais recente disponível, sem depender de intervenção manual em todas as etapas. Entretanto, a automação não deve significar publicação cega. O princípio operacional recomendado é o seguinte:

> **baixar, validar, versionar, processar, recalcular, publicar e auditar**.

Isso significa que o dashboard e os relatórios somente devem ser atualizados quando a nova carga tiver sido aprovada pelas regras mínimas de integridade e consistência.

## 3. Visão geral do fluxo operacional

| Etapa | Nome do módulo | Função principal | Saída |
|---|---|---|---|
| 1 | Monitoramento de fonte | Verificar se existe novo CSV oficial | Evento de nova carga |
| 2 | Coleta | Baixar o arquivo mais recente | Arquivo bruto em `raw/` |
| 3 | Registro de ingestão | Gerar metadados, hash e inventário | Log de carga |
| 4 | Validação inicial | Verificar arquivo, schema e integridade semântica | Status de aprovação ou quarentena |
| 5 | Padronização | Normalizar colunas, tipos, datas e números | Base padronizada |
| 6 | Enriquecimento | Criar variáveis derivadas, buckets, flags e chaves | Base enriquecida |
| 7 | Processamento analítico | Recalcular curvas, métricas, scores e rankings | Base analítica atualizada |
| 8 | Publicação | Atualizar dashboard, tabelas e relatórios | Produtos atualizados |
| 9 | Auditoria | Registrar sucesso, falha, exceções e versão | Log operacional final |

## 4. Arquitetura funcional da rotina

A rotina deve ser organizada em módulos independentes, porém encadeados. Isso reduz risco operacional e facilita manutenção futura.

| Módulo | Responsabilidade | Regras-chave |
|---|---|---|
| `monitor_source` | Verificar disponibilidade de novo arquivo na fonte oficial | Não baixa novamente arquivo idêntico |
| `download_csv` | Efetuar captura do CSV oficial | Deve preservar evidência de origem |
| `register_ingestion` | Registrar metadados da carga | Hash, data, nome, origem, linhas e colunas |
| `validate_csv` | Executar checagens obrigatórias | Pode aprovar, alertar ou bloquear |
| `standardize_data` | Padronizar schema e tipos | Nunca altera o bruto |
| `enrich_data` | Criar variáveis auxiliares e flags | Suporta camada analítica |
| `rebuild_analytics` | Recalcular métricas, curvas e scores | Usa apenas dados aprovados |
| `publish_dashboard` | Atualizar dataset consumido pelo dashboard | Só publica se validação final for aprovada |
| `publish_reports` | Atualizar relatórios tabulares e executivos | Segue versão da carga validada |
| `audit_and_notify` | Registrar execução e emitir status | Gera trilha de auditoria |

## 5. Fluxo lógico de decisão

A rotina não deve tratar toda nova coleta como publicação automática. Deve existir um mecanismo decisório orientado por regras.

| Situação encontrada | Ação operacional |
|---|---|
| Não existe novo arquivo | Encerrar execução com log informativo |
| Existe novo arquivo e hash é inédito | Prosseguir para validação |
| Existe novo arquivo, mas hash já conhecido | Encerrar execução sem reprocessamento |
| Arquivo novo com falha crítica | Enviar para quarentena e não publicar |
| Arquivo novo com alerta tolerável | Prosseguir com flag e registrar exceção |
| Arquivo aprovado | Reprocessar analytics e publicar |
| Arquivo aprovado, mas analytics falham | Manter versão anterior em produção e registrar incidente |

Esse desenho é importante para impedir que uma anomalia de ingestão corrompa o dashboard ou os relatórios.

## 6. Gatilhos da rotina

O projeto pode operar com três tipos de gatilho. A escolha depende do grau de automação desejado e da estabilidade da fonte.

| Tipo de gatilho | Descrição | Recomendação |
|---|---|---|
| Agendado por horário | Verificação automática em horário fixo | Recomendado para operação diária |
| Agendado por intervalo | Verificação a cada número fixo de horas | Útil em fase de testes |
| Execução manual assistida | Disparo pelo operador quando desejar | Adequado no início da operação |

Para o contexto do Tesouro Direto, a recomendação inicial é **execução automática diária em dias úteis**, com janela posterior ao horário típico de atualização da fonte. Se a rotina for implantada em ambiente mais simples, pode começar com execução manual supervisionada e migrar para agendamento quando a política de ingestão estiver estabilizada.

## 7. Frequência operacional recomendada

| Frequência | Objetivo | Observação |
|---|---|---|
| Diária em dias úteis | Verificar novo CSV e atualizar a base | Padrão preferencial |
| Semanal | Revisar estabilidade da rotina e analisar alertas | Controle operacional |
| Mensal | Revisar schema, regras de validação e confiabilidade da fonte | Governança |
| Extraordinária | Rodar fora da agenda em caso de revisão retroativa ou mudança da fonte | Tratamento de exceção |

## 8. Camadas de dados da rotina

A rotina automática deve respeitar a separação entre camadas para que qualquer erro possa ser rastreado e revertido.

| Camada | Conteúdo | Uso na rotina |
|---|---|---|
| `raw/` | CSV bruto oficial | Evidência primária da carga |
| `interim/padronizado/` | Dados limpos e tipados | Base intermediária controlada |
| `interim/enriquecido/` | Dados com prazo, buckets, flags e chaves | Entrada para analytics |
| `processed/` | Métricas, curvas, scores e rankings | Consumo analítico |
| `outputs/` | Tabelas publicáveis, insumos do dashboard e relatórios | Camada de entrega |
| `audit/` | Logs, inventários, hashes e incidentes | Governança e rastreabilidade |

## 9. Validações obrigatórias antes da publicação

O dashboard e os relatórios não devem ser atualizados diretamente após o download. A rotina precisa conter um **gate de publicação**.

| Bloco de validação | Regra de aprovação |
|---|---|
| Leitura do arquivo | O CSV deve ser legível e íntegro |
| Schema | Colunas obrigatórias devem estar presentes |
| Tipagem | Datas, taxas e preços devem ser convertíveis |
| Coerência temporal | `data_vencimento` deve ser posterior à `data_base` |
| Coerência categórica | Família do título deve ser reconhecida |
| Volume esperado | Número de linhas não pode divergir materialmente do padrão sem justificativa |
| Consistência analítica | Métricas calculadas não podem produzir resultados estruturalmente inválidos |
| Integridade de saída | Arquivos finais do dashboard e dos relatórios devem ser gerados sem erro |

Se qualquer uma das validações críticas falhar, a rotina deve encerrar a publicação e preservar a última versão válida do dashboard.

## 10. Módulo de atualização do dashboard

A atualização do dashboard deve consumir **somente uma camada publicada e homologada**, nunca a base intermediária diretamente. Isso evita exposição de dados parcialmente processados.

| Etapa do módulo | Função |
|---|---|
| Receber dataset publicado | Consumir apenas saída aprovada da camada `outputs/` |
| Atualizar tabelas e séries | Substituir datasets de exibição |
| Atualizar metadados de exibição | Registrar data da última atualização, versão e status |
| Validar consistência visual | Confirmar presença de campos essenciais |
| Publicar nova versão | Liberar exibição somente após integridade confirmada |

A recomendação é que o dashboard exiba, no mínimo, **data da última atualização**, **data de referência da carga**, **status da rotina** e **identificador da versão publicada**.

## 11. Módulo de atualização dos relatórios

Os relatórios devem ser tratados como produtos derivados da mesma camada publicada do dashboard. Isso garante coerência entre visão operacional e visão documental.

| Tipo de relatório | Atualização esperada |
|---|---|
| Relatório executivo resumido | Atualização automática após carga validada |
| Relatório analítico de monitoramento | Atualização automática ou semiautomática |
| Relatório metodológico | Não deve ser atualizado automaticamente a cada carga |
| Relatório de incidentes operacionais | Atualização a cada falha relevante |

A rotina deve distinguir entre relatórios **recorrentes de dados** e relatórios **metodológicos**. Apenas os primeiros devem ser parte da cadeia automática.

## 12. Estratégia de fallback e continuidade

A operação automática precisa ser resiliente. Se uma nova carga falhar, o sistema analítico não deve ficar sem referência.

| Cenário de falha | Resposta recomendada |
|---|---|
| Falha no download | Manter última versão válida e registrar incidente |
| Falha na validação estrutural | Quarentenar carga e bloquear publicação |
| Falha na transformação | Manter última versão válida e registrar erro técnico |
| Falha no recálculo dos scores | Interromper publicação e preservar produção anterior |
| Falha no dashboard | Não substituir dataset publicado anterior |
| Falha no relatório | Publicar dashboard, mas registrar degradação parcial se permitido pela governança |

O princípio geral deve ser: **falhou a nova carga, permanece a última versão válida**.

## 13. Logs, auditoria e monitoramento

Toda execução da rotina deve produzir evidências suficientes para auditoria posterior.

| Registro | Conteúdo mínimo |
|---|---|
| Log de execução | horário de início, fim, duração e status |
| Log de coleta | URL, nome do arquivo, hash e tamanho |
| Log de validação | resultado de cada regra validada |
| Log de transformação | arquivos gerados e contagens de registros |
| Log de publicação | versão publicada, data de referência e artefatos atualizados |
| Log de incidente | tipo de falha, impacto e ação tomada |

Além dos logs, recomenda-se geração de um **painel operacional interno** com indicadores como taxa de sucesso da rotina, número de falhas por etapa, dias desde a última atualização válida e divergência de volume por carga.

## 14. Sequência operacional diária recomendada

| Ordem | Passo operacional | Resultado esperado |
|---|---|---|
| 1 | Verificar fonte oficial | Confirmação de disponibilidade |
| 2 | Comparar arquivo com histórico recente | Identificação de novidade real |
| 3 | Baixar CSV e registrar hash | Carga bruta controlada |
| 4 | Validar integridade do arquivo | Aprovação inicial |
| 5 | Validar schema e coerência mínima | Aprovação estrutural |
| 6 | Padronizar e enriquecer dados | Base analítica pronta |
| 7 | Recalcular curvas, métricas e scores | Resultado analítico atualizado |
| 8 | Gerar datasets do dashboard e relatórios | Saídas publicáveis |
| 9 | Publicar somente se tudo estiver válido | Atualização controlada |
| 10 | Registrar auditoria final | Fechamento da execução |

## 15. Critério de prontidão para automação completa

Antes de automatizar completamente a rotina, o projeto deve comprovar que quatro requisitos mínimos estão atendidos.

| Requisito | Condição de prontidão |
|---|---|
| Fonte estável | O portal permite captura recorrente consistente |
| Schema conhecido | O CSV possui colunas mínimas mapeadas |
| Regras de validação definidas | Existe política formal de ingestão e bloqueio |
| Saídas bem definidas | Dashboard e relatórios consomem datasets padronizados |

Sem esses quatro elementos, a automação pode ser tecnicamente possível, mas operacionalmente frágil.

## 16. Evolução recomendada da rotina

A implantação deve ocorrer em estágios, para reduzir risco de erro sistêmico.

| Estágio | Característica | Objetivo |
|---|---|---|
| Estágio 1 | Coleta e validação com supervisão humana | Testar confiabilidade da fonte |
| Estágio 2 | Reprocessamento automático com publicação manual | Validar analytics sem risco de publicação automática |
| Estágio 3 | Publicação automática condicionada a validação | Operação regular controlada |
| Estágio 4 | Monitoramento, alertas e revisão contínua | Maturidade operacional |

Esse modelo é consistente com a preferência por abordagem incremental e com a necessidade de validar antes de publicar em ambiente recorrente.

## 17. Conclusão operacional

O desenho operacional proposto demonstra que é plenamente viável automatizar o ciclo de atualização do projeto com base em arquivos CSV oficiais. A condição para isso não é a existência de API, mas sim a presença de uma **fonte estável**, uma **política formal de ingestão**, uma **camada de validação robusta** e uma **separação clara entre processamento e publicação**.

Em termos operacionais, a rotina ideal do projeto deve funcionar como um pipeline controlado, no qual cada etapa só avança se a etapa anterior tiver sido aprovada. Dessa forma, o dashboard e os relatórios passam a refletir a informação mais recente disponível sem abrir mão de qualidade, auditabilidade e governança.

## Referências

[1]: https://www.tesourotransparente.gov.br/ckan/organization/codip "Tesouro Transparente — Organização CODIP no CKAN"
[2]: https://www.tesourodireto.com.br/produtos/dados-sobre-titulos/historico-de-precos-e-taxas "Tesouro Direto — Histórico de Preços e Taxas"
[3]: https://www.anbima.com.br/data/files/A0/02/CC/70/8FEFC8104606BDC8B82BA2A8/Metodologias%20ANBIMA%20de%20Precificacao%20Titulos%20Publicos.pdf "ANBIMA — Metodologia de Precificação de Títulos Públicos Federais"
