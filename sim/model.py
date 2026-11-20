"""Modelo dinâmico do pêndulo invertido com roda de reação.

Coordenadas
-----------
theta : ângulo do pêndulo medido a partir da vertical para cima [rad]
omega : velocidade da roda em relação ao braço [rad/s] (o que o encoder mede)
V     : tensão média aplicada ao motor [V]

Convenção de sinais: V > 0 gera torque positivo na roda (acelera omega > 0) e,
por reação, torque NEGATIVO no pêndulo (theta diminui).

Equações (Lagrange, ver sim/derivacao.py)
-----------------------------------------
    J * theta''                 = Mgl*sin(theta) - b_p*theta' - tau
    I_w * (theta'' + omega')    = tau
    tau = kt*i - atrito(omega)          torque líquido do braço sobre a roda
    L*di/dt = V - R*i - ke*omega        (L = 0 no modelo de projeto)
"""
from __future__ import annotations

import math

import numpy as np

from .params import Params

EPS_ATRITO = 1.0  # rad/s: largura da transição suave do atrito seco


class Planta:
    """Constantes pré-calculadas + derivadas do modelo não linear."""

    def __init__(self, p: Params):
        m = p.motor
        self.p = p
        self.J, self.Iw, self.Mgl, self.bp = p.J, p.I_w, p.Mgl, p.b_p
        self.kt, self.ke, self.R, self.L = m.kt, m.ke, m.R, m.L
        self.tau_c, self.b = m.tau_c, m.b

    # --- torques -------------------------------------------------------------
    def atrito(self, omega: float) -> float:
        return self.tau_c * math.tanh(omega / EPS_ATRITO) + self.b * omega

    def corrente(self, V: float, omega: float) -> float:
        """Corrente em regime elétrico (L = 0)."""
        return (V - self.ke * omega) / self.R

    # --- derivadas -----------------------------------------------------------
    def deriv_tau(self, x, tau: float, bp: float | None = None):
        """Mecânica pura: x = (theta, theta', omega), torque tau imposto na roda."""
        th, thd, _ = x
        bp = self.bp if bp is None else bp
        thdd = (self.Mgl * math.sin(th) - bp * thd - tau) / self.J
        return (thd, thdd, tau / self.Iw - thdd)

    def deriv(self, x, V: float):
        """Modelo de projeto: x = (theta, theta', omega), indutância desprezada."""
        tau = self.kt * self.corrente(V, x[2]) - self.atrito(x[2])
        return self.deriv_tau(x, tau)

    def deriv_L(self, x, V: float):
        """Modelo com indutância: x = (theta, theta', omega, i)."""
        th, thd, om, i = x
        tau = self.kt * i - self.atrito(om)
        d = self.deriv_tau((th, thd, om), tau)
        return (d[0], d[1], d[2], (V - self.R * i - self.ke * om) / self.L)

    # --- integração ----------------------------------------------------------
    @staticmethod
    def rk4(f, x, u, dt: float):
        k1 = f(x, u)
        k2 = f(tuple(a + 0.5 * dt * b for a, b in zip(x, k1)), u)
        k3 = f(tuple(a + 0.5 * dt * b for a, b in zip(x, k2)), u)
        k4 = f(tuple(a + dt * b for a, b in zip(x, k3)), u)
        return tuple(
            a + dt / 6.0 * (b1 + 2 * b2 + 2 * b3 + b4)
            for a, b1, b2, b3, b4 in zip(x, k1, k2, k3, k4)
        )

    # --- grandezas conservadas (usadas nos testes) -----------------------------
    def energia(self, x) -> float:
        th, thd, om = x[:3]
        return 0.5 * self.J * thd**2 + 0.5 * self.Iw * (thd + om) ** 2 + self.Mgl * math.cos(th)

    def momento_angular(self, x) -> float:
        """Momento angular total em torno do pivô."""
        _, thd, om = x[:3]
        return self.J * thd + self.Iw * (thd + om)

    # --- linearização em torno de theta = 0 -------------------------------------
    def linear(self):
        """Retorna (A, B) contínuos para x = (theta, theta', omega), u = V."""
        J, Iw, Mgl, bp = self.J, self.Iw, self.Mgl, self.bp
        c = self.kt * self.ke / self.R + self.p.motor.b_lin  # d(tau)/d(omega), com sinal trocado
        g = self.kt / self.R                                # d(tau)/dV
        A = np.array(
            [
                [0.0, 1.0, 0.0],
                [Mgl / J, -bp / J, c / J],
                [-Mgl / J, bp / J, -c * (1.0 / Iw + 1.0 / J)],
            ]
        )
        B = np.array([[0.0], [-g / J], [g * (1.0 / Iw + 1.0 / J)]])
        return A, B
