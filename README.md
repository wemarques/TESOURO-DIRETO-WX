# 🏛️ Tesouro Direto WX

Sistema analítico para identificação de oportunidades de investimento em títulos do **Tesouro Direto brasileiro**.

## O que faz

Consome dados históricos oficiais de preços e taxas do Tesouro Direto, aplica um framework quantitativo de scoring multifatorial e entrega resultados via dashboard interativo.

**Oportunidade ≠ taxa mais alta.** O sistema avalia cada título por carry, valor relativo na curva, liquidez e risco de taxa — sempre comparando dentro da mesma família e faixa de prazo.

## Stack

- **Python 3.12+** — Motor analítico
- **Pandas** — Processamento de dados
- **Plotly/Dash** — Dashboard interativo
- **Git** — Versionamento

## Estrutura

```
├── docs/           # Documentação metodológica
├── data/           # Dados (raw → interim → processed → outputs)
├── src/            # Código-fonte
│   ├── ingestao/   # Pipeline de ingestão CSV
│   ├── transformacao/  # Padronização e enriquecimento
│   ├── analytics/  # Curvas, métricas, scores, rankings
│   └── dashboard/  # Interface visual
├── tests/          # Testes automatizados
└── scripts/        # Scripts operacionais
```

## Fontes de dados

| Fonte | Tipo |
|---|---|
| [Tesouro Transparente (CKAN)](https://www.tesourotransparente.gov.br/ckan/organization/codip) | Primária |
| [Tesouro Direto — Histórico](https://www.tesourodireto.com.br/produtos/dados-sobre-titulos/historico-de-precos-e-taxas) | Conferência |
| [ANBIMA — Precificação](https://www.anbima.com.br/data/files/A0/02/CC/70/8FEFC8104606BDC8B82BA2A8/Metodologias%20ANBIMA%20de%20Precificacao%20Titulos%20Publicos.pdf) | Metodológica |

## Setup rápido

```bash
# Clonar
git clone https://github.com/wemarques/TESOURO-DIRETO-WX.git
cd TESOURO-DIRETO-WX

# Instalar dependências
pip install -e .

# Rodar pipeline de ingestão
python scripts/rodar_ingestao.py

# Rodar dashboard
python -m src.dashboard.app
```

## Status

🚧 Em desenvolvimento — Fase 1 (Fundação)

## Licença

Projeto pessoal de análise. Dados públicos do Tesouro Nacional.
