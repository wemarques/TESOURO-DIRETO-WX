# Política Operacional de Ingestão por CSV

**Projeto:** Identificação de Oportunidades em Títulos do Tesouro Direto Brasileiro  
**Autor:** Manus AI  
**Data:** 2026-04-06

## 1. Finalidade

Esta política estabelece as regras operacionais para a **ingestão de dados via arquivos CSV oficiais** no projeto de identificação de oportunidades em títulos do Tesouro Direto. O documento disciplina a coleta, o versionamento, a validação, o armazenamento, a rastreabilidade e a governança dos arquivos utilizados como base analítica do projeto.

A política parte de uma premissa simples: na ausência de uma API oficial claramente disponibilizada para o caso de uso do projeto, a ingestão por arquivos CSV publicados em fontes oficiais é um procedimento plenamente aceitável, desde que seja executado com controles formais de qualidade, integridade e auditoria. O portal do Tesouro Transparente disponibiliza o conjunto de dados **Taxas dos Títulos Ofertados pelo Tesouro Direto** em formato CSV [1], enquanto o Tesouro Direto mantém página oficial com histórico de preços e taxas por família de títulos [2]. Em complemento, as referências institucionais de precificação da ANBIMA reforçam a importância de consistência entre taxas, preços e controles de qualidade no tratamento de dados de títulos públicos [3].

## 2. Escopo

Esta política aplica-se a todo arquivo CSV incorporado ao projeto para fins de análise, consolidação histórica, cálculo de métricas, validação metodológica ou auditoria. O escopo inclui arquivos obtidos diretamente do portal Tesouro Transparente, arquivos históricos consolidados do Tesouro Direto e quaisquer arquivos auxiliares oficiais utilizados para enriquecimento analítico.

O documento cobre exclusivamente a política de ingestão por arquivos e não substitui a documentação metodológica do projeto, a política de segmentação dos títulos, os critérios de validação dos modelos nem as regras de governança de mudanças metodológicas. Seu papel é assegurar que a **camada de entrada de dados** opere de forma previsível, reprodutível e auditável.

## 3. Princípios operacionais

A ingestão por CSV deve obedecer a cinco princípios: **oficialidade da fonte**, **imutabilidade do dado bruto**, **versionamento explícito**, **validação obrigatória** e **rastreabilidade integral**. Em termos práticos, isso significa que o projeto não deverá consumir arquivos sem origem identificada, não deverá sobrescrever arquivos originais, não deverá processar bases sem registrar metadados de carga e não deverá liberar qualquer base analítica sem validação formal da estrutura mínima esperada.

> "As taxas e preços dos títulos ofertados pelo Tesouro Direto refletem o mercado secundário de títulos públicos federais." — **Tesouro Transparente / CKAN** [1]

Esses princípios são coerentes com o uso de dados oficiais para análise de títulos públicos e com práticas institucionais de tratamento de referências de preço, nas quais consistência interna, controle estatístico e governança de divulgação são elementos essenciais [3].

## 4. Fontes autorizadas

As fontes autorizadas para ingestão devem ser formalmente registradas no projeto. Nenhuma nova fonte deve ser incorporada sem avaliação documental prévia.

| Categoria | Fonte autorizada | Papel no projeto | Prioridade |
|---|---|---|---|
| Fonte primária | Tesouro Transparente / CKAN — conjunto “Taxas dos Títulos Ofertados pelo Tesouro Direto” | Base principal de ingestão recorrente | Alta |
| Fonte primária complementar | Tesouro Direto — Histórico de Preços e Taxas | Conferência institucional, recuperação histórica e auditoria | Alta |
| Fonte institucional auxiliar | Documentos metodológicos de precificação da ANBIMA | Referência para controles de consistência e interpretação analítica | Média |
| Fonte auxiliar futura | Arquivos oficiais adicionais do Tesouro Nacional ou Banco Central | Enriquecimento analítico e validação cruzada | Condicional |

Toda fonte autorizada deve possuir registro mínimo contendo URL de origem, nome do conjunto de dados, entidade publicadora, formato, frequência esperada de atualização e observações operacionais.

## 5. Política de coleta

A coleta dos arquivos CSV deverá seguir rotina controlada, com registro da data de obtenção, URL de origem, nome original do arquivo e responsável pela carga. A coleta pode ser manual ou semiautomatizada, desde que preserve os controles documentais exigidos por esta política.

A regra principal é que a coleta deve sempre buscar o **arquivo oficial mais recente disponível**, sem eliminar versões anteriores. Caso o portal publique revisões retroativas, a nova versão deve ser incorporada como uma nova evidência documental, nunca como substituição silenciosa do histórico já armazenado.

| Elemento de coleta | Regra operacional |
|---|---|
| Periodicidade | Preferencialmente diária em dias úteis, ou conforme disponibilidade da fonte |
| Origem | Sempre a partir de link oficial registrado |
| Nome original | Deve ser preservado em metadado, ainda que o arquivo receba nome padronizado internamente |
| Data de captura | Obrigatória |
| Responsável pela carga | Obrigatório em ambiente colaborativo |
| Evidência de origem | URL, tela de referência ou log de download |
| Coleta retroativa | Permitida, desde que identificada como carga histórica |

## 6. Política de nomenclatura e versionamento

Todo arquivo ingressado no projeto deve receber um nome padronizado que permita identificar a origem, o tipo de dado, a data de referência e a data de ingestão. A padronização tem o objetivo de facilitar busca, auditoria, reconciliação histórica e reprocessamento.

A convenção recomendada é a seguinte:

```text
{fonte}_{conjunto}_{data_referencia}_{data_ingestao}_{versao}.csv
```

O conceito de **data de referência** corresponde à data do dado de mercado, enquanto a **data de ingestão** corresponde ao dia em que o arquivo entrou no ambiente do projeto. A versão deve começar em `v001` e ser incrementada apenas quando houver nova obtenção de arquivo com a mesma data de referência e diferença material em relação à carga anterior.

| Campo do nome | Conteúdo esperado |
|---|---|
| `fonte` | Identificador curto da origem, como `tesouro_ckan` ou `tesouro_direto` |
| `conjunto` | Nome resumido do dataset, como `taxas_titulos_ofertados` |
| `data_referencia` | Data-base do conteúdo no padrão `YYYY-MM-DD` |
| `data_ingestao` | Data da captura no padrão `YYYY-MM-DD` |
| `versao` | Identificador incremental no padrão `vNNN` |

Além do nome padronizado, cada ingestão deve gerar um registro em catálogo contendo hash do arquivo, tamanho em bytes, quantidade de linhas, quantidade de colunas e observações relevantes.

## 7. Estrutura de armazenamento

A política de ingestão exige separação rígida entre dado bruto, dado padronizado e dado processado. Essa separação impede perda de rastreabilidade e protege o projeto contra sobrescritas acidentais.

| Diretório | Função | Regra |
|---|---|---|
| `data/raw/` | Armazenar o arquivo original ingerido | Imutável após carga |
| `data/interim/padronizado/` | Armazenar arquivo após renomeação de colunas, tipagem e limpeza mínima | Só pode derivar de `raw/` |
| `data/interim/enriquecido/` | Armazenar arquivo com variáveis derivadas e flags de qualidade | Só pode derivar de `padronizado/` |
| `data/processed/` | Armazenar base analítica consolidada | Uso analítico principal |
| `data/audit/` | Armazenar logs, hashes, inventário de cargas e snapshots | Uso de auditoria |

Nenhum arquivo em `data/raw/` pode ser alterado manualmente. Caso seja necessário corrigir uma carga, o procedimento correto é realizar nova ingestão, gerar novo identificador de versão e atualizar o catálogo de auditoria.

## 8. Metadados obrigatórios da ingestão

Toda carga deve produzir um registro mínimo de metadados. Sem esse registro, a ingestão será considerada incompleta.

| Campo | Obrigatoriedade | Descrição |
|---|---|---|
| `dataset_id` | Obrigatório | Identificador interno da ingestão |
| `fonte` | Obrigatório | Origem oficial do arquivo |
| `url_origem` | Obrigatório | Endereço da coleta |
| `nome_arquivo_original` | Obrigatório | Nome publicado pela fonte |
| `nome_arquivo_interno` | Obrigatório | Nome padronizado no projeto |
| `data_referencia` | Obrigatório | Data-base do dado |
| `data_ingestao` | Obrigatório | Data da captura |
| `hash_sha256` | Obrigatório | Integridade do arquivo |
| `tamanho_bytes` | Obrigatório | Tamanho do arquivo bruto |
| `linhas_brutas` | Obrigatório | Quantidade de registros brutos |
| `colunas_brutas` | Obrigatório | Quantidade de colunas brutas |
| `status_validacao` | Obrigatório | Situação da validação inicial |
| `observacoes` | Condicional | Notas sobre anomalias ou exceções |

## 9. Validação obrigatória do CSV

Nenhum CSV poderá seguir para a camada analítica sem passar por validação formal. A validação deve ser dividida em três níveis: **integridade do arquivo**, **integridade estrutural** e **integridade semântica**.

### 9.1. Integridade do arquivo

A integridade do arquivo verifica se o download foi concluído corretamente e se o conteúdo é legível.

| Verificação | Critério |
|---|---|
| Extensão | O arquivo deve estar em formato `.csv` ou ser convertido de forma controlada para CSV mantendo evidência da origem |
| Leitura | O arquivo deve ser legível sem erro fatal |
| Encoding | O encoding deve ser identificado e registrado |
| Separador | O delimitador deve ser detectado e registrado |
| Hash | O hash deve ser calculado e persistido |

### 9.2. Integridade estrutural

A integridade estrutural verifica se o CSV possui o esquema mínimo esperado pelo projeto.

| Verificação | Critério operacional | Ação em caso de falha |
|---|---|---|
| Cabeçalho | Colunas obrigatórias presentes | Bloquear processamento |
| Duplicidade de coluna | Não permitir nomes repetidos | Bloquear processamento |
| Ordem lógica | Recomendada, não mandatória | Reordenar na camada padronizada |
| Contagem de linhas | Deve ser compatível com histórico recente | Abrir alerta |
| Contagem de colunas | Deve coincidir com schema esperado ou versão homologada | Abrir alerta ou bloquear |

Para o dataset principal, a expectativa inicial é contemplar, no mínimo, as colunas equivalentes a tipo de título, data de vencimento, data-base, taxas de compra e venda e preços unitários de compra, venda e base.

### 9.3. Integridade semântica

A integridade semântica verifica se os valores fazem sentido para o contexto do projeto.

| Verificação | Critério operacional | Tratamento |
|---|---|---|
| Datas | `data_vencimento` deve ser posterior à `data_base` | Descartar linha inválida e registrar |
| Tipagem numérica | Taxas e PU devem ser convertíveis para número | Flag de inconsistência |
| Faixas plausíveis | Taxas e preços devem estar em faixa economicamente plausível para o grupo | Alerta para revisão |
| Valores faltantes | Não permitir ausência nas variáveis críticas | Bloquear uso analítico |
| Coerência de título | Família do título deve ser reconhecida pelo dicionário do projeto | Classificar como não mapeado |
| Coerência interna | Relações preço-taxa devem ser auditáveis | Sinalizar para inspeção |

A existência de filtros estatísticos no processo institucional de precificação de títulos públicos reforça a necessidade de excluir ou sinalizar observações que possam contaminar medidas centrais e rankings analíticos [3].

## 10. Padronização pós-ingestão

Após a validação inicial, o arquivo deverá passar por padronização controlada. Essa etapa não altera o arquivo bruto; ela gera uma nova camada derivada.

A padronização deverá incluir normalização de nomes de colunas, remoção de espaços supérfluos, conversão de datas, tratamento de separadores decimais, tipagem dos campos numéricos e criação de variáveis básicas de apoio, como prazo até vencimento em dias e anos.

| Transformação | Objetivo |
|---|---|
| Renomeação de colunas | Uniformizar o schema ao padrão do projeto |
| Padronização textual | Reduzir ambiguidade entre categorias |
| Conversão de datas | Permitir cálculo de maturidade e ordenação temporal |
| Conversão de números | Tornar taxas e PU utilizáveis analiticamente |
| Criação de chaves lógicas | Facilitar deduplicação e reconciliação |
| Criação de flags | Indicar inconsistências, interpolações e exceções |

## 11. Política de deduplicação e reconciliação

Quando forem identificadas múltiplas ocorrências equivalentes para a mesma combinação lógica de título, data-base e vencimento, deverá ser aplicado procedimento formal de deduplicação. O processo nunca poderá eliminar registros sem evidência preservada em log.

A prioridade de reconciliação deve seguir a seguinte ordem: primeiro, comparar hash e nome de origem; depois, comparar data de ingestão; em seguida, verificar se há revisão retroativa da fonte; por fim, definir qual versão permanece ativa na camada analítica, mantendo todas as versões anteriores preservadas na camada de auditoria.

## 12. Política de exceções

Nem toda inconsistência exige descarte definitivo. A política de ingestão deve distinguir entre falha crítica, falha relevante e falha tolerável.

| Tipo de exceção | Definição | Tratamento |
|---|---|---|
| Crítica | Impede leitura ou invalida estrutura mínima | Bloqueio imediato |
| Relevante | Permite leitura, mas compromete uso analítico | Quarentena e revisão |
| Tolerável | Não compromete a ingestão, mas exige registro | Prosseguir com flag |

Arquivos em quarentena não devem ser usados em cálculo de métricas nem em produção analítica até que a anomalia tenha sido formalmente tratada.

## 13. Política de auditoria e rastreabilidade

Toda ingestão deverá gerar trilha de auditoria suficiente para reconstrução completa do processo. Isso inclui identificação do arquivo bruto, hash, metadados, status das validações, logs de transformação e vínculo com a versão metodológica vigente à época da carga.

| Evidência de auditoria | Obrigatoriedade |
|---|---|
| Registro da origem | Obrigatória |
| Hash do arquivo | Obrigatória |
| Inventário de colunas | Obrigatória |
| Resultado da validação | Obrigatória |
| Registro de transformações | Obrigatória |
| Identificador da metodologia vigente | Obrigatória |
| Justificativa de exceções | Condicional |

## 14. Frequência de revisão da política

Como a política de ingestão depende da estabilidade do portal, do formato dos arquivos e da evolução do próprio projeto, ela deve ser revisada periodicamente.

| Frequência | Escopo da revisão |
|---|---|
| Mensal | Verificação de estabilidade do layout, formato e schema |
| Trimestral | Revisão formal de nomenclatura, validações e controles |
| Extraordinária | Mudança da fonte, do formato, do schema ou da necessidade de novos campos |

Toda revisão desta política deverá ser registrada em documento próprio de alterações metodológicas e operacionais.

## 15. Responsabilidades

A política deve prever, mesmo em ambiente enxuto, responsabilidades claras sobre captura, validação e aprovação do uso analítico dos arquivos.

| Papel | Responsabilidade |
|---|---|
| Responsável pela coleta | Obter o arquivo oficial e registrar a origem |
| Responsável pela validação | Executar as checagens estruturais e semânticas |
| Responsável pela governança | Aprovar exceções e manter trilha documental |
| Responsável metodológico | Autorizar uso do dado na camada analítica |

## 16. Diretriz final de uso no projeto

Para o projeto de identificação de oportunidades em títulos do Tesouro Direto, a ingestão por CSV deve ser tratada como **processo oficial de entrada de dados** até que exista fonte superior, mais estável ou mais automatizável que preserve o mesmo grau de confiabilidade institucional. Isso significa que a evolução metodológica do projeto pode prosseguir normalmente sobre base CSV, desde que a disciplina operacional descrita neste documento seja respeitada.

A adoção desta política torna o projeto menos dependente de infraestrutura de integração e mais aderente ao estágio atual de planejamento. Ao mesmo tempo, preserva a base necessária para crescimento futuro, caso a ingestão venha a ser automatizada posteriormente.

## Referências

[1]: https://www.tesourotransparente.gov.br/ckan/organization/codip "Tesouro Transparente — Organização CODIP no CKAN"
[2]: https://www.tesourodireto.com.br/produtos/dados-sobre-titulos/historico-de-precos-e-taxas "Tesouro Direto — Histórico de Preços e Taxas"
[3]: https://www.anbima.com.br/data/files/A0/02/CC/70/8FEFC8104606BDC8B82BA2A8/Metodologias%20ANBIMA%20de%20Precificacao%20Titulos%20Publicos.pdf "ANBIMA — Metodologia de Precificação de Títulos Públicos Federais"
