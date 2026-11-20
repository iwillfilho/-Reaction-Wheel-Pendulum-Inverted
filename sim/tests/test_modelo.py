"""Testes do modelo físico: leis de conservação e consistência das deduções."""
import math
import random

import numpy as np
import pytest

from sim.derivacao import funcao_numerica
from sim.model import Planta
from sim.params import NOMINAL, Params


@pytest.fixture(scope="module")
def planta() -> Planta:
    return Planta(NOMINAL)


def test_energia_conservada_sem_motor_nem_atrito(planta):
    """Sem torque e sem atrito a energia mecânica não pode mudar."""
    x = (0.3, 0.0, 50.0)
    e0 = planta.energia(x)
    f = lambda x, tau: planta.deriv_tau(x, tau, bp=0.0)
    for _ in range(20000):  # 2 s
        x = planta.rk4(f, x, 0.0, 1e-4)
    assert abs(planta.energia(x) - e0) / abs(e0) < 1e-8
    assert abs(x[0]) > 0.3  # o pêndulo realmente caiu, o teste não é trivial


def test_momento_angular_so_muda_pela_gravidade(planta):
    """O torque do motor é interno: dH/dt = Mgl·sin(theta) para qualquer torque."""
    rng = random.Random(1)
    x = (0.05, 0.2, -30.0)
    h = planta.momento_angular(x)
    integral = 0.0
    dt = 1e-4
    f = lambda x, tau: planta.deriv_tau(x, tau, bp=0.0)
    for k in range(10000):
        tau = 0.2 * math.sin(40 * k * dt) + rng.uniform(-0.05, 0.05)
        x_novo = planta.rk4(f, x, tau, dt)
        integral += 0.5 * planta.Mgl * (math.sin(x[0]) + math.sin(x_novo[0])) * dt
        x = x_novo
    assert planta.momento_angular(x) - h == pytest.approx(integral, rel=1e-5, abs=1e-8)


def test_modelo_igual_a_deducao_de_lagrange(planta):
    """sim/model.py tem que coincidir com as equações deduzidas pelo SymPy."""
    f = funcao_numerica()
    rng = random.Random(2)
    for _ in range(200):
        th, thd, om = rng.uniform(-1, 1), rng.uniform(-5, 5), rng.uniform(-300, 300)
        tau = rng.uniform(-0.4, 0.4)
        esperado = f(th, thd, om, tau, planta.J, planta.Iw, planta.Mgl, planta.bp)
        d = planta.deriv_tau((th, thd, om), tau)
        assert d[1] == pytest.approx(esperado[0], rel=1e-9, abs=1e-9)
        assert d[2] == pytest.approx(esperado[1], rel=1e-9, abs=1e-9)


def test_linearizacao_igual_ao_jacobiano_numerico():
    """A, B analíticos contra diferenças finitas do modelo não linear.

    O atrito seco não é diferenciável em omega = 0, então a comparação usa
    um motor sem atrito seco (toda a perda em vazio como atrito viscoso).
    """
    p = NOMINAL.com(motor__frac_coulomb=0.0)
    pl = Planta(p)
    A, B = pl.linear()
    h = 1e-6
    x0 = np.zeros(3)
    f = lambda x, u: np.array(pl.deriv(tuple(x), u))
    A_num = np.column_stack([(f(x0 + h * e, 0.0) - f(x0 - h * e, 0.0)) / (2 * h) for e in np.eye(3)])
    B_num = ((f(x0, h) - f(x0, -h)) / (2 * h)).reshape(3, 1)
    assert np.allclose(A, A_num, rtol=1e-6, atol=1e-6)
    assert np.allclose(B, B_num, rtol=1e-6, atol=1e-6)


def test_planta_em_malha_aberta_e_instavel(planta):
    A, _ = planta.linear()
    polos = np.linalg.eigvals(A)
    assert sum(z.real > 0 for z in polos) == 1
    assert max(z.real for z in polos) == pytest.approx(math.sqrt(planta.Mgl / planta.J), rel=0.05)


def test_sinais_da_convencao(planta):
    """Tensão positiva acelera a roda no sentido positivo e empurra o pêndulo no negativo."""
    d = planta.deriv((0.0, 0.0, 0.0), 6.0)
    assert d[2] > 0 and d[1] < 0


def test_inercia_da_roda_dominada_pelos_parafusos():
    r = NOMINAL.roda
    i_paraf = r.n_parafusos * r.m_conjunto * r.r_parafusos**2
    assert 0.5 < i_paraf / r.inercia < 0.95
    assert Params().I_w > r.inercia
