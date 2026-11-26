"""Gera, a partir de sim/params.py, tudo o que as outras partes do projeto usam:

  firmware/lib/control/lqr_gains.h        ganhos, limites e constantes do motor
  firmware/test/test_control/vectors.h    vetores de teste (C conferido contra Python)
  cad/dimensoes_geradas.scad              dimensões da roda e do braço

Uso:  python -m sim.export_gains
Rode de novo sempre que mudar um parâmetro medido.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

from .controlador import Integradores, com_lei, lei_controle, projetar
from .model import Planta
from .params import NOMINAL, Params
from .simulacao import simular

RAIZ = Path(__file__).resolve().parent.parent
AVISO = "ARQUIVO GERADO por sim/export_gains.py - não edite à mão; mude sim/params.py e gere de novo."

# Limites de segurança do firmware (não saem do LQR, são decisões de projeto)
THETA_CORTE = math.radians(20.0)     # acima disso desliga: fora da faixa recuperável
THETA_BATENTE = math.radians(25.0)   # onde o batente mecânico segura o braço
THETA_ENGATE = math.radians(3.0)     # janela para começar a equilibrar
THETA_DOT_ENGATE = 0.5               # rad/s
VBUS_MIN = 9.0
VBUS_MAX = 16.5


def _f(v: float) -> str:
    """Literal float de C (precisa de ponto ou expoente: '10f' não compila)."""
    s = f"{v:.9g}"
    if not any(c in s for c in ".en"):
        s += ".0"
    return s + "f"


def gerar_ganhos(p: Params, g) -> str:
    m = p.motor
    linhas = [
        f"/* {AVISO} */",
        "#ifndef LQR_GAINS_H",
        "#define LQR_GAINS_H",
        "",
        "/* Lei de controle: u = -(K1*theta + K2*theta_dot + K3*omega)  [V] */",
        f"#define RWP_K1            ({_f(g.k1)})   /* V/rad      */",
        f"#define RWP_K2            ({_f(g.k2)})   /* V/(rad/s)  */",
        f"#define RWP_K3            ({_f(g.k3)})   /* V/(rad/s)  */",
        f"#define RWP_TS            ({_f(g.ts)})   /* s          */",
        "",
        "/* Limites elétricos */",
        f"#define RWP_U_FRAC        ({_f(g.u_frac)})   /* fração máxima da tensão do barramento */",
        f"#define RWP_I_MAX         ({_f(g.i_max)})   /* A */",
        f"#define RWP_KE            ({_f(g.ke)})   /* V.s/rad  (modelo do motor) */",
        f"#define RWP_R_MOTOR       ({_f(g.R)})   /* ohm */",
        f"#define RWP_VBUS_NOM      ({_f(p.v_bus)})   /* V */",
        f"#define RWP_VBUS_MIN      ({_f(VBUS_MIN)})",
        f"#define RWP_VBUS_MAX      ({_f(VBUS_MAX)})",
        "",
        "/* Estimadores */",
        f"#define RWP_ALPHA_CF      ({_f(g.alfa_cf)})   /* filtro complementar */",
        f"#define RWP_ALPHA_W       ({_f(g.alfa_w)})   /* passa-baixa da velocidade da roda */",
        f"#define RWP_ENC_CPR       ({p.roda.cpr})        /* contagens por volta (4 x {p.roda.n_ranhuras} ranhuras) */",
        f"#define RWP_RAD_PER_COUNT ({_f(g.rad_por_contagem)})",
        "",
        "/* Auto-ajuste do ângulo de equilíbrio: trim' = TRIM_GAIN * omega */",
        f"#define RWP_TRIM_GAIN     ({_f(g.trim_ganho)})",
        f"#define RWP_TRIM_MAX      ({_f(g.trim_max)})   /* rad */",
        "",
        "/* LQI: u = -(Q1*theta + Q2*theta_dot + Q3*omega + Q4*phi_r)  [V], phi_r = ângulo da roda */",
        f"#define RWP_Q1            ({_f(g.q1)})   /* V/rad      */",
        f"#define RWP_Q2            ({_f(g.q2)})   /* V/(rad/s)  */",
        f"#define RWP_Q3            ({_f(g.q3)})   /* V/(rad/s)  */",
        f"#define RWP_Q4            ({_f(g.q4)})   /* V/rad      */",
        "",
        "/* PID: u = KP*e + KI*int(e) + KD*theta_dot, e = theta - theta_ref,",
        "        theta_ref = -(KW*omega + KWI*phi_r)  (malha externa na roda) */",
        f"#define RWP_PID_KP        ({_f(g.kp)})   /* V/rad      */",
        f"#define RWP_PID_KI        ({_f(g.ki)})   /* V/(rad.s)  */",
        f"#define RWP_PID_KD        ({_f(g.kd)})   /* V/(rad/s)  */",
        f"#define RWP_PID_KW        ({_f(g.kw)})   /* rad por rad/s */",
        f"#define RWP_PID_KWI       ({_f(g.kwi)})   /* rad por rad   */",
        f"#define RWP_PID_I_MAX     ({_f(g.pid_i_max)})   /* rad.s */",
        "",
        "/* Segurança */",
        f"#define RWP_THETA_CUT     ({_f(THETA_CORTE)})   /* rad ({math.degrees(THETA_CORTE):.0f} graus) */",
        f"#define RWP_THETA_ENGAGE  ({_f(THETA_ENGATE)})   /* rad ({math.degrees(THETA_ENGATE):.0f} graus) */",
        f"#define RWP_THETADOT_ENGAGE ({_f(THETA_DOT_ENGATE)}) /* rad/s */",
        f"#define RWP_W_MAX         ({_f(p.w_max)})   /* rad/s ({p.w_max * 60 / (2 * math.pi):.0f} rpm) */",
        "",
        "#endif /* LQR_GAINS_H */",
        "",
    ]
    return "\n".join(linhas)


def gerar_vetores(p: Params, g, n_lei: int = 96, n_seq: int = 1500) -> str:
    rng = random.Random(7)
    lei = []
    for _ in range(n_lei):
        th = rng.uniform(-0.35, 0.35) * rng.choice((1.0, 0.1, 0.01))
        thd = rng.uniform(-4.0, 4.0) * rng.choice((1.0, 0.1))
        om = rng.uniform(-p.w_max, p.w_max)
        vb = rng.uniform(9.5, 14.0)
        lei.append((th, thd, om, vb, lei_controle(th, thd, om, vb, g)))

    theta0 = math.radians(6.0)
    r = simular(p, g, theta0=theta0, T=n_seq * p.ts, realista=True, disturbios=[(0.7, -1.5)], semente=11)
    seq = r.extras["entradas"]
    assert not r.caiu and len(seq) == n_seq

    pl = Planta(p)
    out = [
        f"/* {AVISO} */",
        "#ifndef TEST_VECTORS_H",
        "#define TEST_VECTORS_H",
        "",
        "/* Lei de controle: {theta_e, theta_dot, omega, vbus, u_esperado} */",
        f"#define N_LAW {n_lei}",
        "static const float LAW_VEC[N_LAW][5] = {",
    ]
    out += [f"    {{{_f(a)}, {_f(b)}, {_f(c)}, {_f(d)}, {_f(e)}}}," for a, b, c, d, e in lei]
    out += [
        "};",
        "",
        "/* Sequência em malha fechada gravada da simulação realista:",
        "   {theta_acel, giro, u_esperado} e a contagem do encoder em SEQ_COUNT. */",
        f"#define N_SEQ {n_seq}",
        f"#define SEQ_THETA0 ({_f(theta0)})",
        f"#define SEQ_VBUS   ({_f(p.v_bus)})",
        "static const float SEQ_VEC[N_SEQ][3] = {",
    ]
    out += [f"    {{{_f(a)}, {_f(b)}, {_f(u)}}}," for a, b, _, u in seq]
    out += ["};", "static const int SEQ_COUNT[N_SEQ] = {"]
    cont = [str(c) for _, _, c, _ in seq]
    out += ["    " + ", ".join(cont[i:i + 16]) + "," for i in range(0, n_seq, 16)]
    out += [
        "};",
        "",
    ]
    for lei in ("lqi", "pid"):
        rl = simular(p, com_lei(g, lei), theta0=theta0, T=n_seq * p.ts, realista=True,
                     disturbios=[(0.7, -1.5)], semente=11)
        sl = rl.extras["entradas"]
        assert not rl.caiu and len(sl) == n_seq
        nome = lei.upper()
        out += [
            "",
            f"/* Mesma sequência com a lei {nome}: {{theta_acel, giro, u_esperado}} e a contagem. */",
            f"static const float SEQ_{nome}_VEC[N_SEQ][3] = {{",
        ]
        out += [f"    {{{_f(a)}, {_f(b)}, {_f(u)}}}," for a, b, _, u in sl]
        out += ["};", f"static const int SEQ_{nome}_COUNT[N_SEQ] = {{"]
        cl = [str(c) for _, _, c, _ in sl]
        out += ["    " + ", ".join(cl[i:i + 16]) + "," for i in range(0, n_seq, 16)]
        out += ["};"]
    # Integradores do LQI e do PID sozinhos, com saturação e roda disparando: exercita o anti-windup.
    n_int = 600
    out += ["", f"#define N_INT {n_int}",
            "/* rwp_balance_law(): {theta, theta_dot, omega, phi, vbus, u_esperado, ref_esperado} */"]
    for lei in ("lqi", "pid"):
        gl, it, phi = com_lei(g, lei), Integradores(0.0), 0.0
        linhas = []
        for k in range(n_int):
            t = k * p.ts
            th = 0.12 * math.sin(2.0 * math.pi * 1.5 * t) + (0.25 if 200 <= k < 260 else 0.0)
            thd = 0.12 * 2.0 * math.pi * 1.5 * math.cos(2.0 * math.pi * 1.5 * t)
            om = 150.0 * math.sin(2.0 * math.pi * 0.8 * t) + (120.0 if k >= 400 else 0.0)
            phi += om * p.ts
            vb = 12.0 - 1.5 * math.sin(2.0 * math.pi * 0.5 * t)
            u = it.passo(gl, th, thd, om, phi, vb)
            linhas.append((th, thd, om, phi, vb, u, it.ref))
        out += [f"static const float INT_{lei.upper()}_VEC[N_INT][7] = {{"]
        out += ["    {" + ", ".join(_f(v) for v in ln) + "}," for ln in linhas]
        out += ["};"]
    out += [
        "",
        "/* Planta nominal, para o teste de malha fechada em C */",
        f"#define PLANT_J     ({_f(pl.J)})",
        f"#define PLANT_IW    ({_f(pl.Iw)})",
        f"#define PLANT_MGL   ({_f(pl.Mgl)})",
        f"#define PLANT_BP    ({_f(pl.bp)})",
        f"#define PLANT_KT    ({_f(pl.kt)})",
        f"#define PLANT_KE    ({_f(pl.ke)})",
        f"#define PLANT_R     ({_f(pl.R)})",
        f"#define PLANT_TAU_C ({_f(pl.tau_c)})",
        f"#define PLANT_B     ({_f(pl.b)})",
        "",
        "#endif /* TEST_VECTORS_H */",
        "",
    ]
    return "\n".join(out)


def gerar_scad(p: Params) -> str:
    r = p.roda
    mm = lambda v: f"{v * 1e3:.3f}".rstrip("0").rstrip(".")
    return "\n".join(
        [
            f"// {AVISO}",
            "// Unidades: mm. Estas dimensões saem do dimensionamento (sim/sizing.py).",
            "",
            f"l_w            = {mm(p.l_w)};   // pivô -> eixo do motor",
            f"n_parafusos    = {r.n_parafusos};",
            f"r_parafusos    = {mm(r.r_parafusos)};   // raio do círculo de parafusos M8",
            f"r_aro_int      = {mm(r.r_aro_int)};",
            f"r_ext          = {mm(r.r_ext)};   // raio externo do aro",
            f"r_aleta        = {mm(r.r_aleta)};   // raio externo do anel dentado do encoder",
            f"esp_roda       = {mm(r.espessura)};",
            f"esp_alma       = {mm(r.esp_alma)};",
            f"r_cubo         = {mm(r.r_cubo)};",
            f"n_raios        = {r.n_raios};",
            f"larg_raio      = {mm(r.larg_raio)};",
            f"esp_aleta      = {mm(r.esp_aleta)};",
            f"n_ranhuras     = {r.n_ranhuras};",
            f"furo_m8        = {mm(r.furo_m8)};",
            f"angulo_batente = {math.degrees(THETA_BATENTE):.0f};   // graus: onde o batente segura o braço",
            "",
        ]
    )


def main() -> None:
    p = NOMINAL
    g = projetar(p)
    saidas = {
        RAIZ / "firmware/lib/control/lqr_gains.h": gerar_ganhos(p, g),
        RAIZ / "firmware/test/test_control/vectors.h": gerar_vetores(p, g),
        RAIZ / "cad/dimensoes_geradas.scad": gerar_scad(p),
    }
    for caminho, texto in saidas.items():
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(texto, encoding="utf-8")
        print(f"gerado: {caminho.relative_to(RAIZ)}  ({len(texto.splitlines())} linhas)")
    print(f"K = [{g.k1:.2f}, {g.k2:.3f}, {g.k3:.5f}]")


if __name__ == "__main__":
    main()
