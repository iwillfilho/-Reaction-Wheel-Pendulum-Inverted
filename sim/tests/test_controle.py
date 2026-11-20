"""Testes do controlador: estabilidade, limites, robustez e auto-ajuste."""
import math
from dataclasses import replace

import numpy as np
import pytest

from sim.controlador import Controlador, lei_controle, polos_malha_fechada, projetar
from sim.lqr_design import VARIACOES, variar
from sim.params import NOMINAL
from sim.simulacao import Sensores, inclinacao_maxima, simular


@pytest.fixture(scope="module")
def g():
    return projetar(NOMINAL)


def test_polos_dentro_do_circulo_unitario(g):
    assert np.all(np.abs(polos_malha_fechada(NOMINAL, g)) < 1.0)


@pytest.mark.parametrize("nome", list(VARIACOES))
def test_estavel_com_erro_de_parametro(g, nome):
    """Os ganhos nominais têm que estabilizar a planta com parâmetros errados."""
    real = variar(NOMINAL, VARIACOES[nome])
    assert np.all(np.abs(polos_malha_fechada(real, g)) < 1.0)


def test_recupera_de_5_graus_com_sensores_realistas(g):
    r = simular(NOMINAL, g, theta0=math.radians(5.0), T=5.0, realista=True)
    assert not r.caiu
    assert r.acomodou(tol_theta=math.radians(1.0), tol_thd=0.3)
    assert r.i_pico <= NOMINAL.i_max * 1.15      # pequeno excesso pelo atraso elétrico
    assert np.max(np.abs(r.u)) <= NOMINAL.u_max + 1e-9
    assert r.omega_pico < NOMINAL.w_max


def test_cai_quando_a_inclinacao_e_grande_demais(g):
    """Além do limite estático de torque não há controlador que salve."""
    r = simular(NOMINAL, g, theta0=NOMINAL.theta_max_estatico + math.radians(3.0), T=2.0, realista=False)
    assert r.caiu


def test_inclinacao_maxima_coerente_com_o_limite_estatico(g):
    th = inclinacao_maxima(NOMINAL, g)
    assert math.radians(8.0) < th < NOMINAL.theta_max_estatico


def test_rejeita_peteleco(g):
    r = simular(NOMINAL, g, theta0=0.0, T=5.0, realista=True, disturbios=[(0.5, 2.0)])
    assert not r.caiu and r.acomodou(tol_theta=math.radians(1.5), tol_thd=0.3)


def test_auto_ajuste_aprende_o_erro_de_montagem(g):
    vies = math.radians(2.0)
    s = Sensores(vies_angulo=vies)
    com = simular(NOMINAL, g, theta0=0.0, T=40.0, sensores=s)
    sem = simular(NOMINAL, replace(g, trim_ganho=0.0), theta0=0.0, T=40.0, sensores=s)
    assert not com.caiu
    assert com.trim[-1] == pytest.approx(vies, abs=math.radians(0.3))
    # sem o ajuste a roda fica girando para sempre; com ele, volta para perto de zero
    assert abs(np.mean(com.omega[-3000:])) < 0.25 * abs(np.mean(sem.omega[-3000:]))


def test_limite_de_corrente_e_de_tensao(g):
    for th, thd, om in [(0.3, 0, 0), (-0.3, 0, 0), (0.3, 0, 150), (-0.3, 0, 150), (0, 5, -150), (0.01, 0, 0)]:
        u = lei_controle(th, thd, om, NOMINAL.v_bus, g)
        assert abs(u) <= g.u_frac * NOMINAL.v_bus + 1e-12
        assert abs((u - g.ke * om) / g.R) <= g.i_max + 1e-9


def test_estimador_de_velocidade_em_baixa_e_alta_rotacao(g):
    """Erro pequeno tanto com várias contagens por período quanto com uma a cada muitos."""
    for w_real in (1.0, 3.0, 20.0, 30.0, 47.0, 150.0, -80.0, -200.0):
        c = Controlador(g)
        phi = 0.0
        for _ in range(3000):
            phi += w_real * g.ts
            w = c.velocidade_roda(math.floor(phi / g.rad_por_contagem))
        assert w == pytest.approx(w_real, rel=0.08, abs=0.5)


def test_estimador_decai_quando_a_roda_para(g):
    c = Controlador(g)
    phi = 0.0
    for _ in range(500):
        phi += 30.0 * g.ts
        c.velocidade_roda(math.floor(phi / g.rad_por_contagem))
    parado = math.floor(phi / g.rad_por_contagem)
    for _ in range(1500):
        w = c.velocidade_roda(parado)
    assert abs(w) < 0.5
