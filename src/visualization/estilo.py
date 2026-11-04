"""Estilo único dos gráficos do projeto (matplotlib)."""

import re

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib import font_manager
from matplotlib.transforms import offset_copy

from src import config

# Paleta categórica validada para daltonismo — usar SEMPRE nesta ordem
CORES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
AZUL, LARANJA, VERDE_AGUA = CORES[:3]
SEQUENCIAL_AZUL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

TINTA = "#0b0b0b"
TINTA_SECUNDARIA = "#52514e"
TINTA_SUAVE = "#898781"
GRADE = "#e1e0d9"
EIXO = "#c3c2b7"
FUNDO = "#fcfcfb"

# IBM Plex Sans (licença SIL OFL, em assets/fontes): a mesma fonte do painel HTML
PASTA_FONTES = config.ROOT / "assets" / "fontes"
FONTE = "IBM Plex Sans"


def _registra_fontes() -> None:
    for arquivo in PASTA_FONTES.rglob("*.ttf"):
        font_manager.fontManager.addfont(str(arquivo))


def aplicar() -> None:
    _registra_fontes()
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": [FONTE, "DejaVu Sans"],
        "figure.facecolor": FUNDO,
        "axes.facecolor": FUNDO,
        "savefig.facecolor": FUNDO,
        "figure.dpi": 110,
        "savefig.dpi": 160,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.3,
        "font.size": 10,
        "axes.titlesize": 11.5,
        "axes.titleweight": "semibold",
        "axes.titlelocation": "left",
        "axes.titlepad": 10,
        "figure.titlesize": 14,
        "figure.titleweight": "bold",
        "axes.labelcolor": TINTA_SECUNDARIA,
        "axes.labelsize": 9.5,
        "axes.edgecolor": EIXO,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "axes.axisbelow": True,
        "grid.color": GRADE,
        "grid.linewidth": 0.7,
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "xtick.major.pad": 6,
        "ytick.major.pad": 6,
        "xtick.color": TINTA_SUAVE,
        "ytick.color": TINTA_SUAVE,
        "xtick.labelcolor": TINTA_SECUNDARIA,
        "ytick.labelcolor": TINTA_SECUNDARIA,
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5,
        "text.color": TINTA,
        "legend.frameon": False,
        "legend.fontsize": 9.5,
        "legend.handlelength": 1.0,
        "legend.handleheight": 1.0,
        "lines.linewidth": 2.2,
        "lines.solid_capstyle": "round",
        "axes.prop_cycle": mpl.cycler(color=CORES),
    })


def cabecalho(fig: plt.Figure, titulo: str, subtitulo: str | None = None) -> None:
    """Título (a conclusão do gráfico) e subtítulo (como ler o gráfico) acima de tudo, alinhados à esquerda."""
    fig.subplots_adjust(top=0.95)
    acima = lambda pts: offset_copy(fig.transFigure, fig=fig, x=0, y=pts, units="points")
    fig.text(0.01, 1, titulo, transform=acima(30 if subtitulo else 10), ha="left", va="bottom",
             fontsize=14, fontweight="bold", color=TINTA)
    if subtitulo:
        fig.text(0.01, 1, subtitulo, transform=acima(10), ha="left", va="bottom", fontsize=10,
                 color=TINTA_SECUNDARIA)


def rodape(fig: plt.Figure, texto: str) -> None:
    """Fonte dos dados, em letra pequena abaixo do gráfico."""
    fig.text(0.01, 0, texto, transform=offset_copy(fig.transFigure, fig=fig, x=0, y=-12, units="points"),
             ha="left", va="top", fontsize=8.5, color=TINTA_SUAVE)


def milhar(x, _=None) -> str:
    """Formata 1234567 como '1,2 mi' / '12 mil' (para eixos)."""
    if abs(x) >= 1e6:
        return f"{x / 1e6:.1f} mi".replace(".", ",")
    if abs(x) >= 1e3:
        return f"{x / 1e3:.0f} mil"
    return f"{x:.0f}"


class _FormatadorVirgula(mticker.ScalarFormatter):
    def __call__(self, x, pos=None):
        return super().__call__(x, pos).replace(".", ",")


_DECIMAL = re.compile(r"(?<![\d.,])(\d+)\.(\d{1,2})(?![\d.])")


def virgula_decimal(fig: plt.Figure) -> None:
    """Troca o ponto decimal por vírgula nos eixos e nos textos da figura (1.5 → 1,5).

    Só números com 1 ou 2 casas decimais são trocados; "4.251.434" (separador de milhar) fica como está.
    """
    for ax in fig.axes:
        for eixo in (ax.xaxis, ax.yaxis):
            if type(eixo.get_major_formatter()) is mticker.ScalarFormatter:
                eixo.set_major_formatter(_FormatadorVirgula())
    for texto in fig.findobj(mpl.text.Text):
        conteudo = texto.get_text()
        if conteudo and "$" not in conteudo:
            texto.set_text(_DECIMAL.sub(r"\1,\2", conteudo))


def salvar(fig: plt.Figure, nome: str) -> None:
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    virgula_decimal(fig)
    fig.savefig(config.FIGURES / f"{nome}.png")
