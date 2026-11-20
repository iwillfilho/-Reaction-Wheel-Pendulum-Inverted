"""Testes das ferramentas de bancada com dados sintéticos (sem hardware)."""
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from sim.model import Planta
from sim.params import NOMINAL
from tools.identify import identificar, identificar_pendulo
from tools.telemetry_log import CABECALHO, converter

RAIZ = Path(__file__).resolve().parents[2]


def ensaio_sintetico(duties=(0.10, 0.20, 0.30, 0.40), t_patamar=4.0, ts=0.005):
    """Roda sozinha (braço preso) respondendo a patamares de tensão, como no ensaio real."""
    pl = Planta(NOMINAL)
    dt = 1e-4
    t, u, w = [], [], []
    om, agora = 0.0, 0.0
    for d in duties:
        v = d * NOMINAL.v_bus
        for k in range(int(t_patamar / dt)):
            tau = pl.kt * pl.corrente(v, om) - pl.atrito(om)
            om += dt * tau / pl.Iw
            agora += dt
            if k % int(ts / dt) == 0:
                t.append(agora), u.append(v), w.append(om)
    return np.array(t), np.array(u), np.array(w)


def test_identificacao_recupera_os_parametros_do_modelo():
    t, u, w = ensaio_sintetico()
    r = identificar(t, u, w, R=NOMINAL.motor.R)
    m = NOMINAL.motor
    assert r["ke"] == pytest.approx(m.ke, rel=0.05)
    assert r["n0_rpm"] == pytest.approx(m.n0_rpm, rel=0.05)
    assert r["i0"] == pytest.approx(m.i0, rel=0.35)      # atrito seco + viscoso: só a ordem de grandeza
    assert r["I_w"] == pytest.approx(NOMINAL.I_w, rel=0.15)


def test_identificacao_acusa_encoder_invertido():
    t, u, w = ensaio_sintetico()
    with pytest.raises(ValueError, match="inv enc"):
        identificar(t, u, -w, R=NOMINAL.motor.R)


def test_conversao_da_linha_de_telemetria():
    # D,t_ms,estado,falha,theta_mgrau,vel_mgrau_s,roda_drpm,u_mV,vbus_mV,trim_mgrau,enc
    linha = "D,12345,3,0,-1500,25000,-1234,5600,11950,300,-42"
    campos = converter(linha.split(",")[1:]).split(",")
    assert len(campos) == len(CABECALHO.split(","))
    assert campos == ["12.345", "3", "0", "-1.500", "25.00", "-123.4", "5.600", "11.95", "0.300", "-42"]


def test_grafico_de_log(tmp_path):
    t, u, w = ensaio_sintetico(duties=(0.2, 0.3), t_patamar=2.0)
    csv = tmp_path / "ensaio.csv"
    with open(csv, "w") as f:
        f.write(CABECALHO + "\n")
        for a, b, c in zip(t, u, w):
            f.write(f"{a:.3f},4,0,22.000,0.00,{c * 60 / (2 * math.pi):.1f},{b:.3f},12.00,0.000,0\n")
    r = subprocess.run([sys.executable, str(RAIZ / "tools/plot_log.py"), str(csv)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert csv.with_suffix(".png").stat().st_size > 10_000
    r = subprocess.run([sys.executable, str(RAIZ / "tools/identify.py"), "motor", str(csv), "--R", "0.8"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "ke = kt" in r.stdout


def test_identificacao_do_pendulo_pendurado():
    """Oscilação amortecida em torno de 180° (pendurado), com a volta de ±180° no log."""
    wn, zeta = 9.0, 0.02
    t = np.arange(0, 20, 0.005)
    wd = wn * math.sqrt(1 - zeta**2)
    th = 180.0 + 10.0 * np.exp(-zeta * wn * t) * np.cos(wd * t)
    th = (th + 180.0) % 360.0 - 180.0                       # como o atan2 do firmware entrega
    th += np.random.default_rng(0).normal(0, 0.05, t.size)  # ruído
    r = identificar_pendulo(t, th)
    assert r["wn"] == pytest.approx(wn, rel=0.01)
    assert r["zeta"] == pytest.approx(zeta, rel=0.15)
