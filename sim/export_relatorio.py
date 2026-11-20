"""Gera relatorio/valores.tex: todos os números do relatório como macros LaTeX.

O texto do relatório (relatorio/relatorio.tex) nunca traz um número do modelo
digitado à mão; tudo vem daqui, calculado a partir de sim/params.py.

Uso:  python -m sim.export_relatorio
      (cd relatorio && latexmk -pdf relatorio.tex)
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from cad.folgas import derivar, ler_parametros
from .controlador import (DESVIO_OMEGA, DESVIO_THETA, DESVIO_THETA_DOT, DESVIO_U, discretizar,
                          polos_malha_fechada, projetar)
from .model import Planta
from .params import NOMINAL, Params
from .simulacao import inclinacao_maxima

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "relatorio" / "valores.tex"
RPM = 60 / (2 * math.pi)


def n(v: float, sig: int = 4) -> str:
    """Número para \\num{}: sig algarismos significativos, sem zeros sobrando.

    Notação científica só para valores menores que 1e-3; inteiros grandes
    (2000 rpm, 190 g) ficam por extenso.
    """
    if v == 0:
        return "0"
    if not math.isfinite(v):
        return "nan"
    e = math.floor(math.log10(abs(v)))
    if e < -3:
        mant, exp = f"{v:.{sig - 1}e}".split("e")
        if "." in mant:
            mant = mant.rstrip("0").rstrip(".")
        return f"{mant}e{int(exp)}"
    casas = sig - 1 - e
    if casas <= 0:
        return str(int(round(v, casas)))
    s = f"{v:.{casas}f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def matriz(m: np.ndarray, sig: int = 4) -> str:
    linhas = [" & ".join(rf"\num{{{n(float(v), sig)}}}" for v in linha) for linha in np.atleast_2d(m)]
    return r"\begin{bmatrix} " + r" \\ ".join(linhas) + r" \end{bmatrix}"


def polo(z: complex, sig: int = 3) -> str:
    if abs(z.imag) < 1e-9 * max(1.0, abs(z)):
        return rf"\num{{{n(z.real, sig)}}}"
    return rf"\num{{{n(z.real, sig)}}} \pm \num{{{n(abs(z.imag), sig)}}}\,\mathrm{{j}}"


def lista_polos(polos, sig: int = 3) -> str:
    vistos = []
    for z in sorted(polos, key=lambda z: z.real):
        if not any(abs(z - w.conjugate()) < 1e-9 and abs(z.imag) > 1e-9 for w in vistos):
            vistos.append(z)
    txt = [polo(complex(z), sig) for z in vistos]
    return ", ".join(txt[:-1]) + r" \text{ e } " + txt[-1]


def _tex(s: str) -> str:
    s = s.replace("\\", r"\textbackslash{}")
    for a, b in (("_", r"\_"), ("&", r"\&"), ("%", r"\%"), ("#", r"\#"), ("->", r"$\to$"), ("<-", r"$\leftarrow$")):
        s = s.replace(a, b)
    return s


def tabela_pinos() -> str:
    """Linhas da tabela de pinagem, lidas do comentário de firmware/include/board.h."""
    import re

    texto = (RAIZ / "firmware/include/board.h").read_text(encoding="utf-8")
    linhas = []
    for linha in texto.splitlines():
        m = re.match(r"\s*\*\s+(.+?)\s{2,}(P[ABC]\d+)\s+(.+?)\s*$", linha)
        if m:
            linhas.append(rf"\texttt{{{m.group(2)}}} & {_tex(m.group(1))} & {_tex(m.group(3))} \\")
    assert len(linhas) >= 14, "tabela de pinos de board.h não encontrada"
    return "\n".join(linhas)


def gerar(p: Params = NOMINAL) -> str:
    import control

    m, r = p.motor, p.roda
    pl = Planta(p)
    A, B = pl.linear()
    Ad, Bd = discretizar(p)
    g = projetar(p)
    Q = np.diag([1 / DESVIO_THETA**2, 1 / DESVIO_THETA_DOT**2, 1 / DESVIO_OMEGA**2])
    R = np.array([[1 / DESVIO_U**2]])
    K, P, _ = control.dlqr(Ad, Bd, Q, R)
    K = np.asarray(K)
    assert np.allclose(K.ravel(), [g.k1, g.k2, g.k3])
    ctrb = np.hstack([B, A @ B, A @ A @ B])
    polos_ma = np.linalg.eigvals(A)
    polos_z = polos_malha_fechada(p, g)
    polos_s = np.log(polos_z.astype(complex)) / p.ts
    th_max = inclinacao_maxima(p, g)
    c_lin = m.kt * m.ke / m.R + m.b_lin
    cad = derivar(ler_parametros())
    arq_massas = RAIZ / "cad" / "stl" / "massas.json"
    massas = json.loads(arq_massas.read_text(encoding="utf-8")) if arq_massas.exists() else {}

    v: dict[str, str] = {
        # motor
        "vMotorR": n(m.R), "vMotorL": n(m.L * 1e3), "vMotorNzero": n(m.n0_rpm), "vMotorIzero": n(m.i0),
        "vMotorKe": n(m.ke), "vMotorTauC": n(m.tau_c * 1e3, 3), "vMotorB": n(m.b, 3), "vMotorBeq": n(m.b_lin, 3),
        "vMotorMassa": n(m.massa * 1e3), "vMotorJ": n(m.J_rotor, 2), "vMotorTauEl": n(m.L / m.R * 1e3, 2),
        "vMotorIpartida": n(m.v_nom / m.R, 3), "vMotorTpartida": n(m.kt * m.v_nom / m.R, 3),
        # roda
        "vRodaN": str(r.n_parafusos), "vRodaMconj": n(r.m_conjunto * 1e3), "vRodaRparaf": n(r.r_parafusos * 1e3),
        "vRodaDext": n(2 * r.r_ext * 1e3), "vRodaDaleta": n(2 * r.r_aleta * 1e3), "vRodaMassa": n(p.m_w * 1e3, 3),
        "vRodaMimpressa": n(r.massa_impressa * 1e3, 2), "vRodaIw": n(p.I_w, 3), "vRodaRanhuras": str(r.n_ranhuras),
        "vRodaCpr": str(r.cpr), "vRodaEsp": n(r.espessura * 1e3),
        "vRodaForcaParaf": n(r.m_conjunto * p.w_max**2 * r.r_parafusos, 2),
        "vRodaFracParaf": n(100 * r.n_parafusos * r.m_conjunto * r.r_parafusos**2 / p.I_w, 2),
        # pêndulo
        "vLw": n(p.l_w * 1e3), "vMbraco": n(p.m_braco * 1e3), "vFracCm": n(p.frac_cm_braco), "vMextras": n(p.m_extras * 1e3),
        "vLextras": n(p.l_extras * 1e3), "vJ": n(p.J, 3), "vMgl": n(p.Mgl, 3), "vMassaTotal": n(p.massa_total * 1e3, 3),
        "vBp": n(p.b_p, 2), "vPoloInst": n(math.sqrt(p.Mgl / p.J), 3),
        "vTqueda": n(1e3 / math.sqrt(p.Mgl / p.J), 2),
        # limites
        "vVbus": n(p.v_bus), "vUmax": n(p.u_max), "vImax": n(p.i_max), "vWmax": n(p.w_max, 3),
        "vWmaxRpm": n(p.w_max * RPM, 2), "vTs": n(p.ts * 1e3), "vFs": n(1 / p.ts),
        "vTauMax": n(p.tau_max, 3), "vThetaEst": n(math.degrees(p.theta_max_estatico), 3),
        "vThetaMax": n(math.degrees(th_max), 3), "vHmax": n(p.I_w * p.w_max, 3),
        # modelo linear
        "vCoefC": n(c_lin, 3), "vCoefG": n(m.kt / m.R, 3),
        "vPostoCtrb": str(int(np.linalg.matrix_rank(ctrb))),
        # LQR
        "vDesvTheta": n(math.degrees(DESVIO_THETA)), "vDesvThetaDot": n(DESVIO_THETA_DOT), "vDesvOmega": n(DESVIO_OMEGA),
        "vDesvU": n(DESVIO_U),
        "vKum": n(g.k1), "vKdois": n(g.k2), "vKtres": n(g.k3),
        "vKumGrau": n(abs(g.k1) * math.pi / 180, 3),"vKtresRpm": n(g.k3 / RPM * 100, 3),
        "vRaioEspectral": n(float(np.max(np.abs(polos_z))), 5),
        # CAD
        "vEixoFora": n(cad["eixo_fora"]), "vDistSensores": n(cad["dist_sensores"], 3), "vBarraComp": n(cad["barra_comp"], 2),
        "vYroda": n(cad["y_roda"]), "vAnguloBatente": n(cad["angulo_batente"]), "vHpivo": n(cad["h_pivo"]),
        "vCauda": n(cad["cauda"]),
    }
    for peca in ("roda", "braco", "suporte_sensores", "base", "bandeja", "batente_tpu"):
        nome = "vCad" + "".join(t.capitalize() for t in peca.split("_"))
        d = massas.get(peca, {})
        v[nome + "Massa"] = n(d.get("massa_g", float("nan")), 2)
        v[nome + "Vol"] = n(d.get("volume_cm3", float("nan")), 3)
        v[nome + "Dim"] = r" \times ".join(f"{x:.0f}" for x in d.get("dimensoes_mm", [0, 0, 0]))
    v["vCadRodaInercia"] = n(massas.get("roda", {}).get("I_eixo_gm2", float("nan")) * 1e-3, 3)

    linhas = ["% ARQUIVO GERADO por sim/export_relatorio.py - não edite à mão.",
              "% Mude sim/params.py e rode: python -m sim.export_relatorio"]
    linhas += [rf"\newcommand{{\{k}}}{{{val}}}" for k, val in v.items()]
    linhas += [
        rf"\newcommand{{\matA}}{{{matriz(A)}}}",
        rf"\newcommand{{\matB}}{{{matriz(B)}}}",
        rf"\newcommand{{\matAd}}{{{matriz(Ad, 5)}}}",
        rf"\newcommand{{\matBd}}{{{matriz(Bd, 3)}}}",
        rf"\newcommand{{\matCtrb}}{{{matriz(ctrb, 3)}}}",
        rf"\newcommand{{\matQ}}{{{matriz(Q, 3)}}}",
        rf"\newcommand{{\matR}}{{\num{{{n(float(R[0, 0]), 3)}}}}}",
        rf"\newcommand{{\matP}}{{{matriz(np.asarray(P), 3)}}}",
        rf"\newcommand{{\matK}}{{{matriz(K)}}}",
        rf"\newcommand{{\polosMA}}{{{lista_polos(polos_ma)}}}",
        rf"\newcommand{{\polosMFz}}{{{lista_polos(polos_z, 5)}}}",
        rf"\newcommand{{\polosMFs}}{{{lista_polos(polos_s)}}}",
        r"\newcommand{\tabelaPinos}{%",
        tabela_pinos(),
        "}",
        "",
    ]
    return "\n".join(linhas)


FIGURAS = [
    "sim/out/dimensionamento.png",
    "cad/previews/montagem_0graus_iso.png",
    "cad/previews/montagem_25graus_frente.png",
    "cad/previews/montagem_lado.png",
    "cad/previews/roda.png",
    "cad/previews/braco.png",
    "cad/previews/suporte_sensores.png",
    "cad/previews/base.png",
]


def preparar_figuras(margem: int = 16) -> list[Path]:
    """Copia as figuras para relatorio/figuras/, cortando a margem vazia em volta do desenho."""
    from PIL import Image, ImageChops

    destino = SAIDA.parent / "figuras"
    destino.mkdir(exist_ok=True)
    feitas = []
    for rel in FIGURAS:
        origem = RAIZ / rel
        if not origem.exists():
            raise FileNotFoundError(f"{rel} não existe: rode sim.sizing / cad/build.sh antes")
        img = Image.open(origem).convert("RGB")
        fundo = Image.new("RGB", img.size, img.getpixel((0, 0)))
        caixa = ImageChops.difference(img, fundo).convert("L").point(lambda v: 255 if v > 12 else 0).getbbox()
        if caixa:
            l, t, r, b = caixa
            img = img.crop((max(0, l - margem), max(0, t - margem), min(img.width, r + margem), min(img.height, b + margem)))
        saida = destino / origem.name
        img.save(saida)
        feitas.append(saida)
    return feitas


def main() -> None:
    SAIDA.parent.mkdir(exist_ok=True)
    texto = gerar()
    SAIDA.write_text(texto, encoding="utf-8")
    print(f"gerado: {SAIDA.relative_to(RAIZ)} ({len(texto.splitlines())} linhas)")
    figs = preparar_figuras()
    print(f"figuras: {len(figs)} em {figs[0].parent.relative_to(RAIZ)}/")


if __name__ == "__main__":
    main()
