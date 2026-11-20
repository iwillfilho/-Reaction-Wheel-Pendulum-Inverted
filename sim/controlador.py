"""Controlador de referência em Python.

Espelha linha a linha o que roda no firmware (firmware/lib/control). Os vetores
de teste exportados por sim/export_gains.py são gerados com estas funções e
conferidos contra o código C em `pio test -e native`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.signal import cont2discrete

from .model import Planta
from .params import Params

# Pesos do LQR pela regra de Bryson: 1 / (desvio aceitável)².
DESVIO_THETA = math.radians(3.0)   # rad
DESVIO_THETA_DOT = 0.5             # rad/s
DESVIO_OMEGA = 50.0                # rad/s  (menor = roda volta a zero mais rápido)
DESVIO_U = 11.4                    # V

TAU_TRIM = 8.0        # s   auto-ajuste do ângulo de equilíbrio (bem mais lento que a malha da roda)
TRIM_MAX = math.radians(4.0)
FC_OMEGA = 30.0       # Hz  corte do filtro da velocidade da roda
TAU_CF = 0.5          # s   constante de tempo do filtro complementar
N_EVENTOS = 16        # mudanças de contagem guardadas pelo estimador de velocidade
BASE_MIN = 8          # períodos: base de tempo mínima do estimador
BASE_MAX = 100        # períodos: não usa contagens mais velhas que isso


@dataclass(frozen=True)
class Ganhos:
    k1: float            # V/rad
    k2: float            # V/(rad/s)
    k3: float            # V/(rad/s)
    ts: float
    u_frac: float        # fração máxima da tensão do barramento
    i_max: float         # A
    ke: float            # V·s/rad   modelo do motor para o limite de corrente
    R: float             # ohm
    trim_ganho: float    # (rad/s) por (rad/s): trim' = trim_ganho * omega
    trim_max: float      # rad
    alfa_w: float        # coeficiente do passa-baixa da velocidade da roda
    alfa_cf: float       # coeficiente do filtro complementar
    rad_por_contagem: float

    @property
    def K(self) -> np.ndarray:
        return np.array([[self.k1, self.k2, self.k3]])


def discretizar(p: Params):
    A, B = Planta(p).linear()
    Ad, Bd, *_ = cont2discrete((A, B, np.eye(3), np.zeros((3, 1))), p.ts, method="zoh")
    return Ad, Bd


def projetar(p: Params, desvios=None) -> Ganhos:
    """LQR discreto para x = (theta, theta', omega), u = tensão do motor."""
    import control

    d_th, d_thd, d_om, d_u = desvios or (DESVIO_THETA, DESVIO_THETA_DOT, DESVIO_OMEGA, DESVIO_U)
    Ad, Bd = discretizar(p)
    Q = np.diag([1 / d_th**2, 1 / d_thd**2, 1 / d_om**2])
    Rm = np.array([[1 / d_u**2]])
    K, _, _ = control.dlqr(Ad, Bd, Q, Rm)
    k1, k2, k3 = (float(v) for v in np.asarray(K).ravel())

    m = p.motor
    k_ef = m.ke + m.R * m.b_lin / m.kt  # V por rad/s para manter a roda girando em regime
    return Ganhos(
        k1=k1, k2=k2, k3=k3, ts=p.ts,
        u_frac=p.u_frac, i_max=p.i_max, ke=m.ke, R=m.R,
        trim_ganho=-(k3 + k_ef) / (k1 * TAU_TRIM),
        trim_max=TRIM_MAX,
        alfa_w=1.0 - math.exp(-2.0 * math.pi * FC_OMEGA * p.ts),
        alfa_cf=TAU_CF / (TAU_CF + p.ts),
        rad_por_contagem=2.0 * math.pi / p.roda.cpr,
    )


def polos_malha_fechada(p: Params, g: Ganhos) -> np.ndarray:
    Ad, Bd = discretizar(p)
    return np.linalg.eigvals(Ad - Bd @ g.K)


def _volta(a: float) -> float:
    """Ângulo em [-pi, pi]."""
    return (a + math.pi) % (2.0 * math.pi) - math.pi


def _limita(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def lei_controle(theta_e: float, theta_dot: float, omega: float, vbus: float, g: Ganhos) -> float:
    """Tensão a aplicar no motor [V]. Mesma sequência de rwp_lqr_lei() em C."""
    u = -(g.k1 * theta_e + g.k2 * theta_dot + g.k3 * omega)
    fcem = g.ke * omega
    u = _limita(u, fcem - g.R * g.i_max, fcem + g.R * g.i_max)   # limite de corrente
    um = g.u_frac * vbus
    return _limita(u, -um, um)                                   # limite de tensão


class Controlador:
    """Estimadores + lei de controle + auto-ajuste, um passo por período."""

    def __init__(self, g: Ganhos, theta0: float = 0.0):
        self.g = g
        self.theta = theta0   # estimativa do filtro complementar
        self.w = 0.0          # velocidade filtrada da roda
        self.trim = 0.0
        self.cont_ant = 0
        self.agora = 0        # contador de períodos
        self.eventos: list[tuple[int, int]] = [(0, 0)]   # (instante, contagem) das últimas mudanças
        self.w_bruta = 0.0

    def velocidade_roda(self, contagem: int) -> float:
        """Velocidade da roda a partir dos instantes das últimas contagens.

        Dividir a variação de contagem por um único período daria um trem de
        pulsos em baixa rotação (chega menos de uma contagem por período).
        Aqui cada mudança de contagem é guardada com o instante em que ocorreu
        e a velocidade é a variação entre a mais recente e uma anterior que
        esteja a pelo menos BASE_MIN períodos de distância: base longa o
        bastante para o erro de 1 período na medida do tempo pesar pouco, e
        que se estica sozinha quando a roda gira devagar. Sem contagens novas,
        a estimativa é limitada por 1 contagem / tempo decorrido.
        """
        g = self.g
        self.agora += 1
        if contagem != self.cont_ant:
            self.cont_ant = contagem
            self.eventos.append((self.agora, contagem))
            del self.eventos[:-N_EVENTOS]
        w = 0.0
        n = len(self.eventos)
        if n >= 2:
            t_novo, c_novo = self.eventos[-1]
            j = 1
            while j + 1 <= n - 1:
                if t_novo - self.eventos[-1 - j][0] >= BASE_MIN:
                    break
                if t_novo - self.eventos[-2 - j][0] > BASE_MAX:
                    break
                j += 1
            t_ant, c_ant = self.eventos[-1 - j]
            w = (c_novo - c_ant) * g.rad_por_contagem / ((t_novo - t_ant) * g.ts)
            parado = self.agora - t_novo
            if parado > 0:
                teto = g.rad_por_contagem / (parado * g.ts)
                w = _limita(w, -teto, teto)
        self.w_bruta = w
        self.w += g.alfa_w * (w - self.w)
        return self.w

    def passo(self, theta_acel: float, giro: float, contagem: int, vbus: float, trim_ativo: bool = True):
        g = self.g
        # filtro complementar na forma predição + correção (mesmo que rwp_control.c)
        pred = self.theta + giro * g.ts
        self.theta = _volta(pred + (1.0 - g.alfa_cf) * _volta(theta_acel - pred))
        self.w = self.velocidade_roda(contagem)

        u = lei_controle(self.theta - self.trim, giro, self.w, vbus, g)
        if trim_ativo and abs(u) < 0.9 * g.u_frac * vbus:
            self.trim = _limita(self.trim + g.trim_ganho * self.w * g.ts, -g.trim_max, g.trim_max)
        return u
