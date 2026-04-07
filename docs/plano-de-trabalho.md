# Plano de Trabalho de Planejamento — Oportunidades em Títulos do Tesouro Direto Brasileiro

**Autor:** Manus AI  
**Data:** 06/04/2026

## 1. Síntese executiva

Este documento consolida a **fase de planejamento** do projeto voltado à identificação de oportunidades de investimento em títulos do **Tesouro Direto brasileiro**, a partir da base histórica enviada pelo usuário e de referências metodológicas alinhadas às práticas de mercado. O foco deste material é exclusivamente o desenho do trabalho analítico, estatístico e de governança do projeto. Não há, neste estágio, qualquer proposição de desenvolvimento de sistema, aplicação ou automação operacional.

A análise do arquivo encaminhado indica que a base possui amplitude histórica suficiente para suportar um framework robusto de pesquisa aplicada. O conjunto contém **169.478 registros**, cobre o período de **31/12/2004 a 02/04/2026** em `data_base`, alcança vencimentos entre **04/01/2005 e 15/12/2084** e inclui **oito famílias de títulos**. No snapshot mais recente, datado de **02/04/2026**, há **60 registros** distribuídos entre títulos pós-fixados, prefixados, indexados à inflação e produtos de finalidade previdenciária/educacional. Isso confirma que o problema central do projeto não é apenas ranquear taxas, mas construir uma metodologia capaz de comparar instrumentos **heterogêneos em fluxo de caixa, indexação, sensibilidade a juros e liquidez**.

Sob a ótica de mercado, o planejamento deve partir de quatro princípios. O primeiro é a **relação inversa entre preço e yield**, fundamento básico da renda fixa e da identificação de desalinhamentos de valor relativo [1]. O segundo é a necessidade de incorporar **duration e convexidade** como medidas estruturais de risco de taxa [1]. O terceiro é tratar a **estrutura a termo de juros** como eixo principal de comparação entre títulos, em vez de avaliar isoladamente a taxa observada [1]. O quarto é reconhecer que a referência de mercado para títulos públicos no Brasil é construída a partir de práticas de **marcação a mercado**, com tratamento estatístico de outliers, cálculo de taxas indicativas e critérios de consistência entre compra, venda e preço justo [3].

> "Taxa Indicativa: taxas avaliadas pela instituição como referência de preço justo, em que a oferta encontra a sua demanda para negociação do ativo no fechamento do mercado." — **ANBIMA** [3]

## 2. Diagnóstico inicial da base enviada

A base fornecida apresenta estrutura compatível com um projeto quantitativo de análise de oportunidades. As colunas observadas são consistentes com o histórico oficial de preços e taxas do Tesouro Direto, incluindo tipo de título, data de vencimento, data-base, taxas de compra e venda e preços unitários de compra, venda e base. A inspeção inicial não identificou valores ausentes nas colunas centrais utilizadas para planejamento, o que reduz o risco de retrabalho na fase de preparação de dados.

| Indicador | Resultado observado na base enviada |
|---|---:|
| Total de registros | 169.478 |
| Famílias de títulos | 8 |
| Início da série (`data_base`) | 31/12/2004 |
| Fim da série (`data_base`) | 02/04/2026 |
| Menor vencimento observado | 04/01/2005 |
| Maior vencimento observado | 15/12/2084 |
| Registros no snapshot mais recente | 60 |
| Valores ausentes nas colunas centrais | 0 |

A composição histórica mostra predominância de papéis indexados à inflação e prefixados, mas também inclui Tesouro Selic, IGPM+, Educa+ e Renda+. Essa diversidade é valiosa para pesquisa, porém exige segmentação metodológica. Comparações diretas entre famílias não são economicamente neutras, porque cada grupo responde a fatores distintos de precificação e carrega perfis muito diferentes de prazo e sensibilidade.

| Família de título | Registros históricos | Observação de planejamento |
|---|---:|---|
| Tesouro IPCA+ com Juros Semestrais | 42.829 | Requer tratamento explícito do fluxo de cupons e risco de reinvestimento |
| Tesouro Prefixado | 27.545 | Base importante para estudos de curva nominal e valor relativo |
| Tesouro Prefixado com Juros Semestrais | 26.569 | Comparação deve considerar cupom e duration distinta |
| Tesouro Selic | 20.929 | Útil como referência de baixo risco de mercado |
| Tesouro IPCA+ | 18.046 | Relevante para estudos reais de médio e longo prazo |
| Tesouro IGPM+ com Juros Semestrais | 15.679 | Série histórica relevante, mas com menor aderência ao cardápio atual |
| Tesouro Educa+ | 11.545 | Produto com finalidade específica e longa duration |
| Tesouro Renda+ Aposentadoria Extra | 6.336 | Produto extremamente longo, com forte sensibilidade a juros reais |

O snapshot mais recente também reforça a heterogeneidade do universo analisado. Os títulos Selic concentram prazos curtos, os prefixados ocupam a parte curta e intermediária da curva nominal, os IPCA+ e IPCA+ com juros se distribuem na curva real de médio e longo prazo, enquanto Renda+ representa a ponta muito longa da estrutura a termo. Isso inviabiliza um **score único e indiferenciado** como primeira abordagem metodológica.

| Família de título no snapshot de 02/04/2026 | Quantidade | Taxa de compra mediana (% a.a.) | Prazo mediano (anos) |
|---|---:|---:|---:|
| Tesouro Selic | 4 | 0,02 | 2,41 |
| Tesouro Prefixado | 5 | 13,87 | 2,75 |
| Tesouro IGPM+ com Juros Semestrais | 1 | 8,18 | 4,75 |
| Tesouro Prefixado com Juros Semestrais | 6 | 14,07 | 5,75 |
| Tesouro IPCA+ | 7 | 7,51 | 9,12 |
| Tesouro IPCA+ com Juros Semestrais | 10 | 7,44 | 12,74 |
| Tesouro Educa+ | 19 | 7,41 | 13,70 |
| Tesouro Renda+ Aposentadoria Extra | 8 | 7,04 | 41,20 |

## 3. Premissas metodológicas para a fase de planejamento

O relatório de planejamento enviado pelo usuário traz elementos úteis, especialmente na preocupação com governança, padronização de regras, controle de pesos e organização do trabalho. Entretanto, como o projeto está explicitamente na **fase de planejamento**, a priorização correta não é arquitetura de aplicação, mas a formulação de um **framework analítico auditável**, capaz de responder com consistência à pergunta: *quando um título do Tesouro Direto está relativamente atraente frente aos demais títulos comparáveis e frente ao seu próprio histórico?*

Para responder a essa pergunta, o projeto deve separar com clareza três camadas. A primeira é a camada de **dados e convenções**, responsável por padronizar famílias de títulos, fluxos, prazos, periodicidades e checagens de consistência entre taxa, PU e vencimento. A segunda é a camada de **modelagem da oportunidade**, na qual se estimam métricas de carry, rolldown, valor relativo, liquidez e ajuste por risco. A terceira é a camada de **validação**, destinada a testar se os sinais gerados são estáveis, economicamente interpretáveis e robustos ao longo do tempo.

Do ponto de vista de mercado, referências institucionais indicam que a formação de preços em títulos públicos depende de taxas de compra, venda e indicativas, com filtragem estatística de outliers e critérios formais de consistência [3]. Na prática, isso significa que o planejamento do projeto deve incorporar, desde o início, mecanismos de controle de qualidade inspirados nessa lógica. Além disso, a documentação de renda fixa consultada reforça que duration, convexidade, DV01, key rate duration e modelos de curva são instrumentos usuais para mensurar risco e valor relativo em renda fixa [1]. Já a própria página oficial do Tesouro Direto confirma a disponibilidade de históricos por família de papel, o que apoia a construção de estudos comparativos consistentes e auditáveis [2].

## 4. Estrutura analítica recomendada

A abordagem recomendada para o projeto é **hierárquica**. Primeiro, os títulos devem ser comparados apenas dentro de subconjuntos economicamente comparáveis. Em seguida, cada título deve ser avaliado por um conjunto de fatores quantitativos. Por fim, esses fatores devem ser combinados em um score de oportunidade governado por regras claras, revisão periódica e validação empírica.

| Camada analítica | Objetivo | Recomendação para o planejamento |
|---|---|---|
| Segmentação do universo | Evitar comparações economicamente incorretas | Separar por família de título, indexador, presença de cupom e bucket de prazo |
| Curva de referência | Estimar valor justo relativo | Construir curvas nominais e reais por vencimento e, em fase posterior, testar Nelson-Siegel-Svensson [1] |
| Métricas de retorno esperado | Capturar atratividade econômica | Medir carry, inclinação da curva, rolldown esperado e spread versus benchmark interno |
| Métricas de valor relativo | Detectar desalinhamentos | Trabalhar com resíduos da curva, z-scores intrafamília e desvios versus histórico próprio |
| Métricas de risco | Penalizar oportunidades frágeis | Incluir duration, DV01, convexidade e sensibilidade por trecho da curva [1] |
| Métricas de execução | Filtrar sinais pouco operáveis | Incorporar spread compra-venda e estabilidade do preço como proxies de liquidez |
| Camada de validação | Testar utilidade real do framework | Aplicar validação temporal, testes de estabilidade de ranking e análise por regimes |

A fórmula preliminar de score mencionada no material enviado — combinando carry, valor relativo e liquidez — é uma boa hipótese inicial, mas ainda insuficiente como definição final. O risco metodológico de um score simples é favorecer automaticamente títulos mais longos ou mais voláteis, confundindo prêmio de risco com oportunidade. Por isso, o planejamento deve tratar essa fórmula como **ponto de partida**, não como conclusão. A recomendação é manter a lógica de combinação multifatorial, porém acrescentando uma camada explícita de ajuste por risco de taxa antes da consolidação final do ranking.

## 5. Modelos estatísticos e métricas recomendados

A fase de planejamento deve prever o teste comparativo entre modelos de complexidade crescente. A ideia central não é começar pelo modelo mais sofisticado, mas por uma trilha que permita evidenciar ganho incremental de qualidade analítica. Em renda fixa, isso significa sair de métricas descritivas e comparações simples, avançar para modelagem da curva e, somente então, avaliar versões mais elaboradas de score e de detecção de anomalias.

| Bloco de modelagem | Finalidade | Prioridade no planejamento |
|---|---|---|
| Estatística descritiva por família e prazo | Entender regimes, dispersões e anomalias básicas | Alta |
| Z-score intrafamília e por bucket de vencimento | Detectar desvios relativos simples | Alta |
| Resíduo em relação à curva ajustada | Medir valor relativo de forma mais econômica | Alta |
| Regressões por curva e prazo | Explicar taxa observada por fatores estruturais | Alta |
| Nelson-Siegel-Svensson | Modelar nível, inclinação e curvatura da curva [1] | Média-Alta |
| PCA em fatores de curva | Identificar choques dominantes de nível, slope e curvature | Média |
| Modelos de detecção de regime | Separar ambientes de política monetária e inflação | Média |
| Análise de estabilidade temporal do score | Verificar robustez do ranking | Alta |
| Testes de sensibilidade de pesos | Avaliar fragilidade do score multifatorial | Alta |

Em termos de métricas, a recomendação é organizar o framework em quatro grupos. O primeiro grupo é o de **retorno implícito**, com carry e rolldown. O segundo é o de **valor relativo**, com resíduos da curva, spreads versus títulos comparáveis e padronizações por z-score. O terceiro é o de **risco de taxa**, com duration, convexidade e DV01. O quarto é o de **liquidez e executabilidade**, para evitar que o ranking privilegie sinais de baixa utilidade prática. Essa separação ajuda a manter governança analítica e facilita auditoria futura dos pesos e decisões.

## 6. Governança de dados e critérios de qualidade

A governança precisa ser parte do planejamento, e não uma atividade secundária. A documentação metodológica da ANBIMA deixa claro que o mercado trabalha com filtros estatísticos, critérios mínimos de observação, consistência entre pontas e monitoramento de qualidade [3]. Para o projeto, isso se traduz em um conjunto de regras internas de validação, com trilhas de auditoria e revisão periódica.

| Dimensão de governança | Critério recomendado |
|---|---|
| Fonte primária | Prioridade para base oficial do Tesouro Direto [2] |
| Fonte de referência de mercado | Uso de convenções e metodologias ANBIMA para validação e comparação [3] |
| Padronização | Normalização de nomes, indexadores, cupons, calendário e convenções de prazo |
| Controle de qualidade | Checagens entre taxa, PU, vencimento, monotonicidade e duplicidades |
| Tratamento de outliers | Filtros estatísticos inspirados em quartis e dispersão cross-section [3] |
| Versionamento metodológico | Registro formal de mudanças em pesos, fórmulas e critérios |
| Frequência de revisão | Revisão mensal de qualidade da base e trimestral do framework analítico |
| Reprodutibilidade | Geração de artefatos e relatórios de validação para cada revisão metodológica |

Uma implicação importante do diagnóstico é que títulos como **Renda+**, **Educa+** e papéis com cupons semestrais não devem ser tratados como meras extensões de NTN-B ou prefixados tradicionais. Ainda que haja parentesco econômico entre algumas famílias, as diferenças de fluxo e finalidade de uso alteram substancialmente a comparabilidade. O planejamento, portanto, deve formalizar uma política de **comparabilidade permitida** e outra de **comparabilidade proibida**, para evitar distorções no score.

## 7. Plano de trabalho proposto para o projeto

A melhor forma de conduzir o projeto é por trilhas sequenciais, com critérios claros de entrada e saída. Como o objetivo ainda está em planejamento, as fases abaixo foram desenhadas para orientar a pesquisa e a construção metodológica do framework, sem qualquer pressuposto de implementação tecnológica.

| Fase | Objetivo principal | Entregável de planejamento | Critério de conclusão |
|---|---|---|---|
| 1. Enquadramento metodológico | Definir escopo, universo e comparabilidade | Documento de premissas analíticas | Famílias, buckets e benchmarks aprovados |
| 2. Auditoria e padronização da base | Formalizar regras de limpeza e consistência | Dicionário de dados e protocolo de validação | Base auditável e segmentada |
| 3. Engenharia de variáveis | Definir fatores econômicos do framework | Catálogo de features por família | Features priorizadas e justificadas |
| 4. Modelagem da curva | Estabelecer referência de valor justo | Documento de curvas nominais e reais | Método-base de curva selecionado |
| 5. Construção do score | Integrar retorno, valor relativo, risco e liquidez | Matriz de score com pesos candidatos | Versões candidatas definidas |
| 6. Validação estatística | Testar robustez temporal e sensibilidade | Protocolo de validação e métricas de desempenho | Critérios de aceitação definidos |
| 7. Governança e revisão | Formalizar revisão de pesos e regras | Política metodológica do framework | Processo de revisão documentado |

Cada uma dessas fases deve ser tratada como uma unidade de decisão. Em outras palavras, o projeto não deve avançar para a etapa seguinte sem consolidar formalmente as premissas da etapa anterior. Essa disciplina é especialmente importante porque, em renda fixa, um erro de convenção ou de comparabilidade pode contaminar todas as interpretações posteriores.

## 8. Critérios de sucesso do projeto na ótica de planejamento

O sucesso do projeto não deve ser medido apenas pela capacidade de gerar um ranking de títulos. O verdadeiro critério de sucesso é a capacidade de produzir um ranking que seja **economicamente explicável, estatisticamente estável e metodologicamente auditável**. Portanto, a fase de planejamento deve fixar critérios objetivos para avaliar a qualidade futura do framework.

| Dimensão de sucesso | Critério recomendado |
|---|---|
| Coerência econômica | O score precisa respeitar estrutura de fluxo, indexação e risco de taxa |
| Estabilidade estatística | O ranking não deve mudar de forma errática sob pequenas alterações de input |
| Robustez temporal | Os sinais devem manter poder informacional em diferentes janelas históricas |
| Interpretabilidade | Cada componente do score deve ter significado econômico claro |
| Governança | Mudanças de pesos e regras devem ser documentadas e justificadas |
| Aderência a mercado | O framework deve ser compatível com princípios de marcação a mercado e curva [3] |
| Reprodutibilidade | O processo analítico deve poder ser reexecutado com o mesmo resultado metodológico |

## 9. Riscos metodológicos já identificados

O planejamento também precisa explicitar os riscos mais prováveis. O primeiro risco é o de comparar títulos estruturalmente distintos como se fossem equivalentes. O segundo é o de confundir alta taxa com alta oportunidade, sem descontar o risco implícito no prazo e na convexidade. O terceiro é o de construir um score excessivamente sensível a outliers de mercado ou a mudanças de convenção. O quarto é o de superestimar a utilidade de liquidez observada a partir de dados limitados a preço e taxa. O quinto é o de misturar indevidamente informações de mercado primário, secundário e dados de distribuição do Tesouro Direto.

| Risco metodológico | Efeito potencial | Mitigação recomendada |
|---|---|---|
| Comparabilidade inadequada | Ranking enviesado entre famílias | Segmentar por família, indexador e fluxo |
| Viés de duration longa | Score favorece títulos mais voláteis | Ajustar por risco de taxa antes do ranking final |
| Outliers de taxa ou PU | Falsos sinais de oportunidade | Filtros estatísticos e revisão de consistência [3] |
| Peso arbitrário dos fatores | Instabilidade metodológica | Sensibilidade formal de pesos e governança de revisão |
| Curva mal ajustada | Resíduos sem interpretação econômica | Validar modelos simples e paramétricos em paralelo |
| Mudança estrutural de regime | Quebra de desempenho do score | Validação por subperíodos e ambientes macroeconômicos |

## 10. Recomendação final para a fase atual

A recomendação para a fase atual é concentrar o projeto em três decisões centrais. A primeira é formalizar a **taxonomia analítica** dos títulos, estabelecendo com precisão quais comparações são válidas. A segunda é definir o **framework-base de oportunidade** como uma combinação entre carry, valor relativo na curva, liquidez e ajuste por risco, preservando a fórmula inicial apenas como hipótese a ser validada. A terceira é estruturar um **protocolo de validação estatística** antes de qualquer avanço operacional, garantindo que o projeto não confunda um ranking visualmente atraente com uma metodologia realmente robusta.

Em síntese, o material enviado pelo usuário é suficiente para sustentar um planejamento sério e bem fundamentado. A base histórica é rica, as fontes oficiais são adequadas para auditoria metodológica, e as referências de mercado apontam com clareza para uma arquitetura analítica centrada em **curva, valor relativo, risco e governança** [1] [2] [3]. Assim, a próxima etapa natural do projeto, ainda dentro do ciclo analítico e sem desenvolvimento de sistema, é transformar este plano em um **documento metodológico operacional**, detalhando fórmulas candidatas, políticas de segmentação, critérios de validação e cronograma de revisão.

## Referências

[1]: https://vlab.stern.nyu.edu/docs/fixedIncome "V-Lab: Fixed Income Analysis Documentation"
[2]: https://www.tesourodireto.com.br/produtos/dados-sobre-titulos/historico-de-precos-e-taxas "Histórico de Preços e Taxas - Tesouro Direto"
[3]: https://www.anbima.com.br/data/files/A0/02/CC/70/8FEFC8104606BDC8B82BA2A8/Metodologias%20ANBIMA%20de%20Precificacao%20Titulos%20Publicos.pdf "Metodologia ANBIMA de Precificação de Títulos Públicos Federais"
