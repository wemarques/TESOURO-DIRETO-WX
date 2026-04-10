"""Tema Plotly customizado para o dashboard Tesouro Direto WX.

Define um template escuro 'tdwx_dark' alinhado com o CSS do projeto.
Importar este modulo registra o template e o define como padrao.
"""

import plotly.graph_objects as go
import plotly.io as pio

# Cores fundamentais
BG_PRIMARY = "#0F1923"
BG_CARD = "#1A2736"
TEXT_PRIMARY = "#E8ECF1"
TEXT_SECONDARY = "#8899AA"
BORDER = "#2A3A4A"
BORDER_STRONG = "#3A4A5A"

# Sequencia de cores para series (ordenada por contraste)
COLORWAY = [
    "#00D4AA",  # accent primary - verde
    "#4DA6FF",  # accent info - azul
    "#FFB830",  # accent warning - amarelo
    "#A78BFA",  # purple
    "#FF8C42",  # orange
    "#F472B6",  # pink
    "#FF5555",  # danger
    "#00B894",  # verde escuro
]

# Mapeamento de cores por familia normalizada
CORES_FAMILIA = {
    "SELIC": "#4DA6FF",
    "PRE": "#00D4AA",
    "PRE_JS": "#00B894",
    "IPCA": "#FFB830",
    "IPCA_JS": "#F0A020",
    "IGPM_JS": "#FF8C42",
    "EDUCA": "#A78BFA",
    "RENDA": "#F472B6",
}


_AXIS = dict(
    gridcolor=BORDER,
    gridwidth=1,
    zerolinecolor=BORDER_STRONG,
    zerolinewidth=1,
    linecolor=BORDER_STRONG,
    tickcolor=BORDER_STRONG,
    tickfont=dict(family="JetBrains Mono, monospace", color=TEXT_SECONDARY, size=11),
    title=dict(font=dict(family="DM Sans, sans-serif", color=TEXT_SECONDARY, size=12)),
)


TEMPLATE = go.layout.Template(
    layout=go.Layout(
        font=dict(
            family="DM Sans, sans-serif",
            size=12,
            color=TEXT_PRIMARY,
        ),
        title=dict(
            font=dict(family="DM Sans, sans-serif", size=15, color=TEXT_PRIMARY),
            x=0.02,
            xanchor="left",
            y=0.97,
            yanchor="top",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=COLORWAY,
        xaxis=_AXIS,
        yaxis=_AXIS,
        hoverlabel=dict(
            bgcolor=BG_CARD,
            bordercolor=BORDER_STRONG,
            font=dict(family="JetBrains Mono, monospace", color=TEXT_PRIMARY, size=12),
        ),
        legend=dict(
            font=dict(family="DM Sans, sans-serif", color=TEXT_PRIMARY, size=11),
            bgcolor="rgba(26, 39, 54, 0.85)",
            bordercolor=BORDER,
            borderwidth=1,
        ),
        margin=dict(l=60, r=30, t=60, b=60),
    )
)


def aplicar_tema(fig):
    """Aplica o tema dark a uma figura plotly existente.

    Util quando a figura ja foi criada com outro template.
    """
    fig.update_layout(template="tdwx_dark")
    return fig


# Registrar como template global do plotly
pio.templates["tdwx_dark"] = TEMPLATE
pio.templates.default = "tdwx_dark"
