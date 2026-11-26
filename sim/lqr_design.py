"""Projeto do LQR, do LQI e do PID e validação por simulação não linear.

Uso:  python -m sim.lqr_design

Imprime os ganhos e as margens, testa a robustez a erros de parâmetro e gera
os gráficos em sim/out/.
"""
from __future__ import annotations

import math
from dataclasses import replace

import numpy as np

from .controlador import LEIS, PID_POLO, com_lei, discretizar_lqi, polos_malha_fechada, projetar
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


NOMES_LEIS = {"lqr": "LQR + auto-ajuste", "lqi": "LQI", "pid": "PID + malha da roda"}


def comparar_leis(p: Params, g) -> list[tuple]:
    """As três leis nos mesmos ensaios: solta a 5°, dois petelecos e MPU6050 2° torto."""
    linhas = []
    for lei in LEIS:
        gl = com_lei(g, lei)
        r1 = simular(p, gl, theta0=math.radians(5.0), T=6.0, semente=1)
        r2 = simular(p, gl, theta0=0.0, T=6.0, disturbios=[(1.0, 1.5), (3.5, -2.5)], semente=2)
        r3 = simular(p, gl, theta0=0.0, T=20.0, sensores=Sensores(vies_angulo=math.radians(2.0)), semente=3)
        rob = sum((not r.caiu) and r.acomodou(tol_theta=math.radians(1.5), tol_thd=0.5)
                  for r in (simular(p, gl, theta0=math.radians(5.0), T=6.0, planta=variar(p, f), semente=1)
                            for f in VARIACOES.values()))
        w10 = float(np.mean(r3.omega[9500:10500])) * RPM
        voltas = float(np.trapezoid(r3.omega, r3.t)) / (2.0 * math.pi)
        linhas.append((NOMES_LEIS[lei], r1.acomodou(tol_theta=math.radians(1.0), tol_thd=0.3), r1.omega_pico * RPM,
                       not r2.caiu, w10, voltas, rob, math.degrees(inclinacao_maxima(p, gl))))
    return linhas


def _grafico_leis(p: Params, g) -> str:
    import matplotlib.pyplot as plt

    from . import graficos as gr

    gr.aplicar_estilo()
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7.2, 6.0))
    fig.suptitle("PID, LQR e LQI nos mesmos ensaios", x=0.07, ha="left", fontsize=12, fontweight="bold", color=gr.TINTA)
    s = Sensores(vies_angulo=math.radians(2.0))
    for lei, cor in zip(LEIS, gr.SERIES):
        gl = com_lei(g, lei)
        r = simular(p, gl, theta0=0.0, T=20.0, sensores=s, semente=3)
        y = _media_movel(r.omega * RPM, 200)
        a1.plot(r.t, y, color=cor, label=NOMES_LEIS[lei])
        r2 = simular(p, gl, theta0=0.0, T=4.0, disturbios=[(0.5, 2.0)], semente=2)
        a2.plot(r2.t, np.degrees(r2.theta), color=cor, label=NOMES_LEIS[lei])
    a1.set_title("MPU6050 montado 2° torto: rotação da roda (rpm, média de 0,2 s)")
    a1.set_xlabel("tempo (s)")
    a1.legend(loc="lower right")
    a2.set_title("Peteleco de 2 rad/s em t = 0,5 s: inclinação (graus)")
    a2.set_xlabel("tempo (s)")
    a2.legend(loc="upper right")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    return gr.salvar(fig, "comparacao_leis.png")


def main() -> None:
    p = NOMINAL
    g = projetar(p)
    print(p.resumo())
    print(f"\nGanhos LQR (u = -K·x, x = [theta, theta', omega]):")
    print(f"  K1 = {g.k1:.2f} V/rad   K2 = {g.k2:.3f} V/(rad/s)   K3 = {g.k3:.5f} V/(rad/s)")
    polos = np.log(polos_malha_fechada(p, g).astype(complex)) / p.ts
    print("  polos de malha fechada (rad/s):", ", ".join(f"{z.real:.2f}{z.imag:+.2f}j" for z in sorted(polos, key=lambda z: z.real)))
    print(f"  auto-ajuste: trim' = {g.trim_ganho:.3e} · omega")
    zl = np.log(np.linalg.eigvals(discretizar_lqi(p)[0] - discretizar_lqi(p)[1] @ g.KI).astype(complex)) / p.ts
    print(f"\nGanhos LQI (x = [theta, theta', omega, phi_r]):")
    print(f"  Q1 = {g.q1:.2f} V/rad   Q2 = {g.q2:.3f} V/(rad/s)   Q3 = {g.q3:.5f} V/(rad/s)   Q4 = {g.q4:.5f} V/rad")
    print("  polos de malha fechada (rad/s):", ", ".join(f"{z.real:.2f}{z.imag:+.2f}j" for z in sorted(zl, key=lambda z: z.real)))
    print(f"\nGanhos PID (polo triplo da malha de theta em -{PID_POLO:.0f} rad/s):")
    print(f"  kp = {g.kp:.2f} V/rad   ki = {g.ki:.1f} V/(rad·s)   kd = {g.kd:.3f} V/(rad/s)")
    print(f"  malha da roda: theta_ref = -({g.kw:.1e}·omega + {g.kwi:.1e}·phi_r)")

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

    print("\nComparação das leis (solta a 5°, petelecos, MPU6050 2° torto, robustez):")
    print(f"  {'lei':<22} {'5°':>4} {'pico 5°':>9} {'peteleco':>9} {'roda em 10 s':>13} {'voltas':>7} {'robustez':>9} {'máx':>6}")
    for nome, ok, pico, pet, w10, voltas, rob, thm in comparar_leis(p, g):
        print(f"  {nome:<22} {'sim' if ok else 'NÃO':>4} {pico:6.0f} rpm {'ok' if pet else 'cai':>9} {w10:9.0f} rpm "
              f"{voltas:7.1f} {rob:>4}/{len(VARIACOES)} {thm:5.1f}°")
    f4 = _grafico_leis(p, g)
    print("\nGráficos:", f1, f2, f3, f4, sep="\n  ")


if __name__ == "__main__":
    main()
