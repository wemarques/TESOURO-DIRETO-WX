# Notas de pesquisa para o planejamento do projeto Tesouro Direto

## Fonte 1
- **Título:** V-Lab: Fixed Income Analysis Documentation
- **URL:** https://vlab.stern.nyu.edu/docs/fixedIncome

## Achados principais relevantes ao projeto

1. **Relação preço-yield inversa** deve ser tratada como fundamento central do modelo analítico, pois oportunidades em renda fixa decorrem de desalinhamentos entre preço e taxa observada na curva.
2. **Duration e convexidade** são métricas essenciais para quantificar sensibilidade do preço a movimentos de juros; devem entrar como métricas de risco, mesmo que não componham inicialmente o score principal.
3. **Yield curve / estrutura a termo** deve ser um eixo analítico do projeto, pois o formato da curva contém informação econômica e de valor relativo entre vértices.
4. **Key rate duration e DV01** são métricas úteis para fase posterior de robustez do framework, sobretudo para comparar risco entre títulos de diferentes vencimentos.
5. **Modelos paramétricos de curva, como Nelson-Siegel-Svensson**, são prática reconhecida para modelagem parsimoniosa dos fatores de nível, inclinação e curvatura da curva de juros.
6. Em gestão profissional de renda fixa, o processo de análise combina **retorno esperado, risco de taxa e posicionamento na curva**, não apenas taxa bruta observada.

## Implicações para o plano de trabalho

- Incluir uma trilha específica de **engenharia de features de renda fixa** com duration, convexidade, slope, curvature e measures de carry/rolldown.
- Separar no planejamento os blocos de **detecção de oportunidade** e **controle de risco**, para evitar ranking enviesado por maturidade longa.
- Prever uma etapa de comparação entre **métodos simples de score** e **modelos baseados em curva ajustada**.
- Recomendar que a oportunidade seja definida por combinação de **carry, valor relativo na curva, liquidez e ajuste por risco**.

## Fonte 2
- **Título:** Histórico de Preços e Taxas - Tesouro Direto
- **URL:** https://www.tesourodireto.com.br/produtos/dados-sobre-titulos/historico-de-precos-e-taxas

## Achados principais relevantes ao projeto

1. O site oficial disponibiliza **históricos anuais por família de título** (LFT, LTN, NTN-B, NTN-B Principal, NTN-C, NTN-F, Tesouro Educa+ e Tesouro Renda+), o que reforça a confiabilidade e a rastreabilidade da base usada no projeto.
2. A organização por tipo de papel confirma a necessidade de tratar o universo de títulos em **subgrupos homogêneos**, evitando comparar diretamente taxas de instrumentos com estruturas de fluxo distintas.
3. A existência de séries de **preços unitários e taxas históricas** sustenta a construção de métricas de oportunidade baseadas em comportamento relativo no tempo, não apenas em snapshot estático.
4. A fonte é apropriada para uma camada de ingestão oficial e para auditoria metodológica do projeto, mas não elimina a necessidade de padronização de convenções analíticas entre famílias de títulos.

## Implicações para o plano de trabalho

- Incluir no planejamento uma etapa formal de **normalização por família de título**.
- Prever testes de consistência entre **taxa, PU e prazo até vencimento** por tipo de instrumento.
- Separar no framework analítico os blocos de **títulos nominais, indexados à inflação, pós-fixados e produtos com finalidade previdenciária/educacional**.
- Definir política de atualização da base e governança de dados com prioridade para **fontes oficiais**.
