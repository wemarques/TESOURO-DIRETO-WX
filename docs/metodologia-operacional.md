# Documento Metodológico Operacional

**Projeto:** Identificação de Oportunidades em Títulos do Tesouro Direto Brasileiro  
**Autor:** Manus AI  
**Data:** 2026-04-06

## 1. Finalidade do documento

Este documento estabelece a **metodologia operacional** para identificar oportunidades de investimento no universo de títulos do **Tesouro Direto brasileiro**, a partir da base histórica de preços e taxas enviada pelo usuário e de referências institucionais e técnicas sobre precificação, risco de taxa e estrutura a termo. O objetivo central é definir um padrão de trabalho robusto para a fase de planejamento, delimitando critérios analíticos, fórmulas candidatas, políticas de segmentação, regras de validação e rotinas de revisão metodológica.

A premissa principal do projeto é que uma oportunidade em renda fixa soberana **não deve ser definida apenas pela taxa observada em um dado dia**, mas pela combinação entre **retorno potencial**, **posição relativa na curva**, **liquidez operacional**, **coerência de precificação** e **risco de sensibilidade a juros**. Essa abordagem é compatível com as práticas usuais de análise de renda fixa, nas quais preço, yield, duration, convexidade e estrutura a termo são tratados de forma integrada [1] [2].

## 2. Escopo metodológico

O escopo do framework cobre os títulos disponibilizados no conjunto histórico do Tesouro Direto e deve operar sobre observações diárias de taxa e preço unitário. A análise preliminar da base enviada indica que ela contém histórico amplo, sem valores faltantes nas colunas centrais, abrangendo múltiplas famílias de títulos e diferentes horizontes de vencimento, o que a torna adequada para um processo de modelagem comparativa e segmentada.

O framework metodológico proposto possui quatro objetivos simultâneos. O primeiro é **padronizar os dados** para tornar comparáveis observações que hoje pertencem a famílias instrumentais distintas. O segundo é **medir valor relativo** dentro de subconjuntos homogêneos, evitando comparações indevidas entre papéis pós-fixados, prefixados e indexados à inflação. O terceiro é **ranquear oportunidades** por meio de fórmulas transparentes e auditáveis. O quarto é **preservar governança metodológica**, com revisões formais, trilha de mudanças e critérios explícitos para promoção, ajuste ou descarte de modelos.

## 3. Princípios metodológicos

A metodologia deve seguir princípios consistentes com o funcionamento do mercado brasileiro de títulos públicos e com fundamentos clássicos de renda fixa. A ANBIMA explicita que a precificação de títulos públicos se apoia na coleta de taxas de compra e venda, observadas ou avaliadas como referência de preço justo, com processo de filtro estatístico e cálculo diário de taxas indicativas [2]. O Tesouro Direto, por sua vez, disponibiliza histórico oficial por família de título, reforçando a necessidade de trabalhar com fontes rastreáveis e segmentação por instrumento [3]. Em termos conceituais, a literatura técnica de renda fixa destaca que a relação inversa entre preço e yield, bem como as medidas de duration, convexidade e curva de juros, são centrais para avaliação de risco e retorno [1].

> "A precificação de títulos públicos da ANBIMA baseia-se na coleta de taxas de compra e venda, que devem ser referenciadas em ofertas firmes praticadas ou observadas no mercado, quando disponíveis e, indicativas, taxas avaliadas como referência de preço justo em que a oferta encontra a sua demanda, para negociação do ativo no fechamento do mercado." — **Metodologia ANBIMA de Precificação de Títulos Públicos Federais** [2]

A partir desses fundamentos, o projeto deve adotar os seguintes princípios operacionais. A comparação deve ser **intraclasse antes de ser interclasse**. O score final deve ser **explicável** e decomponível em fatores. O componente de oportunidade deve ser sempre acompanhado de um componente de **controle de risco**. E toda alteração de pesos, fórmulas, filtros ou segmentações deve ser tratada como alteração metodológica formal, sujeita a revisão documentada.

## 4. Universo analítico e política de segmentação

A primeira decisão operacional relevante é a **segmentação do universo**. Ela é necessária porque títulos com cupons, indexação inflacionária, pós-fixação ou finalidades específicas possuem estruturas de fluxo e sensibilidade muito diferentes. A comparabilidade direta entre suas taxas observadas é, portanto, metodologicamente inadequada.

A política de segmentação deve combinar três eixos: **família do título**, **bucket de prazo** e **estrutura de fluxo**. A aplicação conjunta desses eixos cria células analíticas nas quais os testes de valor relativo e os rankings passam a ter interpretação econômica mais consistente.

| Eixo de segmentação | Regra operacional | Justificativa metodológica |
|---|---|---|
| Família do título | Separar, no mínimo, Tesouro Selic, Tesouro Prefixado, Tesouro Prefixado com Juros Semestrais, Tesouro IPCA+, Tesouro IPCA+ com Juros Semestrais, Tesouro Educa+ e Tesouro Renda+ | Evita comparar instrumentos com indexadores e perfis de fluxo distintos [3] |
| Estrutura de fluxo | Separar títulos bullet, com cupom semestral e com cronograma previdenciário/educacional | Duration, convexidade e dinâmica de preço diferem materialmente entre estruturas [1] |
| Prazo remanescente | Criar buckets por anos até vencimento ou duration equivalente | O valor relativo em renda fixa depende do vértice da curva e do risco de taxa [1] |
| Janela temporal | Trabalhar separadamente com snapshot corrente, histórico recente e histórico longo | Permite distinguir oportunidade tática de distorção estrutural |
| Liquidez implícita | Classificar por spread relativo e recorrência da observação | Reduz risco de ranking enviesado por papéis pouco executáveis |

A segmentação por prazo pode seguir uma malha operacional inicial composta por **curto prazo**, **intermediário**, **longo** e **ultralongo**. Entretanto, a referência principal para comparabilidade deve migrar progressivamente de prazo simples para **duration efetiva ou duration de Macaulay/modified duration**, sempre que houver qualidade de dados suficiente para esse avanço [1] [2].

## 5. Camada de dados e padronização analítica

A etapa de preparação de dados deve transformar a base original em uma base analítica com variáveis observadas, derivadas e de controle. A estrutura mínima recomendada está resumida na tabela a seguir.

| Grupo | Variáveis mínimas | Finalidade |
|---|---|---|
| Identificação | tipo_titulo, data_base, data_vencimento | Chave analítica e governança da série |
| Mercado | taxa_compra_manha, taxa_venda_manha, pu_compra_manha, pu_venda_manha, pu_base_manha | Mensuração de preço, yield e liquidez |
| Prazo | dias_ate_vencimento, anos_ate_vencimento | Segmentação e risco de taxa |
| Estrutura | flag_cupom, flag_indexado_inflacao, flag_pos_fixado, flag_produto_planejamento | Regras de comparabilidade |
| Curva | taxa_teorica_curva, residuo_curva, slope_local, curvature_local | Medidas de valor relativo |
| Risco | duration_aprox, convexidade_aprox, dv01_aprox | Controle de exposição |
| Qualidade | flag_outlier, flag_interpolado, flag_inconsistencia_preco_taxa | Validação e auditoria |

A padronização numérica deve converter vírgula decimal para ponto, normalizar datas para tipo calendário, padronizar nomes de colunas e criar um dicionário de famílias de títulos. Além disso, os dados devem ser persistidos com metadados de ingestão, incluindo data de carga, hash do arquivo bruto e versão da metodologia aplicada à transformação.

## 6. Fórmulas candidatas para o framework de oportunidade

O framework deve nascer com **mais de uma fórmula candidata**, precisamente para evitar que o projeto fique prematuramente dependente de um único desenho de score. O processo recomendado é começar com um modelo-base transparente, manter um modelo intermediário com ajuste por risco e desenvolver um modelo avançado ancorado em curva ajustada.

### 6.1. Fórmula candidata A: Score base de oportunidade

A fórmula candidata A deve funcionar como **modelo operacional inicial**, simples, auditável e de fácil interpretação.

```text
Score_A = 0,40 × Carry_Norm + 0,40 × RV_Norm + 0,20 × Liquidez_Norm
```

Nessa formulação, o termo **Carry_Norm** representa o ganho relativo estimado do título frente a um benchmark adequado ao seu grupo; **RV_Norm** representa a atratividade de valor relativo dentro da célula analítica; e **Liquidez_Norm** representa a executabilidade do papel observada por spreads de compra e venda. Essa estrutura está alinhada ao racional já presente no material de planejamento enviado pelo usuário e é coerente com a lógica de combinar retorno esperado, posicionamento relativo e viabilidade operacional.

A normalização recomendada para a primeira versão é a seguinte:

```text
Carry = Taxa_Compra - Benchmark_Grupo
Carry_Norm = winsorize_minmax(Carry)

Spread_Relativo = |PU_Compra - PU_Venda| / PU_Base
Liquidez_Norm = 1 - min(1, Spread_Relativo / Limite_Spread_Grupo)

RV_Z = zscore(Taxa_Compra dentro do grupo analítico)
RV_Norm = clip(0, 1, 0,5 + 0,5 × sinal_desejado × RV_Z_Ajustado)
```

A orientação do sinal em **RV_Norm** deve ser definida por família de título. Em papéis onde taxa mais alta indica maior atratividade relativa, o resíduo positivo pode ser premiado. Em famílias nas quais a estrutura de preço seja mais diretamente comparável, o valor relativo deve migrar da taxa bruta para o **resíduo da curva ajustada**, o que é metodologicamente superior.

### 6.2. Fórmula candidata B: Score ajustado por risco de taxa

A fórmula candidata B introduz uma penalização explícita para papéis cujo bom posicionamento aparente decorre principalmente de prazo muito longo e sensibilidade excessiva a juros.

```text
Score_B = 0,35 × Carry_Norm + 0,30 × RV_Norm + 0,15 × Liquidez_Norm + 0,20 × Risco_Norm
```

Onde:

```text
Risco_Norm = 1 - Penalidade_Risco
Penalidade_Risco = w1 × Duration_Norm + w2 × Convexidade_Choque + w3 × DV01_Norm
```

Neste desenho, **Risco_Norm** não premia risco alto; ele reduz a pontuação quando o ativo apresenta elevada sensibilidade a deslocamentos paralelos ou não paralelos da curva. A vantagem dessa fórmula é evitar que o ranking seja capturado por títulos ultralongos que carregam prêmio aparente, mas também elevada volatilidade de marcação a mercado [1].

### 6.3. Fórmula candidata C: Score por resíduo de curva ajustada

A fórmula candidata C é a mais adequada para uma fase metodológica madura, pois substitui comparações simplificadas por um processo explícito de ajuste da estrutura a termo.

```text
Taxa_Teorica_i = f(vencimento_i, fatores_de_curva)
Residuo_i = Taxa_Observada_i - Taxa_Teorica_i

Score_C = 0,30 × Carry_Norm + 0,40 × Residuo_Curva_Norm + 0,15 × Rolldown_Norm + 0,15 × Liquidez_Norm
```

A curva teórica pode ser estimada, em fases sucessivas, por: regressão local por bucket, spline cúbica monotônica, ou modelo paramétrico **Nelson-Siegel-Svensson**, amplamente reconhecido em análise de estrutura a termo [1]. O componente **Rolldown_Norm** mede o benefício esperado da caminhada natural do título ao longo da curva, desde que essa métrica seja calculada em ambiente metodologicamente homogêneo.

### 6.4. Benchmark de carry por grupo

A definição do benchmark não deve ser global e fixa. Ela deve respeitar a família analítica.

| Grupo | Benchmark recomendado | Observação |
|---|---|---|
| Tesouro Selic | Taxa Selic ou referência pós-fixada equivalente | Score de oportunidade tende a depender menos de curva e mais de spread/execução |
| Prefixados bullet | Curva nominal do mesmo bucket de duration | Comparabilidade centrada em taxa nominal e prazo |
| Prefixados com cupom | Curva nominal ajustada por duration e fluxo | Necessário evitar viés por estrutura de cupom |
| IPCA+ bullet | Curva real do mesmo bucket | Comparação em termos reais |
| IPCA+ com cupom | Curva real ajustada por fluxos | Maior sensibilidade à convexidade e ao perfil de caixa |
| Educa+ e Renda+ | Curva real segmentada e política própria | Requer tratamento específico por finalidade e cronograma de fluxo |

## 7. Política de segmentação operacional

A segmentação metodológica deve ser tratada como política formal e não como simples convenção técnica. Toda observação somente poderá participar de ranking competitivo quando estiver dentro de uma **célula analítica válida**, definida por família, bucket de prazo e qualidade mínima de dados.

A política recomendada é a seguinte.

| Dimensão | Regra | Consequência operacional |
|---|---|---|
| Família | Nunca ranquear em conjunto títulos de indexadores diferentes | Evita distorção econômica do score |
| Cupom | Não comparar diretamente bullet com cupom sem ajuste de duration/fluxo | Preserva comparabilidade |
| Produtos temáticos | Educa+ e Renda+ devem ter submetodologia própria | Estrutura de uso e horizonte diferem dos papéis tradicionais |
| Bucket mínimo | Exigir número mínimo de observações por célula analítica | Sem massa crítica, não calcular z-score nem resíduo de curva |
| Liquidez | Títulos com spread relativo acima do limite do grupo entram como observação, mas não em ranking principal | Mantém visibilidade sem contaminar top oportunidades |
| Interpolação | Observações dependentes de curva interpolada devem receber flag específico | Necessário para auditoria e interpretação |

Como regra de governança, quando uma célula analítica possuir **massa estatística insuficiente**, o processo deve escalar para uma estrutura hierárquica: primeiro ampliar o bucket de prazo, depois migrar para agrupamento por duration equivalente e, apenas em último caso, excluir a célula do ranking principal e mantê-la em monitoramento.

## 8. Critérios de validação metodológica

O framework deve operar com duas camadas de validação: **validação de dados** e **validação de modelo**. Ambas são mandatórias.

### 8.1. Validação de dados

A base enviada deve ser validada diariamente antes de qualquer cálculo de score. As regras mínimas são descritas abaixo.

| Critério | Regra operacional | Ação em caso de falha |
|---|---|---|
| Integridade de schema | Presença de todas as colunas obrigatórias | Bloquear processamento |
| Formato de datas | Datas válidas em padrão interpretável | Reprocessar ou descartar linha |
| Conversão numérica | Taxas e PU convertidos sem erro | Flag de inconsistência |
| Relação temporal | data_vencimento > data_base | Descartar linha |
| Coerência de preço e taxa | Variações extremas incompatíveis com o grupo devem ser auditadas | Enviar para fila de exceção |
| Coerência bid/ask | Taxa indicativa deve ser consistente com compra e venda, por analogia ao racional institucional | Rebaixar confiança da observação [2] |
| Duplicidade | Não permitir múltiplas linhas idênticas por chave lógica | Deduplicar com rastreabilidade |
| Missing | Sem valores faltantes nas variáveis centrais | Bloquear score parcial |

A ANBIMA adota filtro estatístico para eliminar observações capazes de contaminar o cálculo da média e exige consistência entre taxas de compra, venda e indicativa [2]. Ainda que a base do Tesouro Direto não seja idêntica ao processo ANBIMA de formação de taxa indicativa, o princípio de **filtro pré-modelagem e coerência interna das cotações** deve ser incorporado ao framework.

### 8.2. Validação de modelo

A validação do modelo deve responder a quatro perguntas: o score é **estável**, **explicável**, **economicamente coerente** e **útil em amostras futuras**?

| Eixo | Métrica sugerida | Objetivo |
|---|---|---|
| Estabilidade | Correlação de ranking entre dias consecutivos | Evitar score errático |
| Robustez | Sensibilidade a winsorização, pesos e buckets | Medir dependência de parâmetros |
| Coerência econômica | Relação entre score alto e retorno ajustado a risco em janelas futuras | Testar utilidade da metodologia |
| Generalização | Backtest walk-forward por período | Evitar sobreajuste |
| Discriminação | Separação entre decis superiores e inferiores do score | Confirmar capacidade de ranqueamento |
| Interpretabilidade | Decomposição da pontuação por fator | Garantir auditoria |

### 8.3. Testes mínimos para promoção de versão metodológica

Uma versão metodológica só deve ser promovida para uso principal quando cumprir simultaneamente os seguintes critérios institucionais internos.

| Critério | Exigência mínima |
|---|---|
| Documentação | Fórmula, pesos, regras e exceções documentados |
| Reprodutibilidade | Mesmo input gera mesmo output |
| Rastreabilidade | Toda pontuação permite reconstrução fator a fator |
| Robustez | Sem inversão material de ranking após pequenas perturbações de parâmetros |
| Coerência econômica | Score não premia sistematicamente baixa liquidez ou risco extremo sem contrapartida |
| Revisão humana | Aprovação analítica registrada |

## 9. Política de outliers, exceções e observações não comparáveis

A política de outliers deve distinguir entre **erro de dado** e **evento de mercado**. Observações extremas não devem ser automaticamente excluídas quando houver justificativa econômica plausível, mas devem receber marcação específica para evitar que contaminem estimadores de grupo.

O processo recomendado é sequencial. Primeiro, aplicar filtros univariados simples. Em seguida, aplicar filtros intragrupo por boxplot, desvio robusto ou mediana e MAD. Depois, submeter os casos extremos a validação cruzada com séries vizinhas de mesmo grupo e com a dinâmica preço-taxa esperada. O racional para esse desenho é compatível com o uso institucional de filtros estatísticos em dados de precificação [2].

## 10. Governança de pesos, fórmulas e versões

A governança metodológica deve tratar o framework como um ativo versionado. Nenhuma mudança de pesos, buckets, regras de exclusão ou fórmulas candidatas deve ocorrer sem registro formal. A recomendação é trabalhar com três estados de versão: **experimental**, **validada** e **produção analítica**.

| Estado | Definição | Requisito |
|---|---|---|
| Experimental | Fórmula em teste, sem uso decisório principal | Testes preliminares e documentação inicial |
| Validada | Fórmula aprovada em validação interna | Backtest, análise de sensibilidade e revisão técnica |
| Produção analítica | Fórmula padrão do projeto | Histórico de estabilidade e governança formal |

Toda mudança metodológica deve gerar registro contendo hipótese de alteração, impacto esperado, impacto observado, data de vigência, responsável pela aprovação e necessidade de reprocessamento histórico.

## 11. Cronograma de revisão metodológica

O cronograma de revisão deve combinar monitoramento frequente com revisões estruturadas. Como o mercado de títulos públicos é sensível a mudanças macroeconômicas, composição da curva e liquidez por família, o framework não deve ficar longos períodos sem recalibração.

| Frequência | Escopo da revisão | Entregável |
|---|---|---|
| Diário | Verificação de integridade, ingestão, outliers e flags de exceção | Log operacional |
| Semanal | Revisão de estabilidade do ranking, dispersão por grupo e títulos fora do padrão | Relatório curto de monitoramento |
| Mensal | Avaliação de desempenho das fórmulas candidatas e sensibilidade de pesos | Memorando analítico |
| Trimestral | Revisão formal de buckets, benchmarks, pesos, critérios de liquidez e política de exclusão | Ata metodológica versionada |
| Semestral | Reavaliação da arquitetura conceitual do score e inclusão de novos fatores | Revisão metodológica ampliada |
| Extraordinária | Mudança regulatória, alteração material de mercado ou inclusão de nova família de título | Nota técnica extraordinária |

A revisão trimestral é a frequência mínima recomendada para reavaliar pesos e segmentação, especialmente porque a literatura e a prática institucional mostram que curva, duration e dinâmica de marcação a mercado não permanecem estáticas ao longo do tempo [1] [2].

## 12. Sequência operacional recomendada

O processo metodológico deve seguir uma ordem fixa para reduzir risco operacional e garantir auditabilidade.

| Etapa | Descrição | Saída esperada |
|---|---|---|
| 1 | Ingestão do arquivo bruto | Base bruta validada |
| 2 | Padronização e tipagem | Base limpa |
| 3 | Enriquecimento com prazo, flags e grupos | Base analítica |
| 4 | Aplicação de filtros e exceções | Base elegível |
| 5 | Construção de curva ou benchmark por grupo | Referência analítica |
| 6 | Cálculo das fórmulas candidatas | Tabela de scores |
| 7 | Aplicação de penalizações e governança de ranking | Ranking principal e ranking monitorado |
| 8 | Validação e logging | Evidências de qualidade |
| 9 | Publicação analítica interna | Resultado auditável |

## 13. Recomendação de priorização metodológica

Para a continuidade do projeto, a recomendação é iniciar com a **Fórmula Candidata A** como modelo-base oficial de planejamento, mantendo a **Fórmula B** em validação paralela como modelo de controle de risco e preparando a **Fórmula C** como objetivo de maturidade metodológica. Essa sequência preserva simplicidade inicial sem abrir mão de sofisticação progressiva.

Em termos de política analítica, a maior prioridade deve ser dada a quatro frentes. A primeira é a **segmentação correta por família e fluxo**. A segunda é a **construção de referência de curva por grupo**. A terceira é a **qualificação do componente de liquidez**. A quarta é a **implantação de um protocolo formal de validação e revisão**. Sem esses quatro elementos, o ranking pode produzir aparentes oportunidades que, na prática, refletem apenas mistura inadequada de instrumentos, baixa liquidez ou exposição excessiva a prazo.

## 14. Conclusão metodológica

Este documento transforma o plano inicial em uma **metodologia operacional estruturada**, adequada para orientar o projeto ainda na fase de planejamento. O framework proposto parte de princípios sólidos de renda fixa, respeita a heterogeneidade do universo do Tesouro Direto e estabelece regras explícitas para score, segmentação, validação e governança. O ganho principal dessa abordagem é substituir uma lógica genérica de ranqueamento por um processo disciplinado, auditável e progressivamente calibrável.

A decisão metodológica mais importante é reconhecer que a oportunidade em títulos públicos brasileiros deve ser tratada como uma função conjunta de **valor relativo, carry, liquidez e risco de taxa**, e não como simples ordenação por taxa observada. Esse posicionamento torna o projeto mais aderente às práticas profissionais de análise de renda fixa e cria uma base adequada para evoluções futuras sem necessidade de ruptura conceitual [1] [2] [3].

## Referências

[1]: https://vlab.stern.nyu.edu/docs/fixedIncome "V-Lab: Fixed Income Analysis Documentation"
[2]: https://www.anbima.com.br/data/files/A0/02/CC/70/8FEFC8104606BDC8B82BA2A8/Metodologias%20ANBIMA%20de%20Precificacao%20Titulos%20Publicos.pdf "ANBIMA — Metodologia de Precificação de Títulos Públicos Federais"
[3]: https://www.tesourodireto.com.br/produtos/dados-sobre-titulos/historico-de-precos-e-taxas "Tesouro Direto — Histórico de Preços e Taxas"
