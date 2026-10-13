"""Callbacks de interatividade do dashboard."""

import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, html, no_update

from src.analytics.duration import TIPOS_IPCA, TIPOS_NOMINAIS, decompor_retorno
from src.analytics.simulador import matriz_cenarios, proximo_degrau_ir, simular
from src.analytics.tese import avaliar_condicoes

# Importacao registra o template plotly 'tdwx_dark' como padrao
from src.dashboard import plotly_theme  # noqa: F401
from src.dashboard.dados import (
    EstadoDados,
    build_summary_stats,
)
from src.dashboard.layouts import NOMES_FAMILIA, summary_row_from_stats
from src.dashboard.plotly_theme import CORES_FAMILIA
from src.utils.constants import IPCA_ATUAL, SELIC_META_REF
from src.utils.nomes import nome_curto

MAPA_INDEXADOR = {
    "Tesouro Selic": "Selic",
    "Tesouro Prefixado": "Prefixado",
    "Tesouro Prefixado com Juros Semestrais": "Prefixado",
    "Tesouro IPCA+": "IPCA",
    "Tesouro IPCA+ com Juros Semestrais": "IPCA",
    "Tesouro IGPM+ com Juros Semestrais": "IGP-M",
    "Tesouro Educa+": "IPCA",
    "Tesouro Renda+ Aposentadoria Extra": "IPCA",
}


# =============================================================================
# HELPERS
# =============================================================================

def _formatar_pp(v: float) -> str:
    """Formata variacao em pontos percentuais. Ex: '+0.50 pp' ou '-0.30 pp'."""
    if pd.isna(v):
        return "—"
    return f"{v:+.2f} pp"


def _formatar_moeda(v: float) -> str:
    """Formata valor como moeda BRL."""
    if pd.isna(v):
        return "—"
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _formatar_pct(v: float) -> str:
    """Fracao como percentual com sinal. Ex: 0.544 -> '+54,4%'."""
    if pd.isna(v):
        return "—"
    return f"{v * 100:+.1f}%".replace(".", ",")


COLS_RISCO_RANKING = [
    "duration_macaulay", "duration_modificada", "convexidade",
    "var_pct_taxa_menos_1pp", "var_pct_taxa_mais_1pp", "inflacao_implicita",
]


def _info_row(label: str, value: str) -> html.Div:
    """Linha de informacao para o card de titulo (estilo dark)."""
    return html.Div(
        [
            html.Span(label, className="tdwx-info-label"),
            html.Span(value, className="tdwx-info-value"),
        ],
        className="tdwx-info-row",
    )


def _stat_card(label: str, value: str, variant: str = "") -> html.Div:
    """Card pequeno de estatistica (estilo dark)."""
    return html.Div(
        [
            html.Div(label, className="tdwx-stat-label"),
            html.Div(value, className=f"tdwx-stat-value {variant}"),
        ],
        className="tdwx-stat-card",
    )


def _leitura_dupla_12m(tipo: str, df_full, df_12m_atras, ultimo) -> html.Div:
    """As duas faces da variacao de taxa em 12 meses: quem ja tinha x quem entra hoje.

    Usa ``decompor_retorno``: separa a variacao do PU em efeito-taxa (marcacao a
    mercado) e carrego/indexacao. Cupons/parcelas pagos no periodo entram no
    retorno de quem ja tinha o titulo.
    """
    if df_12m_atras.empty or "pu_compra_manha" not in df_full.columns:
        return html.P("Sem dado de 12 meses atrás", className="tdwx-sim-note")
    antigo = df_12m_atras.iloc[-1]
    try:
        d = decompor_retorno(
            tipo,
            ultimo["data_vencimento"],
            antigo["data_base"],
            float(antigo["taxa_compra_manha"]),
            float(antigo["pu_compra_manha"]),
            ultimo["data_base"],
            float(ultimo["taxa_compra_manha"]),
            float(ultimo["pu_compra_manha"]),
        )
    except (ValueError, KeyError, ZeroDivisionError):
        return html.Div()

    pp = d["delta_taxa_pp"]
    efeito = d["efeito_taxa"]
    if abs(pp) < 0.005:
        return html.P(
            "Taxa praticamente estável em 12 meses: o preço variou só pelo carrego.",
            className="tdwx-sim-note",
        )
    taxa_caiu = pp < 0
    nota_fluxo = (
        f" Inclui {_formatar_moeda(d['fluxos_recebidos'])} em cupons/parcelas recebidos."
        if d.get("fluxos_recebidos", 0) > 0 else ""
    )
    quem_tinha = html.Div(
        [
            html.Div("Quem já tinha o título", className="tdwx-leitura-titulo"),
            html.Div(
                _formatar_pct(d["retorno_total"]) + " em 12 meses",
                className="tdwx-leitura-valor",
            ),
            html.Div(
                f"{_formatar_pct(efeito)} vieram da {'queda' if taxa_caiu else 'alta'} de "
                f"{abs(pp):.2f} p.p. na taxa (marcação a mercado) e "
                f"{_formatar_pct(d['carrego_indexacao'])} do carrego"
                f"{' + indexador' if tipo not in TIPOS_NOMINAIS else ''}.{nota_fluxo}",
                className="tdwx-leitura-texto",
            ),
        ],
        className=f"tdwx-leitura {'ganho' if efeito >= 0 else 'perda'}",
    )
    quem_entra = html.Div(
        [
            html.Div("Quem entra hoje", className="tdwx-leitura-titulo"),
            html.Div(
                f"paga {_formatar_pct(efeito).lstrip('+-')} {'a mais' if taxa_caiu else 'a menos'}",
                className="tdwx-leitura-valor",
            ),
            html.Div(
                (
                    "do que pagaria com a taxa de 12 meses atrás, e trava uma taxa menor "
                    "até o vencimento. Só ganha com marcação se a taxa cair ainda mais."
                )
                if taxa_caiu
                else (
                    "do que pagaria com a taxa de 12 meses atrás, e trava uma taxa maior "
                    "até o vencimento. Se a taxa voltar a cair, ganha com a marcação."
                ),
                className="tdwx-leitura-texto",
            ),
        ],
        className=f"tdwx-leitura {'perda' if taxa_caiu else 'ganho'}",
    )
    return html.Div([quem_tinha, quem_entra], className="tdwx-leitura-dupla")



# =============================================================================
# LOGICA DA CALCULADORA - CASCATA DE FALLBACK
# =============================================================================

BUCKETS_ORDER = ["CURTO", "INTER", "LONGO", "ULTRA"]

# Mapeamento objetivo -> familias permitidas, buckets ideais e prazo minimo.
# prazo_min_anos vale em todos os niveis da cascata (inclusive quando os buckets
# sao expandidos): um titulo de 3 meses nao atende "medio prazo (2-5 anos)".
MAPA_OBJETIVO = {
    "reserva": {
        "familias": ["SELIC"],
        "buckets": ["CURTO", "INTER", "LONGO", "ULTRA"],
        "prazo_min_anos": 0.0,
    },
    "curto": {
        "familias": ["SELIC", "PRE"],
        "buckets": ["CURTO"],
        "prazo_min_anos": 0.0,
    },
    "medio": {
        "familias": ["PRE", "PRE_JS", "IPCA", "IPCA_JS"],
        "buckets": ["INTER"],
        "prazo_min_anos": 2.0,
    },
    "longo": {
        "familias": ["IPCA", "IPCA_JS", "PRE_JS"],
        "buckets": ["LONGO", "INTER"],
        "prazo_min_anos": 5.0,
    },
    "aposentadoria": {
        "familias": ["IPCA", "IPCA_JS", "RENDA", "EDUCA"],
        "buckets": ["ULTRA", "LONGO"],
        "prazo_min_anos": 15.0,
    },
}

# Mapeamento perfil de risco -> coluna de score
MAPA_PERFIL_SCORE = {
    "conservador": "score_b",
    "moderado": "score_a",
    "arrojado": "score_c",
}

# Familias com cupom semestral
FAMILIAS_COM_CUPOM = {"PRE_JS", "IPCA_JS", "IGPM_JS"}

# Mapeamento familia -> grupo amplo (nominal/real/pos_fixado)
GRUPOS_AMPLOS = {
    "SELIC": "pos_fixado",
    "PRE": "nominal",
    "PRE_JS": "nominal",
    "IPCA": "real",
    "IPCA_JS": "real",
    "IGPM_JS": "real",
    "EDUCA": "real",
    "RENDA": "real",
}


def _expandir_buckets(buckets: list[str]) -> list[str]:
    """Adiciona buckets adjacentes a uma lista existente."""
    expandido = set(buckets)
    for b in buckets:
        if b in BUCKETS_ORDER:
            i = BUCKETS_ORDER.index(b)
            if i > 0:
                expandido.add(BUCKETS_ORDER[i - 1])
            if i < len(BUCKETS_ORDER) - 1:
                expandido.add(BUCKETS_ORDER[i + 1])
    return list(expandido)


def _gerar_explicacao(melhor: pd.Series) -> str:
    """Gera frase explicativa baseada nos atributos do titulo."""
    razoes = []
    if pd.notna(melhor.get("carry")) and melhor.get("carry", 0) > 0.05:
        razoes.append("carry alto")
    if pd.notna(melhor.get("rv_zscore")) and melhor.get("rv_zscore", 0) > 0:
        razoes.append("posicao favoravel na curva")
    if pd.notna(melhor.get("liquidez_norm")) and melhor.get("liquidez_norm", 0) > 0.7:
        razoes.append("boa liquidez")
    if not razoes:
        razoes = ["a melhor combinacao de fatores disponivel"]

    grupo = melhor.get("grupo_analitico", "?")
    return (
        f"Este titulo oferece {' e '.join(razoes)} dentro do grupo {grupo}."
    )


def _ordenar_e_montar(
    df: pd.DataFrame, score_col: str, badge: str | None,
) -> tuple[pd.Series, pd.DataFrame, str, str, str | None]:
    """Ordena o DataFrame pelo score e retorna o resultado padronizado."""
    df = df.copy()
    if score_col in df.columns and df[score_col].isna().any():
        df_ord = df.sort_values(
            [score_col, "score_a"],
            ascending=[False, False],
            na_position="last",
        )
    else:
        df_ord = df.sort_values(score_col, ascending=False)

    df_ord = df_ord.reset_index(drop=True)
    melhor = df_ord.iloc[0]
    alternativas = df_ord.head(4)  # melhor + ate 3 alternativas
    explicacao = _gerar_explicacao(melhor)
    return melhor, alternativas, score_col, explicacao, badge


def recomendar_titulo(
    objetivo: str,
    perfil_risco: str,
    renda_periodica: str,
    df_ranking: pd.DataFrame,
) -> tuple[pd.Series, pd.DataFrame, str, str, str | None]:
    """Recomenda um titulo com cascata de fallback que SEMPRE retorna resultado.

    Returns:
        (melhor, alternativas, score_col, explicacao, badge_fallback)
    """
    config = MAPA_OBJETIVO.get(objetivo, MAPA_OBJETIVO["medio"])
    familias = config["familias"]
    buckets = config["buckets"]
    prazo_min = config.get("prazo_min_anos", 0.0)

    score_col = MAPA_PERFIL_SCORE.get(perfil_risco, "score_a")
    # Se score_c selecionado mas todos NaN, usar score_a
    if score_col == "score_c" and (
        "score_c" not in df_ranking.columns or df_ranking["score_c"].isna().all()
    ):
        score_col = "score_a"

    # So titulos disponiveis para COMPRA entram na sugestao (todos os niveis).
    # Sem a coluna (lista oficial ausente), mantem o comportamento anterior.
    if "disponivel_compra" in df_ranking.columns:
        df_disponiveis = df_ranking[df_ranking["disponivel_compra"].fillna(False).astype(bool)]
        if not df_disponiveis.empty:
            df_ranking = df_disponiveis

    df_base = df_ranking.copy()
    if prazo_min > 0 and "anos_ate_vencimento" in df_base.columns:
        df_base = df_base[df_base["anos_ate_vencimento"] >= prazo_min]
    badge_fallback: str | None = None

    # Filtro de cupom (com fallback se zerar)
    if renda_periodica == "sim":
        df_cupom = df_base[df_base["familia_normalizada"].isin(FAMILIAS_COM_CUPOM)]
        df_teste = df_cupom[
            df_cupom["familia_normalizada"].isin(familias)
            & df_cupom["bucket_prazo"].isin(buckets)
        ]
        if df_teste.empty:
            badge_fallback = (
                "Nao ha titulos com juros semestrais para esse objetivo. "
                "Mostrando melhor opcao sem cupom."
            )
        else:
            df_base = df_cupom

    # Nivel 1: familias + buckets ideais
    df_n1 = df_base[
        df_base["familia_normalizada"].isin(familias)
        & df_base["bucket_prazo"].isin(buckets)
    ]
    if not df_n1.empty:
        return _ordenar_e_montar(df_n1, score_col, badge_fallback)

    # Nivel 2: familias + buckets adjacentes
    buckets_exp = _expandir_buckets(buckets)
    df_n2 = df_base[
        df_base["familia_normalizada"].isin(familias)
        & df_base["bucket_prazo"].isin(buckets_exp)
    ]
    if not df_n2.empty:
        if badge_fallback is None:
            badge_fallback = (
                f"Buckets ideais sem opcoes. Expandindo para "
                f"{', '.join(sorted(set(buckets_exp) - set(buckets)))}."
            )
        return _ordenar_e_montar(df_n2, score_col, badge_fallback)

    # Nivel 3: grupo analitico amplo (nominal / real / pos_fixado)
    grupos_alvo = {GRUPOS_AMPLOS.get(f, "real") for f in familias}
    familias_grupo = [f for f, g in GRUPOS_AMPLOS.items() if g in grupos_alvo]
    df_n3 = df_base[df_base["familia_normalizada"].isin(familias_grupo)]
    if not df_n3.empty:
        if badge_fallback is None:
            badge_fallback = (
                f"Filtros restritivos demais. Mostrando todo o grupo "
                f"{'/'.join(sorted(grupos_alvo))}."
            )
        return _ordenar_e_montar(df_n3, score_col, badge_fallback)

    # Nivel 4: melhor titulo geral
    badge_fallback = (
        "Nenhum titulo se encaixa perfeitamente no perfil. "
        "Esta e a melhor oportunidade geral do dia."
    )
    return _ordenar_e_montar(df_ranking, score_col, badge_fallback)


# Compatibilidade: alias para chamadas legadas
selecionar_titulo_calculadora = recomendar_titulo


# =============================================================================
# REGISTRAR CALLBACKS
# =============================================================================

def registrar_callbacks(app, estado: EstadoDados):
    """Registra todos os callbacks no app Dash."""

    SCORE_LABELS = {
        "score_a": "Score A (base)",
        "score_b": "Score B (risco)",
        "score_c": "Score C (curva)",
    }

    TOOLTIPS_COLUNAS = {
        "tipo_titulo": "Nome da familia do titulo do Tesouro Direto",
        "titulo_label": (
            "Nome curto no padrao do Tesouro Direto. No Renda+ e no Educa+ o ano e o "
            "inicio dos pagamentos, nao o vencimento (ex.: Renda+ 2065 vence em 2084)."
        ),
        "indexador": (
            "Indice ao qual o rendimento esta atrelado. "
            "Prefixado = taxa fixa. Selic/IPCA/IGP-M = taxa + variacao do indice"
        ),
        "data_vencimento": "Data em que o titulo expira e o governo paga o valor de face",
        "bucket_prazo": (
            "Faixa de prazo - Curto (<=2a), Intermediario (2-5a), "
            "Longo (5-15a), Ultralongo (>15a)"
        ),
        "taxa_compra_manha": (
            "Taxa anual que o investidor recebe se comprar e segurar ate o vencimento"
        ),
        "taxa_pp_12m_str": (
            "Variacao da taxa em pontos percentuais (pp) nos ultimos 12 meses. "
            "Em renda fixa: taxa subindo = preco caindo = oportunidade para "
            "quem quer comprar. Taxa caindo = preco subindo = bom para quem ja tem."
        ),
        "pu_compra_str": "Preco unitario de compra atual em reais",
        "carry": (
            "Quanto esse titulo paga acima da mediana do seu grupo. "
            "Positivo = acima da media dos pares"
        ),
        "rv_zscore": (
            "Valor Relativo - quantos desvios-padrao a taxa esta acima ou abaixo "
            "da media do grupo. Quanto maior, mais atrativo"
        ),
        "liquidez_norm": (
            "Facilidade de compra/venda, baseada no spread. "
            "Perto de 1 = facil de negociar, perto de 0 = dificil"
        ),
        "score_a": (
            "Nota de oportunidade (0 a 1) combinando "
            "Carry 40% + Valor Relativo 40% + Liquidez 20%"
        ),
        "score_b": (
            "Nota ajustada por risco (0 a 1) - penaliza titulos com prazo muito longo. "
            "Carry 35% + RV 30% + Liquidez 15% + Risco 20%"
        ),
        "score_c": (
            "Nota por residuo de curva NSS (0 a 1) - identifica titulos que pagam "
            "mais que a curva teorica sugere. Carry 30% + Residuo 40% + Rolldown 15% + Liquidez 15%"
        ),
        "posicao_celula": (
            "Posicao do titulo no ranking dentro do seu grupo comparavel (familia + prazo)"
        ),
        "posicao_global": (
            "Posicao no ranking geral - apenas informativo, "
            "nao use para decisao entre familias diferentes"
        ),
        "duration_macaulay": (
            "Duration de Macaulay: prazo medio ponderado dos fluxos (cupons, parcelas "
            "e principal), em anos. Nao e o prazo ate o vencimento: no Renda+ e no "
            "Educa+ os pagamentos sao mensais e a duration fica bem abaixo do vencimento."
        ),
        "duration_modificada": (
            "Quanto o preco varia, em %, para cada 1 p.p. de mudanca na taxa (1a ordem). "
            "No Tesouro Selic mede a sensibilidade ao spread, nao a Selic: o risco de "
            "juros do Selic e praticamente zero."
        ),
        "convexidade": (
            "Correcao de 2a ordem: quanto maior, mais o ganho numa queda de taxa supera "
            "a perda numa alta do mesmo tamanho. dPU/PU = -MD*di + 1/2*C*di^2"
        ),
        "var_menos_1pp_str": (
            "Variacao exata do preco se a taxa cair 1 p.p. hoje (reprecificacao do "
            "fluxo, ja com convexidade). E o ganho de marcacao a mercado de quem tem o titulo."
        ),
        "var_mais_1pp_str": (
            "Variacao exata do preco se a taxa subir 1 p.p. hoje. Duration alta e faca "
            "de dois gumes: o mesmo titulo que mais ganha na queda e o que mais perde na alta."
        ),
        "inflacao_implicita_str": (
            "Inflacao implicita (Fisher) = (1 + taxa prefixada) / (1 + taxa real) - 1, "
            "com a prefixada interpolada na mesma duration. Se o IPCA medio ficar acima "
            "disso, o IPCA+ rende mais que o prefixado. So e calculada dentro do alcance "
            "da curva prefixada (ate ~6 anos)."
        ),
        "disponivel_str": (
            "Se o titulo esta disponivel para compra hoje no Tesouro Direto. "
            "'So resgate' = continua sendo negociado apenas para quem ja tem. "
            "Fonte: lista oficial em config/titulos_ofertados.csv"
        ),
        "celula_pequena_str": (
            "Marca titulos cuja celula analitica tem menos de 3 observacoes. "
            "Os scores ainda sao calculados, mas a comparacao tem menos "
            "robustez estatistica. Linha exibida em italico/cinza."
        ),
    }

    # =========================================================================
    # RECARGA DE DADOS (cron / parquet atualizado em disco)
    # =========================================================================

    @app.callback(
        Output("dados-meta-store", "data"),
        Output("tdwx-status-bar", "children"),
        Input("reload-dados-interval", "n_intervals"),
        prevent_initial_call=False,
    )
    def recarregar_dados_periodico(_n: int):
        from src.dashboard.layouts import status_bar

        try:
            estado.recarregar()
        except Exception as exc:
            print(f"[dashboard] Falha ao recarregar dados: {exc}")
        return estado.meta(), status_bar(
            estado.data_atualizacao,
            estado.total_titulos,
            estado.total_registros,
            estado.info_ingestao,
            versao_metodologia=estado.versao_metodologia,
            carregado_em=estado.carregado_em,
        )

    # =========================================================================
    # RANKING
    # =========================================================================

    @app.callback(
        Output("ranking-summary-row", "children"),
        Input("ranking-familia-dropdown", "value"),
        Input("ranking-score-dropdown", "value"),
        Input("dados-meta-store", "data"),
    )
    def atualizar_summary_cards(familia: str, score_col: str, _meta: dict | None):
        if not familia:
            familia = "TODAS"
        if not score_col:
            score_col = "score_a"
        stats = build_summary_stats(estado.df_ranking, familia, score_col)
        return summary_row_from_stats(stats, familia)

    @app.callback(
        Output("ranking-bar-chart", "figure"),
        Output("ranking-tabela", "data"),
        Output("ranking-tabela", "columns"),
        Output("ranking-tabela", "tooltip_header"),
        Input("ranking-score-dropdown", "value"),
        Input("ranking-familia-dropdown", "value"),
        Input("ranking-ordenar-dropdown", "value"),
    )
    def atualizar_ranking(score_col: str, familia: str, ordenar_por: str):
        if not score_col or not familia or not ordenar_por:
            return no_update, no_update, no_update, no_update
        df = estado.df_ranking.copy()
        if familia != "TODAS":
            df = df[df["familia_normalizada"] == familia]

        # Colunas de risco (v1.1.0) podem faltar ate o pipeline rodar de novo
        for col in COLS_RISCO_RANKING:
            if col not in df.columns:
                df[col] = float("nan")

        col_ordenar = score_col if ordenar_por == "score" else ordenar_por
        if col_ordenar not in df.columns:
            col_ordenar = score_col
        df = df.sort_values(col_ordenar, ascending=False, na_position="last")

        df["titulo_label"] = [
            nome_curto(t, v) for t, v in zip(df["tipo_titulo"], df["data_vencimento"])
        ]

        score_label = SCORE_LABELS.get(score_col, score_col)
        fig = px.bar(
            df,
            x="titulo_label",
            y=score_col,
            color="familia_normalizada",
            color_discrete_map=CORES_FAMILIA,
            labels={
                "titulo_label": "",
                score_col: score_label,
                "familia_normalizada": "",
            },
            title=f"{score_label} por título",
        )
        fig.update_layout(
            xaxis_tickangle=-45,
            height=460,
            margin=dict(b=140, t=60),
            template="tdwx_dark",
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.45, x=0),
        )
        fig.update_traces(marker_line_width=0)

        # Colunas derivadas para apresentacao
        df["indexador"] = df["tipo_titulo"].map(MAPA_INDEXADOR).fillna("-")
        df["taxa_pp_12m_str"] = df["taxa_pp_12m"].apply(_formatar_pp)
        df["pu_compra_str"] = df["pu_compra_atual"].apply(_formatar_moeda)
        if "celula_pequena" in df.columns:
            df["celula_pequena_str"] = df["celula_pequena"].map(
                {True: "✓", False: ""}
            ).fillna("")
        else:
            df["celula_pequena_str"] = ""
        if "disponivel_compra" in df.columns:
            df["disponivel_str"] = df["disponivel_compra"].map(
                {True: "Sim", False: "Só resgate"}
            ).fillna("—")
        else:
            df["disponivel_str"] = "—"

        df["var_menos_1pp_str"] = df["var_pct_taxa_menos_1pp"].apply(_formatar_pct)
        df["var_mais_1pp_str"] = df["var_pct_taxa_mais_1pp"].apply(_formatar_pct)
        df["inflacao_implicita_str"] = df["inflacao_implicita"].apply(
            lambda v: "—" if pd.isna(v) else f"{v:.2f}%"
        )

        colunas_tabela = [
            ("titulo_label", "Titulo"),
            ("disponivel_str", "À venda"),
            ("indexador", "Indexador"),
            ("data_vencimento", "Vencimento"),
            ("bucket_prazo", "Bucket"),
            ("taxa_compra_manha", "Taxa Compra (%)"),
            ("taxa_pp_12m_str", "Taxa 12M (pp)"),
            ("pu_compra_str", "PU Compra"),
            ("carry", "Carry"),
            ("rv_zscore", "RV z-score"),
            ("liquidez_norm", "Liquidez"),
            ("duration_macaulay", "Duration (anos)"),
            ("duration_modificada", "Duration mod."),
            ("convexidade", "Convexidade"),
            ("var_menos_1pp_str", "Δ PU se taxa −1pp"),
            ("var_mais_1pp_str", "Δ PU se taxa +1pp"),
            ("inflacao_implicita_str", "Inflação implícita"),
            (score_col, score_label),
            ("posicao_celula", "Pos. Celula"),
            ("posicao_global", "Pos. Global"),
            ("celula_pequena_str", "Amostra pequena"),
        ]
        cols_dash = [{"name": label, "id": col_id} for col_id, label in colunas_tabela]

        tooltip_header = {
            col_id: {"value": TOOLTIPS_COLUNAS.get(col_id, label), "type": "text"}
            for col_id, label in colunas_tabela
        }

        df_tab = df[[c for c, _ in colunas_tabela]].copy()
        df_tab["data_vencimento"] = df_tab["data_vencimento"].dt.strftime("%d/%m/%Y")
        for col in ["taxa_compra_manha", "carry", "rv_zscore", "liquidez_norm", score_col]:
            df_tab[col] = df_tab[col].round(4)
        for col in ["duration_macaulay", "duration_modificada"]:
            df_tab[col] = df_tab[col].round(2)
        df_tab["convexidade"] = df_tab["convexidade"].round(1)

        return fig, df_tab.to_dict("records"), cols_dash, tooltip_header

    # =========================================================================
    # SERIES TEMPORAIS
    # =========================================================================

    @app.callback(
        Output("series-titulos-dropdown", "options"),
        Output("series-titulos-dropdown", "value"),
        Input("series-familia-dropdown", "value"),
    )
    def atualizar_titulos_serie(familia: str):
        df = estado.df_historico[estado.df_historico["familia_normalizada"] == familia]
        titulos = sorted(df["tipo_titulo"].unique())
        venc_map = (
            df.groupby("tipo_titulo")["data_vencimento"]
            .first()
            .dt.strftime("%Y")
            .to_dict()
        )
        opcoes = [
            {"label": f"{t} ({venc_map.get(t, '')})", "value": t}
            for t in titulos
        ]
        default = titulos[:3] if len(titulos) >= 3 else titulos
        return opcoes, default

    @app.callback(
        Output("series-line-chart", "figure"),
        Input("series-titulos-dropdown", "value"),
        Input("series-periodo-dropdown", "value"),
    )
    def atualizar_grafico_series(titulos: list[str] | None, periodo_dias: int):
        if not titulos:
            return go.Figure().update_layout(
                title="Selecione titulos para visualizar",
                template="tdwx_dark",
                height=500,
            )

        df = estado.df_historico[estado.df_historico["tipo_titulo"].isin(titulos)].copy()

        if periodo_dias > 0:
            data_corte = df["data_base"].max() - pd.Timedelta(days=periodo_dias)
            df = df[df["data_base"] >= data_corte]

        df["titulo_label"] = (
            df["tipo_titulo"] + " " + df["data_vencimento"].dt.strftime("%Y")
        )

        fig = px.line(
            df,
            x="data_base",
            y="taxa_compra_manha",
            color="titulo_label",
            labels={
                "data_base": "",
                "taxa_compra_manha": "Taxa Compra (% a.a.)",
                "titulo_label": "",
            },
            title="Evolução da Taxa de Compra",
        )
        fig.update_layout(
            height=500,
            template="tdwx_dark",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=-0.25, x=0),
        )
        fig.update_traces(line=dict(width=2.5))
        return fig

    # =========================================================================
    # CURVA NSS
    # =========================================================================

    @app.callback(
        Output("curva-nss-chart", "figure"),
        Input("curva-grupo-dropdown", "value"),
        Input("curva-opcoes-checklist", "value"),
    )
    def atualizar_curva_nss(grupo: str | None, opcoes: list[str] | None):
        if not grupo or not opcoes:
            return go.Figure().update_layout(
                title="Selecione um grupo analitico",
                template="tdwx_dark",
                height=480,
            )

        from src.analytics.curva import obter_curva_snapshot

        resultado = obter_curva_snapshot(estado.df_historico, grupo)
        fig = go.Figure()

        if resultado is None:
            fig.update_layout(
                title=f"Curva indisponível para {grupo} (pontos insuficientes)",
                template="tdwx_dark",
                height=480,
            )
            return fig

        if "pontos" in opcoes:
            fig.add_trace(go.Scatter(
                x=resultado["prazos_obs"],
                y=resultado["taxas_obs"],
                mode="markers",
                name="Taxas observadas",
                marker=dict(size=12, color="#4DA6FF",
                            line=dict(width=2, color="#1A2736")),
            ))

        if "curva" in opcoes:
            fig.add_trace(go.Scatter(
                x=resultado["prazos_plot"],
                y=resultado["taxas_plot"],
                mode="lines",
                name="Curva NSS",
                line=dict(color="#00D4AA", width=3),
            ))

        params = resultado["params"]
        fig.update_layout(
            title=f"Estrutura a termo — {grupo} (RMSE: {params.rmse:.4f})",
            xaxis_title="Prazo (anos)",
            yaxis_title="Taxa (% a.a.)",
            template="tdwx_dark",
            height=480,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, x=0),
        )
        return fig

    # =========================================================================
    # TITULO INDIVIDUAL
    # =========================================================================

    @app.callback(
        Output("titulo-card-info", "children"),
        Output("titulo-stats-cards", "children"),
        Output("titulo-taxa-chart", "figure"),
        Output("titulo-pu-chart", "figure"),
        Output("titulo-spread-chart", "figure"),
        Input("titulo-dropdown", "value"),
        Input("titulo-periodo-dropdown", "value"),
    )
    def atualizar_titulo_individual(titulo: str | None, periodo_dias: int):
        fig_vazia = go.Figure().update_layout(template="tdwx_dark", height=350)
        if not titulo:
            return html.P("Selecione um título"), html.Div(), fig_vazia, fig_vazia, fig_vazia

        # value pode vir como "tipo||YYYY-MM-DD" (titulo especifico) ou so o tipo (compat)
        if "||" in titulo:
            tipo_sel, venc_sel = titulo.split("||", 1)
            venc_ts = pd.Timestamp(venc_sel)
            mask = (estado.df_historico["tipo_titulo"] == tipo_sel) & (
                estado.df_historico["data_vencimento"] == venc_ts
            )
            titulo_label = f"{tipo_sel} {venc_ts:%d/%m/%Y}"
        else:
            tipo_sel = titulo
            mask = estado.df_historico["tipo_titulo"] == tipo_sel
            titulo_label = tipo_sel

        df_full = estado.df_historico[mask].sort_values("data_base")
        if df_full.empty:
            return html.P("Sem dados"), html.Div(), fig_vazia, fig_vazia, fig_vazia

        ultimo = df_full.iloc[-1]
        data_max = df_full["data_base"].max()

        # 52 semanas (365 dias)
        df_52w = df_full[df_full["data_base"] >= data_max - pd.Timedelta(days=365)]
        # 12 meses para variacao
        df_12m_atras = df_full[df_full["data_base"] <= data_max - pd.Timedelta(days=365)]
        # Mes atual
        primeiro_dia_mes = data_max.replace(day=1)
        df_mes = df_full[df_full["data_base"] >= primeiro_dia_mes]

        # Variacoes
        valorizacao_12m = float("nan")
        if not df_12m_atras.empty and "pu_compra_manha" in df_full.columns:
            pu_antigo = df_12m_atras.iloc[-1]["pu_compra_manha"]
            pu_atual = ultimo["pu_compra_manha"]
            if pu_antigo and pu_antigo > 0:
                valorizacao_12m = ((pu_atual - pu_antigo) / pu_antigo) * 100

        valorizacao_mes = float("nan")
        if len(df_mes) >= 2 and "pu_compra_manha" in df_full.columns:
            pu_inicio = df_mes.iloc[0]["pu_compra_manha"]
            pu_atual = ultimo["pu_compra_manha"]
            if pu_inicio and pu_inicio > 0:
                valorizacao_mes = ((pu_atual - pu_inicio) / pu_inicio) * 100

        # Min/Max 52 semanas
        if "pu_compra_manha" in df_52w.columns:
            pu_min = df_52w["pu_compra_manha"].min()
            pu_max = df_52w["pu_compra_manha"].max()
        else:
            pu_min = pu_max = float("nan")
        taxa_min = df_52w["taxa_compra_manha"].min()
        taxa_max = df_52w["taxa_compra_manha"].max()

        # Comparacao 12 meses (taxa em pp)
        taxa_atual = float(ultimo["taxa_compra_manha"])
        if not df_12m_atras.empty:
            taxa_antiga = float(df_12m_atras.iloc[-1]["taxa_compra_manha"])
        else:
            taxa_antiga = float("nan")
        pp_12m = (
            taxa_atual - taxa_antiga
            if pd.notna(taxa_antiga)
            else float("nan")
        )

        def _fmt_pct(v):
            if pd.isna(v):
                return "—"
            return f"{v:+.2f}%"

        stats_row = html.Div(
            [
                _stat_card("PU Min 52s", _formatar_moeda(pu_min)),
                _stat_card("PU Max 52s", _formatar_moeda(pu_max)),
                _stat_card(
                    "Taxa Min 52s",
                    f"{taxa_min:.2f}%" if pd.notna(taxa_min) else "—",
                ),
                _stat_card(
                    "Taxa Max 52s",
                    f"{taxa_max:.2f}%" if pd.notna(taxa_max) else "—",
                ),
                _stat_card(
                    "Valoriz. 12M",
                    _fmt_pct(valorizacao_12m),
                    "success" if (pd.notna(valorizacao_12m) and valorizacao_12m >= 0) else "danger",
                ),
                _stat_card(
                    "Valoriz. mês",
                    _fmt_pct(valorizacao_mes),
                    "success" if (pd.notna(valorizacao_mes) and valorizacao_mes >= 0) else "danger",
                ),
            ],
            className="tdwx-stats-grid",
        )

        # Card de comparacao 12 meses: variacao de taxa + leitura dupla do efeito no preco
        leitura = _leitura_dupla_12m(tipo_sel, df_full, df_12m_atras, ultimo)

        card_12m = html.Div(
            [
                html.H6("Comparação 12 meses (taxa)", className="tdwx-12m-title"),
                html.Div(
                    [
                        _stat_card(
                            "Taxa há 12 meses",
                            f"{taxa_antiga:.2f}%" if pd.notna(taxa_antiga) else "—",
                        ),
                        _stat_card("Taxa hoje", f"{taxa_atual:.2f}%"),
                        _stat_card(
                            "Variação",
                            _formatar_pp(pp_12m),
                            "warning"
                            if pd.notna(pp_12m) and pp_12m < 0
                            else "success",
                        ),
                    ],
                    className="tdwx-12m-grid",
                ),
                leitura,
            ],
            className="tdwx-12m-card",
        )

        stats_div = html.Div([stats_row, card_12m])

        # Filtrar pelo periodo do grafico
        if periodo_dias and periodo_dias > 0:
            df = df_full[df_full["data_base"] >= data_max - pd.Timedelta(days=periodo_dias)]
        else:
            df = df_full

        # Card de informacoes
        indexador = MAPA_INDEXADOR.get(tipo_sel, "-")
        card_body = html.Div(
            [
                html.H4(titulo_label, className="tdwx-info-title"),
                _info_row("Família", NOMES_FAMILIA.get(
                    str(ultimo["familia_normalizada"]), str(ultimo["familia_normalizada"])
                )),
                _info_row("Indexador", indexador),
                _info_row(
                    "Vencimento",
                    pd.Timestamp(ultimo["data_vencimento"]).strftime("%d/%m/%Y"),
                ),
                _info_row("Prazo", f"{ultimo['anos_ate_vencimento']:.1f} anos"),
                _info_row("Bucket", str(ultimo["bucket_prazo"])),
                _info_row("Taxa compra", f"{ultimo['taxa_compra_manha']:.2f}%"),
                _info_row("Taxa venda", f"{ultimo['taxa_venda_manha']:.2f}%"),
                _info_row("Spread", f"{ultimo['spread_compra_venda']:.4f}"),
                _info_row("PU compra", _formatar_moeda(
                    ultimo.get("pu_compra_manha", float("nan"))
                )),
                _info_row(
                    "IPCA 12 meses",
                    f"{((estado.macro or {}).get('ipca_12m') or {}).get('valor', IPCA_ATUAL):.2f}%",
                ),
            ],
            className="tdwx-info-card",
        )

        # Grafico de taxa
        fig_taxa = px.line(
            df,
            x="data_base",
            y=["taxa_compra_manha", "taxa_venda_manha"],
            labels={"data_base": "", "value": "Taxa (% a.a.)", "variable": ""},
            title="Taxas de compra e venda",
            color_discrete_sequence=["#00D4AA", "#4DA6FF"],
        )
        # Contexto historico: banda min-max + mediana de toda a serie e ponto de hoje
        _taxa_hist = df_full["taxa_compra_manha"].dropna()
        if len(_taxa_hist) >= 5:
            h_min, h_max = float(_taxa_hist.min()), float(_taxa_hist.max())
            h_med = float(_taxa_hist.median())
            pctl = float((_taxa_hist <= taxa_atual).mean() * 100)
            fig_taxa.add_hrect(
                y0=h_min, y1=h_max, fillcolor="rgba(136,153,170,0.06)",
                line_width=0, layer="below",
            )
            fig_taxa.add_hline(
                y=h_med, line_dash="dot", line_color="#8899AA",
                annotation_text=f"mediana hist. {h_med:.2f}%",
                annotation_position="top left",
            )
            fig_taxa.add_scatter(
                x=[data_max], y=[taxa_atual], mode="markers",
                marker=dict(size=11, color="#00D4AA",
                            line=dict(width=2, color="#0F1923")),
                name=f"hoje {taxa_atual:.2f}% (p{pctl:.0f})", hoverinfo="name",
            )
        fig_taxa.update_layout(
            template="tdwx_dark",
            height=380,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, x=0),
        )
        fig_taxa.update_traces(line=dict(width=2.5), selector=dict(mode="lines"))

        # Grafico de PU
        pu_cols = [c for c in ["pu_compra_manha", "pu_venda_manha"] if c in df.columns]
        if pu_cols:
            fig_pu = px.line(
                df,
                x="data_base",
                y=pu_cols,
                labels={"data_base": "", "value": "PU (R$)", "variable": ""},
                title="Preços unitários",
                color_discrete_sequence=["#FFB830", "#FF8C42"],
            )
        else:
            fig_pu = fig_vazia
        fig_pu.update_layout(
            template="tdwx_dark",
            height=380,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, x=0),
        )
        fig_pu.update_traces(line=dict(width=2.5))

        # Grafico de spread (em bps + media movel) — proxy de liquidez
        df_sp = df.copy()
        df_sp["spread_bps"] = df_sp["spread_compra_venda"] * 10000
        df_sp["spread_bps_ma"] = df_sp["spread_bps"].rolling(20, min_periods=1).mean()
        fig_spread = px.area(
            df_sp,
            x="data_base",
            y="spread_bps",
            labels={"data_base": "", "spread_bps": "Spread (bps)"},
            title="Spread compra/venda — proxy de liquidez (menor = mais liquido)",
            color_discrete_sequence=["#A78BFA"],
        )
        if fig_spread.data:
            fig_spread.data[0].fillcolor = "rgba(167, 139, 250, 0.2)"
            fig_spread.data[0].line.width = 2
        fig_spread.add_scatter(
            x=df_sp["data_base"], y=df_sp["spread_bps_ma"], mode="lines",
            line=dict(width=2, color="#FFB830"), name="media movel 20d",
        )
        fig_spread.update_layout(
            template="tdwx_dark", height=380,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, x=0),
        )

        return card_body, stats_div, fig_taxa, fig_pu, fig_spread

    # =========================================================================
    # CALCULADORA
    # =========================================================================

    @app.callback(
        Output("calc-resultado", "children"),
        Input("calc-objetivo-dropdown", "value"),
        Input("calc-oscilacao-radio", "value"),
        Input("calc-renda-radio", "value"),
    )
    def atualizar_calculadora(objetivo: str, perfil: str, renda: str):
        if not objetivo or not perfil or not renda:
            return html.Div()

        melhor, alternativas, score_col, explicacao, badge_fallback = recomendar_titulo(
            objetivo, perfil, renda, estado.df_calculadora,
        )
        score_label = SCORE_LABELS.get(score_col, score_col)

        indexador = MAPA_INDEXADOR.get(str(melhor["tipo_titulo"]), "-")
        venc = pd.Timestamp(melhor["data_vencimento"]).strftime("%d/%m/%Y")
        pu = _formatar_moeda(melhor.get("pu_compra_atual", float("nan")))
        prazo = (
            f"{melhor['anos_ate_vencimento']:.1f} anos"
            if pd.notna(melhor.get("anos_ate_vencimento"))
            else "—"
        )
        pos_cel = (
            int(melhor["posicao_celula"])
            if pd.notna(melhor.get("posicao_celula"))
            else "—"
        )

        # Taxa formatada conforme indexador
        if indexador in ("IPCA", "IGP-M"):
            taxa_display = f"{indexador} + {melhor['taxa_compra_manha']:.2f}% a.a."
        elif indexador == "Selic":
            taxa_display = f"Selic + {melhor['taxa_compra_manha']:.2f}% a.a."
        else:
            taxa_display = f"{melhor['taxa_compra_manha']:.2f}% a.a."

        # Cor do card baseada no grupo amplo
        grupo_amplo = GRUPOS_AMPLOS.get(str(melhor["familia_normalizada"]), "real")
        cor_class = {
            "pos_fixado": "info",
            "nominal": "",
            "real": "warning",
        }.get(grupo_amplo, "")

        # Badge de fallback
        badge_html = (
            html.Div(
                [html.Strong("Nota: "), badge_fallback],
                className="tdwx-fallback-note",
            )
            if badge_fallback
            else None
        )

        card_destaque = html.Div(
            [
                html.Div("Sugestão analítica do dia", className="tdwx-result-badge"),
                html.P(
                    "Melhor score no perfil informado — não é recomendação de investimento",
                    className="tdwx-result-label",
                ),
                html.H2(melhor["tipo_titulo"], className="tdwx-result-title"),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div("Taxa", className="tdwx-result-metric-label"),
                                html.Div(
                                    taxa_display,
                                    className="tdwx-result-metric-value large",
                                ),
                            ],
                            className="tdwx-result-metric",
                        ),
                        html.Div(
                            [
                                html.Div(
                                    "Vencimento",
                                    className="tdwx-result-metric-label",
                                ),
                                html.Div(
                                    venc, className="tdwx-result-metric-value"
                                ),
                                html.Small(
                                    prazo,
                                    style={
                                        "color": "#8899AA",
                                        "fontFamily": "DM Sans",
                                    },
                                ),
                            ],
                            className="tdwx-result-metric",
                        ),
                        html.Div(
                            [
                                html.Div("PU compra", className="tdwx-result-metric-label"),
                                html.Div(pu, className="tdwx-result-metric-value"),
                            ],
                            className="tdwx-result-metric",
                        ),
                        html.Div(
                            [
                                html.Div(score_label, className="tdwx-result-metric-label"),
                                html.Div(
                                    f"{melhor[score_col]:.3f}",
                                    className="tdwx-result-metric-value",
                                ),
                            ],
                            className="tdwx-result-metric",
                        ),
                        html.Div(
                            [
                                html.Div("Pos. no grupo", className="tdwx-result-metric-label"),
                                html.Div(
                                    str(pos_cel), className="tdwx-result-metric-value"
                                ),
                            ],
                            className="tdwx-result-metric",
                        ),
                    ],
                    className="tdwx-result-grid",
                ),
                html.Div(
                    [html.Span("✨ ", style={"marginRight": "4px"}), explicacao],
                    className="tdwx-result-explanation",
                ),
            ],
            className=f"tdwx-result-hero {cor_class}",
        )

        # Tabela de alternativas (excluindo o melhor)
        outras = alternativas.iloc[1:] if len(alternativas) > 1 else pd.DataFrame()
        if not outras.empty:
            alt = outras.copy()
            alt["indexador"] = alt["tipo_titulo"].map(MAPA_INDEXADOR).fillna("-")
            alt["venc_str"] = alt["data_vencimento"].dt.strftime("%d/%m/%Y")
            alt["score_str"] = alt[score_col].map(
                lambda v: f"{v:.3f}" if pd.notna(v) else "—"
            )
            alt["taxa_str"] = alt["taxa_compra_manha"].map(lambda v: f"{v:.2f}%")

            tabela = dbc.Table.from_dataframe(
                alt[[
                    "tipo_titulo", "indexador", "venc_str",
                    "bucket_prazo", "taxa_str", "score_str",
                ]].rename(
                    columns={
                        "tipo_titulo": "Titulo",
                        "indexador": "Indexador",
                        "venc_str": "Vencimento",
                        "bucket_prazo": "Bucket",
                        "taxa_str": "Taxa",
                        "score_str": score_label,
                    }
                ),
                striped=True,
                bordered=True,
                hover=True,
                className="mt-2",
            )
            secao_alternativas = html.Div(
                [
                    html.H5("Outras opcoes para voce", className="mt-3 mb-2"),
                    tabela,
                ]
            )
        else:
            secao_alternativas = html.Div()

        componentes = [c for c in [badge_html, card_destaque, secao_alternativas] if c]
        return html.Div(componentes)

    # =========================================================================
    # SIMULADOR DE MARCACAO A MERCADO (/titulo)
    # =========================================================================

    def _ultimo_registro(titulo: str | None):
        if not titulo or "||" not in titulo:
            return None
        tipo, venc = titulo.split("||", 1)
        h = estado.df_historico
        sel = h[(h["tipo_titulo"] == tipo) & (h["data_vencimento"] == pd.Timestamp(venc))]
        return None if sel.empty else sel.sort_values("data_base").iloc[-1]

    @app.callback(
        Output("sim-indexador", "value"),
        Output("sim-indexador", "disabled"),
        Output("sim-indexador-label", "children"),
        Input("titulo-dropdown", "value"),
    )
    def ajustar_indexador_simulador(titulo: str | None):
        tipo = titulo.split("||", 1)[0] if titulo else ""
        macro = estado.macro or {}
        ipca = (macro.get("focus_ipca_12m") or {}).get("valor") or (
            (macro.get("ipca_12m") or {}).get("valor") or IPCA_ATUAL
        )
        selic = (macro.get("selic_meta") or {}).get("valor") or SELIC_META_REF
        if tipo in TIPOS_IPCA:
            return round(ipca, 2), False, "IPCA projetado (% a.a.)"
        if tipo == "Tesouro Selic":
            return round(selic, 2), False, "Selic projetada (% a.a.)"
        if tipo == "Tesouro IGPM+ com Juros Semestrais":
            return round(ipca, 2), False, "IGP-M projetado (% a.a.)"
        return None, True, "Indexador (não se aplica ao prefixado)"

    @app.callback(
        Output("sim-condicoes", "children"),
        Input("titulo-dropdown", "value"),
    )
    def atualizar_condicoes_tese(titulo: str | None):
        if not titulo or "||" not in titulo:
            return html.Div()
        tipo, venc = titulo.split("||", 1)
        h = estado.df_historico
        df_tit = h[(h["tipo_titulo"] == tipo) & (h["data_vencimento"] == pd.Timestamp(venc))]
        if tipo == "Tesouro Selic":
            return html.P(
                "Tesouro Selic não tem tese de marcação a mercado: o preço acompanha a "
                "Selic diariamente e quase não oscila com a curva de juros.",
                className="tdwx-sim-note",
            )
        condicoes = avaliar_condicoes(h, df_tit, estado.macro or {})
        n_ok = sum(1 for c in condicoes if c.atendida)
        n_aval = sum(1 for c in condicoes if c.atendida is not None)
        icone = {True: ("✓", "ok"), False: ("✗", "nao"), None: ("—", "sem")}
        linhas = [
            html.Div(
                [
                    html.Span(
                        icone[c.atendida][0],
                        className=f"tdwx-cond-icone {icone[c.atendida][1]}",
                    ),
                    html.Div(
                        [html.Div(c.nome, className="tdwx-cond-nome"),
                         html.Div(c.detalhe, className="tdwx-cond-detalhe")]
                    ),
                ],
                className="tdwx-cond-linha",
            )
            for c in condicoes
        ]
        fonte = (estado.macro or {}).get("focus_selic_fim_ano_seguinte", {}).get("fonte")
        return html.Div(
            [
                html.Div(
                    [
                        html.Span("Condições para a tese de queda de taxa",
                                  className="tdwx-cond-titulo"),
                        html.Span(f"{n_ok} de {n_aval} atendidas", className="tdwx-cond-placar"),
                    ],
                    className="tdwx-cond-header",
                ),
                *linhas,
                html.P(
                    "Painel descritivo: mostra condições observáveis, não prevê a taxa nem "
                    "recomenda compra. Duration alta é faca de dois gumes — o mesmo título "
                    "que mais ganha na queda é o que mais perde se a taxa subir."
                    + (" Focus/Selic: Banco Central." if fonte == "BCB" else ""),
                    className="tdwx-cond-rodape",
                ),
            ],
            className="tdwx-cond-card",
        )

    @app.callback(
        Output("sim-resultado", "children"),
        Output("sim-heatmap", "figure"),
        Input("titulo-dropdown", "value"),
        Input("sim-delta", "value"),
        Input("sim-horizonte", "value"),
        Input("sim-indexador", "value"),
    )
    def atualizar_simulador(titulo, delta, horizonte, indexador):
        fig_vazia = go.Figure().update_layout(template="tdwx_dark", height=320)
        reg = _ultimo_registro(titulo)
        if reg is None or pd.isna(reg.get("pu_compra_manha")):
            return html.P("Selecione um título.", className="tdwx-sim-note"), fig_vazia

        tipo = reg["tipo_titulo"]
        base = dict(
            tipo_titulo=tipo,
            vencimento=reg["data_vencimento"],
            data_base=reg["data_base"],
            taxa_compra_pct=float(reg["taxa_compra_manha"]),
            pu_compra=float(reg["pu_compra_manha"]),
            taxa_venda_pct=(
                float(reg["taxa_venda_manha"])
                if pd.notna(reg.get("taxa_venda_manha")) else None
            ),
            indexador_aa_pct=float(indexador) if indexador not in (None, "") else 0.0,
        )
        try:
            r = simular(delta_pp=float(delta or 0), horizonte_meses=int(horizonte), **base)
        except ValueError:
            return (
                html.P(
                    "O horizonte escolhido passa do vencimento do título. "
                    "Escolha um prazo menor.",
                    className="tdwx-sim-note",
                ),
                fig_vazia,
            )

        cor = "success" if r.retorno_liquido >= 0 else "danger"
        cards = html.Div(
            [
                _stat_card("PU de compra hoje", _formatar_moeda(r.pu_compra)),
                _stat_card(f"PU de venda em {r.data_venda:%d/%m/%Y}", _formatar_moeda(r.pu_venda)),
                _stat_card("Retorno bruto", _formatar_pct(r.retorno_bruto),
                           "success" if r.retorno_bruto >= 0 else "danger"),
                _stat_card("Só da variação de taxa", _formatar_pct(r.efeito_taxa),
                           "success" if r.efeito_taxa >= 0 else "danger"),
                _stat_card(f"IR ({r.aliquota_ir * 100:.1f}%) + IOF",
                           _formatar_moeda(r.ir + r.iof)),
                _stat_card("Custódia B3", _formatar_moeda(r.custodia)),
                _stat_card("Retorno líquido", _formatar_pct(r.retorno_liquido), cor),
                _stat_card("Líquido ao ano", _formatar_pct(r.retorno_liquido_aa), cor),
            ],
            className="tdwx-sim-grid",
        )

        notas = []
        if r.fluxos_recebidos > 0:
            notas.append(
                f"Inclui {_formatar_moeda(r.fluxos_recebidos)} em cupons/parcelas recebidos "
                "no período (sem reinvestimento)."
            )
        degrau = proximo_degrau_ir(r.dias_corridos)
        if degrau and degrau[0] <= 30 and r.retorno_bruto > 0:
            dias_faltam, nova = degrau
            ganho_ir = (r.aliquota_ir - nova) * r.retorno_bruto
            notas.append(
                f"Atenção ao IR: esperando mais {dias_faltam} dia(s) a alíquota cai de "
                f"{r.aliquota_ir * 100:.1f}% para {nova * 100:.1f}%, "
                f"o que soma cerca de {ganho_ir * 100:.1f} p.p. ao retorno líquido."
            )
        nota_div = [
            html.P(html.Strong(n) if "Atenção" in n else n, className="tdwx-sim-note")
            for n in notas
        ]

        # Matriz delta x horizonte (retorno liquido)
        deltas = [-2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0]
        horizontes = [3, 6, 12, 24, 36, 60]
        m = matriz_cenarios(deltas, horizontes, **base) * 100
        rotulos_h = [f"{h}m" for h in horizontes]
        rotulos_d = [f"{d:+.1f}" for d in deltas]
        texto = [[("—" if pd.isna(v) else f"{v:+.1f}%") for v in linha] for linha in m.values]
        lim = float(np.nanmax(np.abs(m.values))) if np.isfinite(m.values).any() else 1.0
        fig = go.Figure(
            go.Heatmap(
                z=m.values,
                x=rotulos_h,
                y=rotulos_d,
                text=texto,
                texttemplate="%{text}",
                colorscale=[[0, "#FF5555"], [0.5, "#1E2F3F"], [1, "#00D4AA"]],
                zmid=0,
                zmin=-lim,
                zmax=lim,
                hovertemplate=(
                    "Taxa %{y} p.p. · venda em %{x}<br>Líquido: %{text}<extra></extra>"
                ),
                textfont=dict(size=11),
                showscale=False,  # os valores ja estao nas celulas
            )
        )
        fig.update_layout(
            template="tdwx_dark",
            height=400,
            title=dict(text="Retorno líquido por cenário", font=dict(size=14)),
            xaxis_title="Horizonte até a venda",
            yaxis_title="Δ taxa (p.p.)",
            margin=dict(t=50, l=60, r=10, b=50),
            yaxis=dict(type="category"),
            xaxis=dict(type="category"),
        )
        return html.Div([cards, *nota_div]), fig
