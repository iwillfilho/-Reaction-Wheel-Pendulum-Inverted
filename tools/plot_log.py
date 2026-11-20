#!/usr/bin/env python3
"""Gráfico de um log gravado por tools/telemetry_log.py.

Uso:  python tools/plot_log.py logs/ARQUIVO.csv [--inicio 2.0 --fim 8.0]
Gera ARQUIVO.png ao lado do CSV, no mesmo estilo dos gráficos da simulação,
para comparar bancada e modelo lado a lado.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sim import graficos as gr  # noqa: E402


def carregar(caminho: Path) -> dict[str, np.ndarray]:
    dados = np.genfromtxt(caminho, delimiter=",", names=True)
    if dados.size < 2:
        sys.exit(f"{caminho} não tem amostras suficientes.")
    return {nome: dados[nome] for nome in dados.dtype.names}


def main() -> None:
    import matplotlib.pyplot as plt

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", type=Path)
    ap.add_argument("--inicio", type=float, default=None, help="segundos a partir do começo do log")
    ap.add_argument("--fim", type=float, default=None)
    a = ap.parse_args()

    d = carregar(a.csv)
    t = d["t_s"] - d["t_s"][0]
    sel = np.ones_like(t, dtype=bool)
    if a.inicio is not None:
        sel &= t >= a.inicio
    if a.fim is not None:
        sel &= t <= a.fim

    gr.aplicar_estilo()
    fig, eixos = plt.subplots(4, 1, figsize=(7.2, 8.0), sharex=True)
    fig.suptitle(f"Ensaio de bancada: {a.csv.name}", x=0.07, ha="left", fontsize=12, fontweight="bold", color=gr.TINTA)
    paineis = [
        ("theta_graus", "Inclinação do pêndulo (graus)"),
        ("roda_rpm", "Rotação da roda (rpm)"),
        ("u_V", "Tensão comandada ao motor (V)"),
        ("vbus_V", "Tensão do barramento (V)"),
    ]
    for ax, (col, titulo) in zip(eixos, paineis):
        ax.plot(t[sel], d[col][sel], color=gr.SERIES[0])
        ax.set_title(titulo)
    eixos[-1].set_xlabel("tempo (s)")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    saida = a.csv.with_suffix(".png")
    fig.savefig(saida, dpi=150, bbox_inches="tight")
    print("Gráfico:", saida)


if __name__ == "__main__":
    main()
