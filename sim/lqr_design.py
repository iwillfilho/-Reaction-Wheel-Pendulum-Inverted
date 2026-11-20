"""Projeto do LQR e validação por simulação não linear.

Uso:  python -m sim.lqr_design

Imprime os ganhos e as margens, testa a robustez a erros de parâmetro e gera
os gráficos em sim/out/.
"""
from __future__ import annotations

import math
from dataclasses import replace

import numpy as np

from .controlador import polos_malha_fechada, projetar
from .params import NOMINAL, Params
from .simulacao import Resultado, Sensores, inclinacao_maxima, simular

RPM = 60.0 / (2.0 * math.pi)

# Erros de parâmetro testados com os ganhos nominais (a planta real nunca é a do modelo).
VARIACOES = {
    "nominal": {},
    "resistência +40 %": {"motor__R": 1.4},
    "resistência -30 %": {"motor__R": 0.7},
    "motor mais rápido (5000 rpm)": {"motor__n0_rpm": 5000 / 4000},
    "motor mais lento (3000 rpm)": {"motor__n0_rpm": 3000 / 4000},
    "atrito do motor x2": {"motor__i0": 2.0},
    "conjunto M8 +25 %": {"roda__m_conjunto": 1.25},
    "conjunto M8 -25 %": {"roda__m_conjunto": 0.75},
    "braço +50 % de massa": {"m_braco": 1.5},
    "atrito do pivô x4": {"b_p": 4.0},
}


def variar(p: Params, fatores: dict) -> Params:
    atual = {}
    for k, f in fatores.items():
        obj, campo = (p.motor, k[7:]) if k.startswith("motor__") else (p.roda, k[6:]) if k.startswith("roda__") else (p, k)
        atual[k] = getattr(obj, campo) * f
    return p.com(**atual)


def robustez(p: Params, g) -> list[tuple[str, bool, float, float]]:
    linhas = []
    for nome, fatores in VARIACOES.items():
        real = variar(p, fatores)
        r = simular(p, g, theta0=math.radians(5.0), T=6.0, realista=True, planta=real, semente=1)
        fim = slice(-2000, None)
        linhas.append((nome, (not r.caiu) and r.acomodou(tol_theta=math.radians(1.5), tol_thd=0.5),
                       math.degrees(float(np.sqrt(np.mean(r.theta[fim] ** 2)))), r.omega_pico * RPM))
    return linhas


# --- gráficos ---------------------------------------------------------------
def _paineis(r: Resultado, p: Params, titulo: str, nome: str, marcas: list[tuple[float, str]] | None = None):
    import matplotlib.pyplot as plt

    from . import graficos as gr

    gr.aplicar_estilo()
    fig, eixos = plt.subplots(4, 1, figsize=(7.2, 8.0), sharex=True)
    fig.suptitle(titulo, x=0.07, ha="left", fontsize=12, fontweight="bold", color=gr.TINTA)
    series = [
        (np.degrees(r.theta), "Inclinação do pêndulo (graus)", None),
        (r.omega * RPM, "Rotação da roda (rpm)", None),
        (r.u, "Tensão aplicada ao motor (V)", p.u_max),
        (r.i, "Corrente do motor (A)", p.i_max),
    ]
    for ax, (y, rotulo, lim) in zip(eixos, series):
        ax.plot(r.t, y, color=gr.SERIES[0])
        ax.set_title(rotulo)
        if lim is not None and np.max(np.abs(y)) > 0.6 * lim:
            # rótulos por dentro da faixa, para não bater nos eixos
            ax.set_ylim(-1.3 * lim, 1.3 * lim)
            gr.limite(ax, lim, f"limite +{lim:.1f}".replace(".", ","))
            gr.limite(ax, -lim, f"limite -{lim:.1f}".replace(".", ","), acima=False)
        for t_m, _ in marcas or []:
            ax.axvline(t_m, color=gr.TINTA_2, linewidth=0.8, alpha=0.45)
    for t_m, texto in marcas or []:
        eixos[0].annotate(texto, xy=(t_m, 1.0), xycoords=("data", "axes fraction"), xytext=(-4, -4),
                          textcoords="offset points", ha="right", va="top", fontsize=8, color=gr.TINTA_2)
    eixos[-1].set_xlabel("tempo (s)")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    return gr.salvar(fig, nome)


def _grafico_trim(p: Params, g) -> str:
    import matplotlib.pyplot as plt

    from . import graficos as gr

    s = Sensores(vies_angulo=math.radians(2.0))
    sem = simular(p, replace(g, trim_ganho=0.0), theta0=0.0, T=30.0, sensores=s)
    com = simular(p, g, theta0=0.0, T=30.0, sensores=s)
    gr.aplicar_estilo()
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7.2, 5.6), sharex=True)
    fig.suptitle("MPU6050 montado 2° torto: efeito do auto-ajuste",
                 x=0.07, ha="left", fontsize=12, fontweight="bold", color=gr.TINTA)
    for r, cor, nome in ((sem, gr.SERIES[1], "sem auto-ajuste"), (com, gr.SERIES[0], "com auto-ajuste")):
        y = _media_movel(r.omega * RPM, 200)
        a1.plot(r.t, y, color=cor, label=nome)
        gr.rotulo_ponta(a1, r.t[-1], y[-1], nome)
    a1.set_title("Rotação da roda (rpm, média de 0,2 s)")
    a1.legend(loc="center right")
    a2.plot(com.t, np.degrees(com.trim), color=gr.SERIES[0])
    a2.set_ylim(-0.1, 2.6)
    gr.limite(a2, 2.0, "erro real de montagem: 2°", lado="esquerda")
    a2.set_title("Correção aprendida pelo auto-ajuste (graus)")
    a2.set_xlabel("tempo (s)")
    fig.tight_layout(rect=(0, 0, 0.88, 0.95))
    return gr.salvar(fig, "auto_ajuste.png")


def _media_movel(y: np.ndarray, n: int) -> np.ndarray:
    c = np.cumsum(np.insert(y, 0, 0.0))
    out = np.empty_like(y)
    for k in range(len(y)):
        a = max(0, k - n + 1)
        out[k] = (c[k + 1] - c[a]) / (k + 1 - a)
    return out


def main() -> None:
    p = NOMINAL
    g = projetar(p)
    print(p.resumo())
    print(f"\nGanhos LQR (u = -K·x, x = [theta, theta', omega]):")
    print(f"  K1 = {g.k1:.2f} V/rad   K2 = {g.k2:.3f} V/(rad/s)   K3 = {g.k3:.5f} V/(rad/s)")
    polos = np.log(polos_malha_fechada(p, g).astype(complex)) / p.ts
    print("  polos de malha fechada (rad/s):", ", ".join(f"{z.real:.2f}{z.imag:+.2f}j" for z in sorted(polos, key=lambda z: z.real)))
    print(f"  auto-ajuste: trim' = {g.trim_ganho:.3e} · omega")

    th_max = inclinacao_maxima(p, g)
    print(f"\nMaior inclinação inicial recuperável: {math.degrees(th_max):.1f}° "
          f"(limite estático do torque: {math.degrees(p.theta_max_estatico):.1f}°)")

    print("\nRobustez com os ganhos nominais (soltar a 5°, sensores realistas):")
    print(f"  {'planta real':<30} {'equilibra':>9} {'erro rms':>9} {'pico roda':>10}")
    for nome, ok, rms, pico in robustez(p, g):
        print(f"  {nome:<30} {'sim' if ok else 'NÃO':>9} {rms:8.2f}° {pico:7.0f} rpm")

    r1 = simular(p, g, theta0=math.radians(8.0), T=4.0)
    f1 = _paineis(r1, p, "Pêndulo solto a 8° da vertical", "resposta_inicial.png")
    r2 = simular(p, g, theta0=0.0, T=6.0, disturbios=[(1.0, 1.5), (3.5, -2.5)])
    f2 = _paineis(r2, p, "Resposta a dois petelecos no braço", "disturbio.png",
                  marcas=[(1.0, "+1,5 rad/s"), (3.5, "-2,5 rad/s")])
    f3 = _grafico_trim(p, g)
    print("\nGráficos:", f1, f2, f3, sep="\n  ")


if __name__ == "__main__":
    main()
