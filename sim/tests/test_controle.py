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


# --- LQI e PID ------------------------------------------------------------------
from sim.controlador import Integradores, com_lei, discretizar_lqi  # noqa: E402


def test_polos_do_lqi_dentro_do_circulo_unitario(g):
    Ad, Bd = discretizar_lqi(NOMINAL)
    assert np.all(np.abs(np.linalg.eigvals(Ad - Bd @ g.KI)) < 1.0)


@pytest.mark.parametrize("lei", ["lqi", "pid"])
def test_lqi_e_pid_recuperam_de_5_graus(g, lei):
    r = simular(NOMINAL, com_lei(g, lei), theta0=math.radians(5.0), T=5.0, realista=True)
    assert not r.caiu
    assert r.acomodou(tol_theta=math.radians(1.0), tol_thd=0.3)
    assert np.max(np.abs(r.u)) <= NOMINAL.u_max + 1e-9
    assert r.omega_pico < NOMINAL.w_max


@pytest.mark.parametrize("lei", ["lqi", "pid"])
def test_lqi_e_pid_rejeitam_peteleco(g, lei):
    r = simular(NOMINAL, com_lei(g, lei), theta0=0.0, T=5.0, realista=True, disturbios=[(0.5, 2.0)])
    assert not r.caiu and r.acomodou(tol_theta=math.radians(1.5), tol_thd=0.3)


@pytest.mark.parametrize("lei", ["lqi", "pid"])
@pytest.mark.parametrize("nome", ["resistência +40 %", "motor mais lento (3000 rpm)", "braço +50 % de massa"])
def test_lqi_e_pid_com_erro_de_parametro(g, lei, nome):
    r = simular(NOMINAL, com_lei(g, lei), theta0=math.radians(5.0), T=6.0,
                planta=variar(NOMINAL, VARIACOES[nome]), semente=1)
    assert not r.caiu and r.acomodou(tol_theta=math.radians(1.5), tol_thd=0.5)


def test_lqi_para_a_roda_mais_rapido_que_o_auto_ajuste(g):
    """Com o MPU6050 2° torto, o LQI zera a roda em segundos; o LQR com auto-ajuste leva dezenas."""
    s = Sensores(vies_angulo=math.radians(2.0))
    lqi = simular(NOMINAL, com_lei(g, "lqi"), theta0=0.0, T=12.0, sensores=s, semente=3)
    lqr = simular(NOMINAL, g, theta0=0.0, T=12.0, sensores=s, semente=3)
    w = lambda r: abs(np.mean(r.omega[9500:10500]))   # noqa: E731  (em torno de 10 s)
    assert not lqi.caiu and w(lqi) < 1.0            # < 10 rpm
    assert w(lqr) > 5.0 * w(lqi)
    assert lqi.trim[-1] == pytest.approx(math.radians(2.0), abs=math.radians(0.3))


def test_pid_sem_a_malha_da_roda_cai_com_o_mpu_torto(g):
    """Só em theta, o PID não enxerga a roda: com viés ela dispara e o braço cai."""
    s = Sensores(vies_angulo=math.radians(2.0))
    so_theta = replace(com_lei(g, "pid"), kw=0.0, kwi=0.0)
    r = simular(NOMINAL, so_theta, theta0=0.0, T=15.0, sensores=s, semente=3)
    com = simular(NOMINAL, com_lei(g, "pid"), theta0=0.0, T=15.0, sensores=s, semente=3)
    assert r.caiu or r.omega_pico > NOMINAL.w_max
    assert not com.caiu and com.omega_pico < NOMINAL.w_max


@pytest.mark.parametrize("lei", ["lqi", "pid"])
def test_anti_windup_limita_o_integrador_da_roda(g, lei):
    gl = com_lei(g, lei)
    it = Integradores(0.0)
    for k in range(20000):   # roda girando sem parar a 100 rad/s, braço parado
        u = it.passo(gl, 0.0, 0.0, 100.0, 100.0 * k * gl.ts, NOMINAL.v_bus)
        assert abs(u) <= gl.u_frac * NOMINAL.v_bus + 1e-12
    assert abs(it.ref) <= gl.trim_max + 1e-9
