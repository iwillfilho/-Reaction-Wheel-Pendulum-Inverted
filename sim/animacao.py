"""Simulação animada no OpenSCAD.

Roda o modelo não linear com o controlador (sensores realistas), grava a
trajetória em cad/animacao_dados.scad e, opcionalmente, renderiza os quadros
no OpenSCAD e junta tudo num GIF.

Uso:
    python -m sim.animacao                    # só gera cad/animacao_dados.scad
    python -m sim.animacao --renderizar       # + quadros e cad/previews/simulacao.gif

Para ver dentro do OpenSCAD: abra cad/simulacao.scad, menu View > Animate,
FPS = 25 e Steps = número de quadros (aparece no console ao abrir o arquivo).
"""
from __future__ import annotations

import argparse
import math
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from .controlador import projetar
from .params import NOMINAL
from .simulacao import simular

RAIZ = Path(__file__).resolve().parent.parent
CAD = RAIZ / "cad"
FPS = 25
RPM = 60 / (2 * math.pi)

# Roteiro: solto a 15° com o controle ligado, depois dois petelecos no braço.
THETA0_GRAUS = 15.0
PETELECOS = [(2.2, -2.5), (3.8, 2.0)]   # (instante [s], degrau de velocidade [rad/s])
DURACAO = 5.6
CAMERA = "0,0,80,90,0,180,980"            # frente, enquadramento fixo
TAMANHO = (800, 720)


def simular_roteiro():
    p = NOMINAL
    g = projetar(p)
    r = simular(p, g, theta0=math.radians(THETA0_GRAUS), T=DURACAO, realista=True, disturbios=PETELECOS, semente=3)
    if r.caiu:
        raise RuntimeError("O pêndulo caiu na simulação: reduza THETA0_GRAUS ou os petelecos.")
    phi = np.concatenate([[0.0], np.cumsum(0.5 * (r.omega[1:] + r.omega[:-1]) * np.diff(r.t))])
    return r, phi


def gerar_dados(r, phi) -> int:
    passo = int(round(1.0 / (FPS * (r.t[1] - r.t[0]))))
    idx = np.arange(0, len(r.t), passo)
    th = np.degrees(r.theta[idx])
    gi = np.degrees(phi[idx]) % 360.0
    legendas = []
    for k in idx:
        t = r.t[k]
        nota = next((" - peteleco!" for tp, _ in PETELECOS if 0 <= t - tp < 0.4), "")
        legendas.append(
            [f"t = {t:4.2f} s{nota}".replace(".", ","),
             f"inclinação = {math.degrees(r.theta[k]):+5.1f}°".replace(".", ","),
             f"roda = {r.omega[k] * RPM:+5.0f} rpm",
             f"motor = {r.u[k]:+5.1f} V".replace(".", ",")]
        )
    fmt = lambda v: ", ".join(f"{x:.3f}" for x in v)
    texto = "\n".join(
        [
            "// ARQUIVO GERADO por sim/animacao.py - não edite à mão.",
            f"// Roteiro: solto a {THETA0_GRAUS:.0f} graus, petelecos em "
            + ", ".join(f"{t:.1f} s" for t, _ in PETELECOS) + f"; {FPS} quadros por segundo.",
            f"n_quadros = {len(idx)};",
            f"anim_fps = {FPS};",
            f"anim_theta = [{fmt(th)}];",
            f"anim_giro = [{fmt(gi)}];",
            "anim_legenda = [",
            *[f'    ["{a}", "{b}", "{c}", "{d}"],' for a, b, c, d in legendas],
            "];",
            "",
        ]
    )
    (CAD / "animacao_dados.scad").write_text(texto, encoding="utf-8")
    return len(idx)


def renderizar(n: int, saida: Path, trabalhos: int = 4) -> None:
    openscad = shutil.which("openscad")
    if not openscad:
        raise SystemExit("OpenSCAD não encontrado (sudo apt install openscad).")
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        def quadro(k: int) -> Path:
            png = Path(tmp) / f"q{k:04d}.png"
            subprocess.run(
                [openscad, "--hardwarnings", "-o", str(png), f"--imgsize={TAMANHO[0]},{TAMANHO[1]}",
                 "--colorscheme=Tomorrow", f"--camera={CAMERA}", "-D", f"quadro={k}", str(CAD / "simulacao.scad")],
                check=True, capture_output=True,
            )
            return png

        with ThreadPoolExecutor(trabalhos) as ex:
            pngs = list(ex.map(quadro, range(n)))
        imagens = [Image.open(p).convert("RGB").quantize(colors=96, method=Image.Quantize.MEDIANCUT) for p in pngs]
        saida.parent.mkdir(parents=True, exist_ok=True)
        imagens[0].save(saida, save_all=True, append_images=imagens[1:], duration=int(1000 / FPS), loop=0, optimize=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--renderizar", action="store_true", help="gera os quadros no OpenSCAD e o GIF")
    a = ap.parse_args()
    r, phi = simular_roteiro()
    n = gerar_dados(r, phi)
    print(f"cad/animacao_dados.scad: {n} quadros ({DURACAO:.1f} s a {FPS} fps)")
    print(f"pico de inclinação {math.degrees(np.max(np.abs(r.theta))):.1f}°, roda até {np.max(np.abs(r.omega)) * RPM:.0f} rpm, "
          f"corrente até {np.max(np.abs(r.i)):.1f} A")
    if a.renderizar:
        gif = CAD / "previews" / "simulacao.gif"
        renderizar(n, gif)
        print(f"GIF: {gif} ({gif.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
