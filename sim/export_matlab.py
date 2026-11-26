"""Referência para conferir a versão em MATLAB (matlab/).

Uso:  python -m sim.export_matlab

Grava matlab/referencia_python.json com os parâmetros derivados, os ganhos das
três leis e trajetórias simuladas com sensores ideais. O script
matlab/verificar_python.m compara o MATLAB com estes números.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from .controlador import LEIS, com_lei, projetar
from .model import Planta
from .params import NOMINAL
from .simulacao import simular

SAIDA = Path(__file__).resolve().parent.parent / "matlab" / "referencia_python.json"
PASSO = 10  # grava uma amostra a cada 10 períodos (10 ms)


def main() -> None:
    p = NOMINAL
    g = projetar(p)
    A, B = Planta(p).linear()
    m = p.motor
    ref = {
        "derivados": {
            "J": p.J, "Iw": p.I_w, "Mgl": p.Mgl, "m_w": p.m_w, "massa_total": p.massa_total,
            "ke": m.ke, "kt": m.kt, "tau_c": m.tau_c, "b": m.b, "b_lin": m.b_lin,
            "u_max": p.u_max, "tau_max": p.tau_max,
        },
        "A": A.tolist(), "B": B.ravel().tolist(),
        "ganhos": {
            "K": [g.k1, g.k2, g.k3], "KI": [g.q1, g.q2, g.q3, g.q4],
            "kp": g.kp, "ki": g.ki, "kd": g.kd, "kw": g.kw, "kwi": g.kwi,
            "pid_i_max": g.pid_i_max, "trim_max": g.trim_max,
        },
        "ensaio": {"theta0_graus": 5.0, "T": 3.0, "passo": PASSO, "disturbio": [1.5, 2.0]},
        "trajetorias": {},
    }
    for lei in LEIS:
        r = simular(p, com_lei(g, lei), theta0=math.radians(5.0), T=3.0, realista=False,
                    disturbios=[(1.5, 2.0)])
        ref["trajetorias"][lei] = {
            "t": r.t[::PASSO].tolist(),
            "theta": r.theta[::PASSO].tolist(),
            "omega": r.omega[::PASSO].tolist(),
            "u": r.u[::PASSO].tolist(),
        }
    SAIDA.write_text(json.dumps(ref, indent=1) + "\n", encoding="utf-8")
    print(f"gerado: {SAIDA.relative_to(Path.cwd()) if SAIDA.is_relative_to(Path.cwd()) else SAIDA}")
    print("K =", np.round([g.k1, g.k2, g.k3], 4))


if __name__ == "__main__":
    main()
