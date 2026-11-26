"""Controlador de referência em Python.

Espelha linha a linha o que roda no firmware (firmware/lib/control). Os vetores
de teste exportados por sim/export_gains.py são gerados com estas funções e
conferidos contra o código C em `pio test -e native`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

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

# --- leis do equilíbrio --------------------------------------------------------
LEIS = ("lqr", "lqi", "pid")
DESVIO_PHI = 2.0 * math.pi * 3.0   # rad: LQI aceita ~3 voltas de roda longe do ponto de partida
PID_POLO = 15.0       # rad/s  polo triplo da malha de theta do PID (acima de ~20 a integral satura a tensão)
PID_KW = 1.0e-3       # rad por rad/s: malha externa, parte proporcional à rotação da roda
PID_KWI = 2.5e-4      # rad por rad:   malha externa, parte integral (ângulo da roda)
PID_I_MAX = 0.02      # rad·s: limite da integral do erro de theta


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
    # --- lei do equilíbrio: "lqr" (com auto-ajuste), "lqi" ou "pid" ---------------
    lei: str = "lqr"
    # LQI: u = -(q1*theta + q2*theta' + q3*omega + q4*phi_r), phi_r = ângulo da roda [rad]
    q1: float = 0.0      # V/rad
    q2: float = 0.0      # V/(rad/s)
    q3: float = 0.0      # V/(rad/s)
    q4: float = 0.0      # V/rad (de roda)
    # PID em theta + malha externa PI na roda:
    #   u = kp*e + ki*integral(e) + kd*theta',  e = theta - theta_ref,
    #   theta_ref = -(kw*omega + kwi*phi_r)
    kp: float = 0.0      # V/rad
    ki: float = 0.0      # V/(rad·s)
    kd: float = 0.0      # V/(rad/s)
    kw: float = 0.0      # rad por rad/s
    kwi: float = 0.0     # rad por rad
    pid_i_max: float = 0.0   # rad·s: limite da integral de e

    @property
    def K(self) -> np.ndarray:
        return np.array([[self.k1, self.k2, self.k3]])

    @property
    def KI(self) -> np.ndarray:
        return np.array([[self.q1, self.q2, self.q3, self.q4]])

    @property
    def phi_max(self) -> float:
        """Anti-windup do integrador da roda [rad]: o efeito dele fica limitado ao
        mesmo ângulo de equilíbrio equivalente do auto-ajuste (trim_max)."""
        if self.lei == "lqi":
            return self.trim_max * abs(self.q1 / self.q4) if self.q4 else math.inf
        if self.lei == "pid":
            return self.trim_max / self.kwi if self.kwi else math.inf
        return math.inf


def discretizar(p: Params):
    A, B = Planta(p).linear()
    Ad, Bd, *_ = cont2discrete((A, B, np.eye(3), np.zeros((3, 1))), p.ts, method="zoh")
    return Ad, Bd


def discretizar_lqi(p: Params):
    """Planta aumentada com phi_r' = omega: x = (theta, theta', omega, phi_r)."""
    A, B = Planta(p).linear()
    A4 = np.zeros((4, 4))
    A4[:3, :3] = A
    A4[3, 2] = 1.0
    B4 = np.vstack([B, [[0.0]]])
    Ad, Bd, *_ = cont2discrete((A4, B4, np.eye(4), np.zeros((4, 1))), p.ts, method="zoh")
    return Ad, Bd


def projetar_lqi(p: Params, desvio_phi: float | None = None) -> tuple[float, float, float, float]:
    """LQI: o LQR com o ângulo da roda como quarto estado. Mesmos pesos de Bryson
    do LQR mais um para phi_r (quantas voltas de roda são aceitáveis)."""
    import control

    Ad, Bd = discretizar_lqi(p)
    d_phi = DESVIO_PHI if desvio_phi is None else desvio_phi
    Q = np.diag([1 / DESVIO_THETA**2, 1 / DESVIO_THETA_DOT**2, 1 / DESVIO_OMEGA**2, 1 / d_phi**2])
    K, _, _ = control.dlqr(Ad, Bd, Q, np.array([[1 / DESVIO_U**2]]))
    return tuple(float(v) for v in np.asarray(K).ravel())


def projetar_pid(p: Params, polo: float | None = None) -> tuple[float, float, float]:
    """PID em theta por alocação de polos.

    Perto da vertical e com a roda devagar, a tensão vira torque com ganho
    g = kt/R e o braço obedece J*theta'' = Mgl*theta - g*u. Com
    u = kp*e + ki*integral(e) + kd*theta', a malha de theta fica
        J s³ + g kd s² + (g kp - Mgl) s + g ki = 0,
    e um polo triplo em s = -polo dá os três ganhos.
    """
    pl = Planta(p)
    s = PID_POLO if polo is None else polo
    g = pl.kt / pl.R
    return ((pl.Mgl + 3 * s * s * pl.J) / g, s**3 * pl.J / g, 3 * s * pl.J / g)


def com_lei(g: Ganhos, lei: str) -> Ganhos:
    if lei not in LEIS:
        raise ValueError(f"lei desconhecida: {lei}")
    return replace(g, lei=lei)


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
    q1, q2, q3, q4 = projetar_lqi(p)
    kp, ki, kd = projetar_pid(p)
    return Ganhos(
        k1=k1, k2=k2, k3=k3, ts=p.ts,
        u_frac=p.u_frac, i_max=p.i_max, ke=m.ke, R=m.R,
        trim_ganho=-(k3 + k_ef) / (k1 * TAU_TRIM),
        trim_max=TRIM_MAX,
        alfa_w=1.0 - math.exp(-2.0 * math.pi * FC_OMEGA * p.ts),
        alfa_cf=TAU_CF / (TAU_CF + p.ts),
        rad_por_contagem=2.0 * math.pi / p.roda.cpr,
        q1=q1, q2=q2, q3=q3, q4=q4,
        kp=kp, ki=ki, kd=kd, kw=PID_KW, kwi=PID_KWI,
        pid_i_max=PID_I_MAX,
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


def limitar_tensao(u: float, omega: float, vbus: float, g: Ganhos) -> float:
    """Limites de corrente e de tensão das três leis (os mesmos de lei_controle)."""
    fcem = g.ke * omega
    u = _limita(u, fcem - g.R * g.i_max, fcem + g.R * g.i_max)
    um = g.u_frac * vbus
    return _limita(u, -um, um)


class Integradores:
    """Estado das leis LQI e PID. Mesma sequência de rwp_balance_law() em C.

    phi_ref: ângulo da roda tomado como zero ao entrar em equilíbrio. O anti-windup
    move phi_ref para que o integrador da roda nunca peça mais que trim_max de
    inclinação equivalente, e congela tudo enquanto a tensão está saturada.
    """

    def __init__(self, phi0: float = 0.0):
        self.reiniciar(phi0)

    def reiniciar(self, phi0: float) -> None:
        self.phi_ref = phi0
        self.i_e = 0.0
        self.ref = 0.0          # ângulo de equilíbrio equivalente [rad] (telemetria)
        self.saturou = False
        self.z_ant = 0.0

    def passo(self, g: Ganhos, theta: float, theta_dot: float, omega: float, phi: float, vbus: float) -> float:
        z = phi - self.phi_ref
        if self.saturou:                      # congela: a roda anda, o integrador não
            z = self.z_ant
            self.phi_ref = phi - z
        zm = g.phi_max
        if abs(z) > zm:
            z = math.copysign(zm, z)
            self.phi_ref = phi - z
        self.z_ant = z

        if g.lei == "lqi":
            u0 = -(g.q1 * theta + g.q2 * theta_dot + g.q3 * omega + g.q4 * z)
            self.ref = -g.q4 * z / g.q1
        else:  # pid
            self.ref = _limita(-(g.kw * omega + g.kwi * z), -g.trim_max, g.trim_max)
            e = theta - self.ref
            if not self.saturou:
                self.i_e = _limita(self.i_e + e * g.ts, -g.pid_i_max, g.pid_i_max)
            u0 = g.kp * e + g.ki * self.i_e + g.kd * theta_dot
        u = limitar_tensao(u0, omega, vbus, g)
        self.saturou = abs(u) >= 0.9 * g.u_frac * vbus
        return u


class Controlador:
    """Estimadores + lei do equilíbrio (LQR com auto-ajuste, LQI ou PID), um passo por período."""

    def __init__(self, g: Ganhos, theta0: float = 0.0):
        self.g = g
        self.integ = Integradores(0.0)
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

        if g.lei != "lqr":
            u = self.integ.passo(g, self.theta, giro, self.w, contagem * g.rad_por_contagem, vbus)
            self.trim = self.integ.ref
            return u
        u = lei_controle(self.theta - self.trim, giro, self.w, vbus, g)
        if trim_ativo and abs(u) < 0.9 * g.u_frac * vbus:
            self.trim = _limita(self.trim + g.trim_ganho * self.w * g.ts, -g.trim_max, g.trim_max)
        return u
