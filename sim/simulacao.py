"""Simulação em malha fechada: planta não linear + controlador de referência."""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field

import numpy as np

from .controlador import Controlador, Ganhos, lei_controle
from .model import Planta
from .params import Params

THETA_QUEDA = math.radians(25.0)  # batente mecânico: daqui o pêndulo não volta


@dataclass
class Sensores:
    """Imperfeições dos sensores usadas no modo realista."""

    ruido_giro: float = math.radians(0.1)     # rad/s (desvio padrão por amostra)
    ruido_acel: float = math.radians(0.5)     # rad   (vibração do motor)
    vies_giro: float = math.radians(0.02)     # rad/s (resíduo após calibração)
    vies_angulo: float = 0.0                  # rad   (erro de montagem do MPU6050)
    atraso_imu: int = 3                       # amostras (filtro digital do MPU6050)
    atraso_controle: int = 1                  # amostras (cálculo + atualização do PWM)


@dataclass
class Resultado:
    t: np.ndarray
    theta: np.ndarray
    theta_dot: np.ndarray
    omega: np.ndarray
    u: np.ndarray
    i: np.ndarray
    trim: np.ndarray
    theta_est: np.ndarray
    omega_est: np.ndarray
    caiu: bool = False
    extras: dict = field(default_factory=dict)

    @property
    def omega_pico(self) -> float:
        return float(np.max(np.abs(self.omega)))

    @property
    def i_pico(self) -> float:
        return float(np.max(np.abs(self.i)))

    def acomodou(self, tol_theta=math.radians(1.0), tol_thd=0.2, janela=0.3) -> bool:
        if self.caiu:
            return False
        n = max(1, int(janela / (self.t[1] - self.t[0])))
        return bool(np.all(np.abs(self.theta[-n:]) < tol_theta) and np.all(np.abs(self.theta_dot[-n:]) < tol_thd))


def simular(
    p: Params,
    g: Ganhos,
    theta0: float = math.radians(5.0),
    T: float = 5.0,
    realista: bool = True,
    sensores: Sensores | None = None,
    disturbios: list[tuple[float, float]] | None = None,
    planta: Params | None = None,
    semente: int = 0,
) -> Resultado:
    """Simula o pêndulo solto em repouso com inclinação theta0.

    disturbios: lista de (instante [s], degrau de velocidade angular [rad/s]),
                equivalente a um peteleco no braço.
    planta:     parâmetros "verdadeiros" da planta, se diferentes dos usados
                no projeto dos ganhos (teste de robustez).
    """
    pl = Planta(planta or p)
    s = sensores or Sensores()
    rng = np.random.default_rng(semente)
    ts = g.ts
    n = int(round(T / ts))
    sub = 8 if realista else 1
    dt = ts / sub
    f = pl.deriv_L if realista else pl.deriv

    # estado: theta, theta', omega, (i), e phi integrado à parte
    x = (theta0, 0.0, 0.0, 0.0) if realista else (theta0, 0.0, 0.0)
    phi = 0.0
    ctrl = Controlador(g, theta0=theta0 + (s.vies_angulo if realista else 0.0))
    fila_imu = deque([(theta0 + s.vies_angulo, 0.0)] * (s.atraso_imu + 1), maxlen=s.atraso_imu + 1)
    fila_u = deque([0.0] * (s.atraso_controle + 1), maxlen=s.atraso_controle + 1)
    dist = sorted(disturbios or [])
    cpr_rad = 1.0 / g.rad_por_contagem

    reg = {k: np.empty(n) for k in ("theta", "theta_dot", "omega", "u", "i", "trim", "theta_est", "omega_est")}
    entradas: list[tuple[float, float, int, float]] = []  # o que o controlador recebeu e respondeu
    caiu = False
    for k in range(n):
        t = k * ts
        while dist and dist[0][0] <= t:
            x = (x[0], x[1] + dist.pop(0)[1]) + tuple(x[2:])

        if realista:
            fila_imu.append(
                (
                    x[0] + s.vies_angulo + rng.normal(0.0, s.ruido_acel),
                    x[1] + s.vies_giro + rng.normal(0.0, s.ruido_giro),
                )
            )
            th_acel, giro = fila_imu[0]
            contagem = math.floor(phi * cpr_rad)
            u_calc = ctrl.passo(th_acel, giro, contagem, p.v_bus)
            entradas.append((th_acel, giro, contagem, u_calc))
            fila_u.append(u_calc)
            u = fila_u[0]
            th_est, w_est, trim = ctrl.theta, ctrl.w, ctrl.trim
        else:
            u = lei_controle(x[0], x[1], x[2], p.v_bus, g)
            th_est, w_est, trim = x[0], x[2], 0.0

        if caiu:
            u = 0.0
        i_m = x[3] if realista else pl.corrente(u, x[2])
        for name, val in zip(reg, (x[0], x[1], x[2], u, i_m, trim, th_est, w_est)):
            reg[name][k] = val

        for _ in range(sub):
            x_novo = pl.rk4(f, x, u, dt)
            phi += 0.5 * (x[2] + x_novo[2]) * dt
            x = x_novo
        if abs(x[0]) > THETA_QUEDA:
            caiu = True

    return Resultado(t=np.arange(n) * ts, caiu=caiu, extras={"entradas": entradas}, **reg)


def inclinacao_maxima(p: Params, g: Ganhos, T: float = 2.5, teto: float = math.radians(28.0), iteracoes: int = 8) -> float:
    """Maior inclinação inicial (em repouso) que o controlador recupera sem
    cair e sem passar do limite de rotação da roda. Sensores ideais."""

    def ok(th0: float) -> bool:
        r = simular(p, g, theta0=th0, T=T, realista=False)
        return r.acomodou() and r.omega_pico <= p.w_max

    lo, hi = 0.0, teto
    if ok(hi):
        return hi
    for _ in range(iteracoes):
        meio = 0.5 * (lo + hi)
        lo, hi = (meio, hi) if ok(meio) else (lo, meio)
    return lo
