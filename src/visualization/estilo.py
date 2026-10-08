"""Estilo único dos gráficos do projeto (matplotlib)."""

import matplotlib as mpl
import matplotlib.pyplot as plt

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


def aplicar() -> None:
    mpl.rcParams.update({
        "figure.facecolor": FUNDO,
        "axes.facecolor": FUNDO,
        "savefig.facecolor": FUNDO,
        "figure.dpi": 110,
        "savefig.dpi": 150,
        "savefig.bbox": "tight",
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.labelcolor": TINTA_SECUNDARIA,
        "axes.edgecolor": EIXO,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "axes.axisbelow": True,
        "grid.color": GRADE,
        "grid.linewidth": 0.6,
        "xtick.color": TINTA_SUAVE,
        "ytick.color": TINTA_SUAVE,
        "xtick.labelcolor": TINTA_SECUNDARIA,
        "ytick.labelcolor": TINTA_SECUNDARIA,
        "text.color": TINTA,
        "legend.frameon": False,
        "lines.linewidth": 2,
        "axes.prop_cycle": mpl.cycler(color=CORES),
    })


def milhar(x, _=None) -> str:
    """Formata 1234567 como '1,2 mi' / '12 mil' (para eixos)."""
    if abs(x) >= 1e6:
        return f"{x / 1e6:.1f} mi".replace(".", ",")
    if abs(x) >= 1e3:
        return f"{x / 1e3:.0f} mil"
    return f"{x:.0f}"


def salvar(fig: plt.Figure, nome: str) -> None:
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(config.FIGURES / f"{nome}.png")
