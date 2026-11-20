#!/usr/bin/env python3
"""Identificação de parâmetros a partir de logs de bancada (docs/testes_bancada.md).

Motor (etapa 5): braço preso, roda montada; rode `m 10`, `m 20`, `m 30`, `m 40`
deixando ~4 s em cada patamar, depois `s`.
    python tools/identify.py motor logs/ARQUIVO.csv --R 0.8
    (R = resistência do motor medida com o multímetro, em ohm)

    Em regime, V = ke·omega + V_atrito: a reta pelos patamares dá ke e o atrito.
    A subida de cada patamar é exponencial com tau = I_w·R/ke², de onde sai I_w.

Pêndulo (etapa 6): base presa de cabeça para baixo na borda da mesa, braço
pendurado; solte de ~10° e deixe oscilar livre por 20 s (controle parado).
    python tools/identify.py pendulo logs/ARQUIVO.csv

    A frequência natural dá Mgl/J (ω_n² = Mgl/J) e o decaimento dá o atrito do pivô.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sim.params import NOMINAL  # noqa: E402

RPM = 60 / (2 * math.pi)


# ----------------------------------------------------------------------------- motor
def patamares(t: np.ndarray, u: np.ndarray, minimo_s: float = 1.5) -> list[tuple[int, int]]:
    """Trechos em que a tensão comandada fica constante (e diferente de zero)."""
    trechos, ini = [], 0
    for k in range(1, len(u) + 1):
        if k == len(u) or abs(u[k] - u[ini]) > 0.15:
            if abs(u[ini]) > 0.3 and t[k - 1] - t[ini] >= minimo_s:
                trechos.append((ini, k))
            ini = k
    return trechos


def constante_de_tempo(t: np.ndarray, w: np.ndarray) -> float | None:
    """Tempo para percorrer 63,2 % do salto de velocidade do patamar."""
    w0, wf = w[0], float(np.mean(w[int(0.7 * len(w)):]))
    if abs(wf - w0) < 5.0:
        return None
    alvo = w0 + 0.632 * (wf - w0)
    cruzou = np.nonzero((w - alvo) * math.copysign(1.0, wf - w0) >= 0)[0]
    return float(t[cruzou[0]] - t[0]) if len(cruzou) else None


def identificar(t: np.ndarray, u: np.ndarray, w: np.ndarray, R: float, v_nom: float = 12.0) -> dict:
    """t [s], u [V], w [rad/s] de um ensaio em patamares. Retorna os parâmetros do motor."""
    trechos = patamares(t, u)
    if len(trechos) < 2:
        raise ValueError("Preciso de pelo menos 2 patamares de tensão diferentes (m 10, m 20, ...).")
    linhas, taus = [], []
    for i, f in trechos:
        fim = slice(i + int(0.7 * (f - i)), f)
        tau = constante_de_tempo(t[i:f], w[i:f])
        if tau:
            taus.append(tau)
        linhas.append((float(np.mean(u[fim])), float(np.mean(w[fim])), tau))
    ke, v_atrito = np.polyfit([l[1] for l in linhas], [l[0] for l in linhas], 1)
    if ke <= 0:
        raise ValueError("Inclinação negativa: o encoder está contando ao contrário do motor (comando 'inv enc').")
    tau = float(np.median(taus)) if taus else None
    return {
        "patamares": linhas,
        "ke": float(ke),
        "v_atrito": abs(float(v_atrito)),
        "i0": abs(float(v_atrito)) / R,
        "n0_rpm": (v_nom - abs(float(v_atrito))) / float(ke) * RPM,
        "tau": tau,
        "I_w": tau * float(ke) ** 2 / R if tau else None,
    }


def cmd_motor(a) -> None:
    d = np.genfromtxt(a.csv, delimiter=",", names=True)
    m = NOMINAL.motor
    try:
        r = identificar(d["t_s"], d["u_V"], d["roda_rpm"] / RPM, a.R, m.v_nom)
    except ValueError as e:
        sys.exit(str(e))
    print(f"{'tensão':>8} {'rotação em regime':>18} {'constante de tempo':>19}")
    for v, w, tau in r["patamares"]:
        print(f"{v:7.2f} V {w * RPM:14.0f} rpm {(f'{tau * 1e3:.0f} ms' if tau else 'salto pequeno'):>19}")
    print(f"\nke = kt = {r['ke']:.4f} V·s/rad        (modelo atual: {m.ke:.4f})")
    print(f"tensão de atrito = {r['v_atrito']:.2f} V  ->  corrente em vazio ≈ {r['i0']:.2f} A   (modelo atual: {m.i0:.2f})")
    print(f"rotação em vazio a {m.v_nom:.0f} V ≈ {r['n0_rpm']:.0f} rpm   (modelo atual: {m.n0_rpm:.0f})")
    if r["I_w"]:
        print(f"constante de tempo mecânica = {r['tau'] * 1e3:.0f} ms  ->  I_w ≈ {r['I_w'] * 1e3:.3f} g·m²   "
              f"(modelo atual: {NOMINAL.I_w * 1e3:.3f})")
        print("  Se I_w medido diferir muito do modelo, ajuste roda.preenchimento ou roda.m_conjunto.")
    print("\nColoque em sim/params.py (classe Motor):")
    print(f"    R = {a.R:.2f}\n    n0_rpm = {r['n0_rpm']:.0f}\n    i0 = {r['i0']:.2f}")
    print("e gere os ganhos de novo:  python -m sim.export_gains  &&  cd firmware && pio test -e native && pio run -t upload")


# ----------------------------------------------------------------------------- pêndulo
def identificar_pendulo(t: np.ndarray, theta_graus: np.ndarray) -> dict:
    """Oscilação livre pendurado: retorna omega_n [rad/s] e amortecimento zeta."""
    th = np.unwrap(np.radians(theta_graus))     # pendurado fica perto de ±180°: desembrulha
    x = th - np.median(th)
    # cruzamentos de zero subindo, com histerese: só conta depois de passar de
    # -h, para o ruído não criar cruzamentos falsos quando a amplitude já caiu
    h = math.radians(0.3)
    sub, armado = [], False
    for k in range(len(x) - 1):
        if x[k] < -h:
            armado = True
        elif armado and x[k] < 0 <= x[k + 1]:
            sub.append(k)
            armado = False
    sub = np.array(sub, dtype=int)
    if len(sub) < 3:
        raise ValueError("Poucas oscilações no log: solte o braço de ~10° e grave pelo menos 10 s.")
    tz = t[sub] - x[sub] * (t[sub + 1] - t[sub]) / (x[sub + 1] - x[sub])   # interpolação linear
    T = float(np.median(np.diff(tz)))
    picos = np.array([x[a:b].max() for a, b in zip(sub[:-1], sub[1:])])
    picos = picos[picos > np.radians(0.3)]      # abaixo disso o ruído domina
    if len(picos) < 3:
        raise ValueError("Amplitude pequena demais: solte o braço de mais longe (~10°).")
    delta = float(np.mean(np.log(picos[:-1] / picos[1:])))
    zeta = delta / math.sqrt(4 * math.pi**2 + delta**2)
    wn = 2 * math.pi / T / math.sqrt(1 - zeta**2)
    return {"T": T, "wn": wn, "zeta": zeta, "amplitude_graus": math.degrees(float(picos[0]))}


def cmd_pendulo(a) -> None:
    d = np.genfromtxt(a.csv, delimiter=",", names=True)
    try:
        r = identificar_pendulo(d["t_s"], d["theta_graus"])
    except ValueError as e:
        sys.exit(str(e))
    p = NOMINAL
    wn2_modelo = p.Mgl / p.J
    b_p = 2 * r["zeta"] * r["wn"] * p.J
    print(f"período = {r['T'] * 1e3:.0f} ms, amplitude inicial = {r['amplitude_graus']:.1f}°")
    print(f"omega_n² = Mgl/J = {r['wn'] ** 2:.1f} (rad/s)²   (modelo atual: {wn2_modelo:.1f})")
    print(f"amortecimento = {r['zeta']:.4f}  ->  atrito do pivô b_p ≈ {b_p:.2e} N·m·s/rad   (modelo atual: {p.b_p:.2e})")
    erro = r["wn"] ** 2 / wn2_modelo - 1
    print(f"\nDiferença em Mgl/J: {erro * 100:+.0f} %.", end=" ")
    if abs(erro) > 0.10:
        print("Pese de novo motor, roda e braço e confira l_w e frac_cm_braco em sim/params.py.")
    else:
        print("Modelo coerente com a bancada.")
    print(f"Coloque b_p = {b_p:.1e} em sim/params.py e rode `python -m sim.export_gains`.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="ensaio", required=True)
    m = sub.add_parser("motor", help="patamares de tensão com o braço preso")
    m.add_argument("csv", type=Path)
    m.add_argument("--R", type=float, required=True, help="resistência do motor medida [ohm]")
    m.set_defaults(func=cmd_motor)
    pn = sub.add_parser("pendulo", help="oscilação livre com a base de cabeça para baixo")
    pn.add_argument("csv", type=Path)
    pn.set_defaults(func=cmd_pendulo)
    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
