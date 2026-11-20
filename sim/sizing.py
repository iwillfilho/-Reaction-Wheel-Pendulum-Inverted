"""Dimensionamento da roda de reação e do braço para o motor 775.

Varre o raio do círculo de parafusos M8. O comprimento do braço não é livre:
ele precisa ser o raio da roda (com o anel do encoder) mais uma folga para os
sensores ópticos e o mancal, e braço mais curto é sempre melhor para a
autoridade de controle. Para cada geometria projeta o LQR e mede, por
simulação não linear, a maior inclinação inicial que ainda é recuperada sem
passar do limite de rotação da roda.

Uso:  python -m sim.sizing
"""
from __future__ import annotations

import math

import numpy as np

from .controlador import projetar
from .params import NOMINAL, Params
from .simulacao import inclinacao_maxima, simular

FOLGA_MIN = 0.030          # m: do anel do encoder até o eixo do pivô (sensores + mancal)
FOLGAS = (0.030, 0.050, 0.070)
MESA_IMPRESSORA = 0.200    # m: maior diâmetro que cabe com folga numa mesa de 220 mm
PASSO_MIN_PARAFUSOS = 0.019  # m: arruela M8 (16 mm) + 3 mm de parede entre vizinhos


def geometria(r_parafusos: float, folga: float = FOLGA_MIN, base: Params = NOMINAL) -> Params:
    p = base.com(roda__r_parafusos=r_parafusos)
    return p.com(l_w=p.roda.r_aleta + folga)


def avaliar(p: Params) -> dict:
    g = projetar(p)
    th_max = inclinacao_maxima(p, g)
    r5 = simular(p, g, theta0=math.radians(5.0), T=3.0, realista=False)
    r = p.roda
    return {
        "r_parafusos_mm": r.r_parafusos * 1e3,
        "l_w_mm": p.l_w * 1e3,
        "diametro_mm": 2 * r.r_aleta * 1e3,
        "I_w_gm2": p.I_w * 1e3,
        "massa_g": p.massa_total * 1e3,
        "theta_max_graus": math.degrees(th_max),
        "theta_estatico_graus": math.degrees(p.theta_max_estatico),
        "w_pico_5graus_rpm": r5.omega_pico * 60 / (2 * math.pi),
        # força centrífuga em cada conjunto M8 no limite de rotação
        "forca_parafuso_N": r.m_conjunto * p.w_max**2 * r.r_parafusos,
        "cabe_na_mesa": 2 * r.r_aleta <= MESA_IMPRESSORA,
        "parafusos_cabem": 2 * math.pi * r.r_parafusos / r.n_parafusos >= PASSO_MIN_PARAFUSOS,
    }


def varrer(raios_mm=None, folgas=FOLGAS) -> dict[float, list[dict]]:
    raios_mm = raios_mm if raios_mm is not None else np.arange(36, 85, 4)
    return {f: [avaliar(geometria(r * 1e-3, f)) for r in raios_mm] for f in folgas}


def grafico(res: dict[float, list[dict]], escolhido: Params):
    import matplotlib.pyplot as plt

    from . import graficos as gr

    gr.aplicar_estilo()
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for cor, (folga, linhas) in zip(gr.SERIES, res.items()):
        x = [d["r_parafusos_mm"] for d in linhas]
        y = [d["theta_max_graus"] for d in linhas]
        ax.plot(x, y, color=cor, label=f"folga de {folga * 1e3:.0f} mm até o pivô")
        gr.rotulo_ponta(ax, x[-1], y[-1], f"{folga * 1e3:.0f} mm")
    limite_mesa = (MESA_IMPRESSORA / 2 - escolhido.roda.aleta - escolhido.roda.aro_fora) * 1e3
    ax.axvline(limite_mesa, color=gr.TINTA_2, linewidth=0.8, alpha=0.55)
    ax.annotate("limite da mesa\nde impressão", xy=(limite_mesa, 0.04), xycoords=("data", "axes fraction"),
                xytext=(-5, 0), textcoords="offset points", ha="right", va="bottom", fontsize=8, color=gr.TINTA_2)
    e = avaliar(escolhido)
    ax.plot([e["r_parafusos_mm"]], [e["theta_max_graus"]], "o", color=gr.SERIES[0], markersize=8,
            markeredgecolor=gr.SUPERFICIE, markeredgewidth=2, zorder=5)
    texto = f"projeto adotado: {e['r_parafusos_mm']:.0f} mm, recupera {e['theta_max_graus']:.1f}°".replace(".", ",")
    ax.annotate(texto, xy=(e["r_parafusos_mm"], e["theta_max_graus"]), xytext=(8, 12), textcoords="offset points",
                ha="left", fontsize=8.5, color=gr.TINTA)
    ax.set_title("Inclinação máxima recuperável em função do tamanho da roda")
    ax.set_xlabel("raio do círculo de parafusos M8 (mm)")
    ax.set_ylabel("inclinação inicial recuperável (graus)")
    ax.set_ylim(bottom=0)
    ax.legend(loc="lower left", title="braço = raio da roda +", title_fontsize=9, alignment="left")
    return gr.salvar(fig, "dimensionamento.png")


def main() -> None:
    res = varrer()
    print("Folga de 30 mm (braço mais curto possível):")
    print(f"{'raio':>5} {'braço':>6} {'Ø total':>8} {'I_w':>7} {'massa':>6} {'recupera':>9} {'estático':>9} "
          f"{'pico a 5°':>10} {'força/M8':>9}  observação")
    for d in res[FOLGA_MIN]:
        obs = [] if d["cabe_na_mesa"] else ["não cabe na mesa"]
        obs += [] if d["parafusos_cabem"] else ["parafusos encostam"]
        print(f"{d['r_parafusos_mm']:5.0f} {d['l_w_mm']:6.0f} {d['diametro_mm']:8.0f} {d['I_w_gm2']:7.3f} "
              f"{d['massa_g']:6.0f} {d['theta_max_graus']:8.1f}° {d['theta_estatico_graus']:8.1f}° "
              f"{d['w_pico_5graus_rpm']:7.0f} rpm {d['forca_parafuso_N']:7.0f} N  {', '.join(obs)}")
    e = avaliar(NOMINAL)
    print(f"\nProjeto adotado em sim/params.py: raio {e['r_parafusos_mm']:.0f} mm, braço {e['l_w_mm']:.0f} mm "
          f"-> recupera {e['theta_max_graus']:.1f}°, {e['forca_parafuso_N']:.0f} N por parafuso a "
          f"{NOMINAL.w_max * 60 / (2 * math.pi):.0f} rpm")
    print("Gráfico:", grafico(res, NOMINAL))


if __name__ == "__main__":
    main()
