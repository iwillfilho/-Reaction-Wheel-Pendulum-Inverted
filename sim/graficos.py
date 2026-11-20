"""Estilo comum dos gráficos (PNG para o relatório).

Regras seguidas: uma medida por painel (nunca dois eixos y), linhas finas,
grade discreta, legenda sempre que há 2+ séries e rótulo direto na ponta da
linha, texto sempre em tinta neutra (a cor fica só na marca).
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
GRADE = "#e6e5e1"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]  # azul, laranja, água (validadas para daltonismo)
SAIDA = Path(__file__).parent / "out"


def aplicar_estilo() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": SUPERFICIE,
            "axes.facecolor": SUPERFICIE,
            "savefig.facecolor": SUPERFICIE,
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "text.color": TINTA,
            "axes.labelcolor": TINTA_2,
            "axes.titlecolor": TINTA,
            "axes.titlesize": 10.5,
            "axes.titleweight": "bold",
            "axes.titlelocation": "left",
            "axes.titlepad": 6,
            "axes.edgecolor": GRADE,
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": GRADE,
            "grid.linewidth": 0.8,
            "grid.linestyle": "-",
            "xtick.color": TINTA_2,
            "ytick.color": TINTA_2,
            "xtick.major.size": 0,
            "ytick.major.size": 0,
            "lines.linewidth": 1.6,
            "lines.solid_capstyle": "round",
            "lines.solid_joinstyle": "round",
            "legend.frameon": False,
            "legend.fontsize": 9,
        }
    )


def limite(ax, y: float, texto: str, acima: bool = True, lado: str = "direita") -> None:
    """Linha de referência discreta com rótulo (limite físico ou de segurança)."""
    ax.axhline(y, color=TINTA_2, linewidth=0.8, alpha=0.55, zorder=1)
    esq = lado == "esquerda"
    ax.annotate(
        texto, xy=(0.0 if esq else 1.0, y), xycoords=("axes fraction", "data"),
        xytext=(4 if esq else -4, 3 if acima else -3), textcoords="offset points",
        ha="left" if esq else "right", va="bottom" if acima else "top", fontsize=8, color=TINTA_2,
    )


def rotulo_ponta(ax, x, y, texto: str, dy: float = 0.0) -> None:
    """Rótulo direto na ponta de uma série (complementa a legenda)."""
    ax.annotate(
        texto, xy=(x, y), xytext=(6, dy), textcoords="offset points",
        ha="left", va="center", fontsize=8.5, color=TINTA, annotation_clip=False,
    )


def salvar(fig, nome: str) -> Path:
    SAIDA.mkdir(exist_ok=True)
    caminho = SAIDA / nome
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return caminho
