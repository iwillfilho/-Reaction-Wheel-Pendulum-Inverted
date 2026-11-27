#!/usr/bin/env python3
"""Gera plano/visualizacao_projeto.html: o projeto inteiro numa página só.

    python -m tools.gerar_visualizacao            (na raiz, com a .venv ativa)

A página abre sem internet (three.js vai embutido) e junta:
  - o pêndulo em 3D, peça por peça, com os fios (cad/visualizacao.scad);
  - o guia de montagem física convertido de plano/montagem_fisica.tex, com as
    figuras do CAD (plano/figuras/) e os desenhos TikZ compilados à parte;
  - o esquema de ligações e as tabelas de docs/ligacoes.md.

Precisa de: openscad, pdflatex, pdftocairo (poppler-utils) e trimesh (requirements).
Rode de novo depois de mudar o CAD, o guia ou as ligações.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import numpy as np
import trimesh

from tools.visualizacao.latex_html import Conversor

RAIZ = Path(__file__).resolve().parent.parent
CAD = RAIZ / "cad"
PLANO = RAIZ / "plano"
MODELO = Path(__file__).resolve().parent / "visualizacao"
SAIDA = PLANO / "visualizacao_projeto.html"
OPENSCAD = os.environ.get("OPENSCAD", "openscad")

PECAS = [
    "base", "bandeja", "tpu", "barra_colares", "protecao",
    "braco", "suporte_sensores", "motor", "sensores", "mpu", "rolamentos",
    "roda", "flange", "parafusos_m8",
]


def b64(dados: bytes) -> str:
    return base64.b64encode(dados).decode("ascii")


# ----------------------------------------------------------------------------- CAD
def exportar_peca(nome: str, tmp: Path) -> dict:
    stl = tmp / f"{nome}.stl"
    subprocess.run([OPENSCAD, "--hardwarnings", "-o", str(stl), "-D", f'parte="{nome}"',
                    "visualizacao.scad"], cwd=CAD, check=True, capture_output=True)
    malha = trimesh.load(stl, force="mesh")
    malha.merge_vertices()
    pos = np.asarray(malha.vertices, dtype=np.float32)
    idx = np.asarray(malha.faces, dtype=np.uint32).ravel()
    grande = len(pos) > 65535
    idx = idx if grande else idx.astype(np.uint16)
    return {"p": b64(pos.tobytes()), "i": b64(idx.tobytes()), "i32": grande}


def exportar_pecas() -> tuple[dict, dict]:
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        with ThreadPoolExecutor(max_workers=os.cpu_count()) as ex:
            res = dict(zip(PECAS, ex.map(lambda n: exportar_peca(n, tmp), PECAS)))
        eco = tmp / "cotas.echo"
        subprocess.run([OPENSCAD, "-o", str(eco), "-D", 'parte="cotas"', "visualizacao.scad"],
                       cwd=CAD, check=True, capture_output=True)
        cotas = {m.group(1): float(m.group(2))
                 for m in re.finditer(r"ECHO: (\w+) = ([-\d.e]+)", eco.read_text())}
    return res, cotas


# ----------------------------------------------------------------------- guia .tex
def macros_ilustracao() -> dict[str, int]:
    txt = (PLANO / "ilustracoes.tex").read_text()
    return {m.group(1): int(m.group(2) or 0)
            for m in re.finditer(r"\\newcommand\{\\(il[A-Za-z]+)\}(?:\[(\d)\])?", txt)}


def compilar_tikz(snippets: list[str], tex: str) -> list[str]:
    """Compila cada desenho numa página de um documento standalone; devolve data URIs."""
    pre = tex.split("\\begin{document}")[0]
    pre = re.sub(r"^\\documentclass.*$", "", pre, count=1, flags=re.M)
    fora = ("geometry", "fancyhdr", "\\pagestyle", "\\fancy", "headrulewidth", "hyperref",
            "\\hypersetup", "pdftitle", "pdfauthor")
    pre = "\n".join(l for l in pre.splitlines() if not any(f in l for f in fora))
    pre = pre.replace("\\graphicspath{{figuras/}}", "\\graphicspath{{%s/figuras/}}" % PLANO)
    doc = ("\\documentclass[varwidth=17cm,border=4pt,multi=figtikz]{standalone}\n" + pre
           + "\n\\begin{document}\n"
           + "\n".join(f"\\begin{{figtikz}}{s}\\end{{figtikz}}" for s in snippets)
           + "\n\\end{document}\n")
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        (tmp / "tikz.tex").write_text(doc)
        r = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "tikz.tex"],
                           cwd=tmp, env={**os.environ, "TEXINPUTS": f"{PLANO}//:"},
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit("pdflatex falhou nos desenhos:\n" + r.stdout[-2000:])
        uris = []
        for k in range(1, len(snippets) + 1):
            svg = tmp / f"p{k}.svg"
            subprocess.run(["pdftocairo", "-svg", "-f", str(k), "-l", str(k), "tikz.pdf", svg.name],
                           cwd=tmp, check=True)
            png = tmp / f"p{k}"
            subprocess.run(["pdftoppm", "-png", "-r", "170", "-singlefile", "-f", str(k), "-l", str(k),
                            "tikz.pdf", png.name], cwd=tmp, check=True)
            a, b = svg.read_bytes(), (tmp / f"p{k}.png").read_bytes()
            uris.append("data:image/svg+xml;base64," + b64(a) if len(a) <= len(b)
                        else "data:image/png;base64," + b64(b))
    return uris


def guia() -> dict:
    tex = (PLANO / "montagem_fisica.tex").read_text()
    conv = Conversor(macros_ilustracao())
    corpo = conv.documento(tex)
    if conv.desconhecidas:
        print("aviso: macros não tratadas no guia:", dict(conv.desconhecidas))
    figuras = {n: "data:image/png;base64," + b64((PLANO / "figuras" / f"{n}.png").read_bytes())
               for n in sorted(conv.figuras)}
    return {"html": corpo, "tarefas": conv.tarefas, "secoes": conv.secoes,
            "figuras": figuras, "tikz": compilar_tikz(conv.snippets, tex)}


# ------------------------------------------------------------------- markdown
def md_inline(s: str) -> str:
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


def tabelas_md(md: str) -> dict[str, dict]:
    """Cada tabela do markdown, com o título da seção (##/###) em que ela está."""
    tabs, titulo, linhas = {}, "", md.splitlines()
    i = 0
    while i < len(linhas):
        l = linhas[i]
        if l.startswith("#"):
            titulo = l.lstrip("#").strip()
        if l.startswith("|") and i + 1 < len(linhas) and re.match(r"^\|[-| :]+\|$", linhas[i + 1]):
            cab = [md_inline(c.strip()) for c in l.strip("|").split("|")]
            corpo = []
            i += 2
            while i < len(linhas) and linhas[i].startswith("|"):
                corpo.append([md_inline(c.strip()) for c in linhas[i].strip("|").split("|")])
                i += 1
            tabs[titulo] = {"cab": cab, "linhas": corpo}
            continue
        i += 1
    return tabs


def regras_de_ouro(md: str) -> list[str]:
    bloco = re.search(r"> \*\*Regras de ouro\*\*\n((?:>.*\n)+)", md)
    if not bloco:
        return []
    return [md_inline(re.sub(r"^>\s*\d+\.\s*", "", l)) for l in bloco.group(1).splitlines()
            if re.match(r"^>\s*\d+\.", l)]


def resumo_readme() -> list[list[str]]:
    md = (RAIZ / "README.md").read_text()
    sec = md.split("## Resultados da simulação", 1)[1].split("\n## ", 1)[0]
    linhas = []
    for l in sec.splitlines():
        if l.startswith("|") and not re.match(r"^\|[-| :]*\|$", l):
            c = [md_inline(x.strip()) for x in l.strip("|").split("|")]
            if any(c):
                linhas.append(c)
    return linhas


def versao() -> str:
    try:
        h = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ, capture_output=True,
                           text=True, check=True).stdout.strip()
        sujo = subprocess.run(["git", "status", "--porcelain"], cwd=RAIZ, capture_output=True,
                              text=True).stdout.strip()
        return h + (" + alterações locais" if sujo else "")
    except (OSError, subprocess.CalledProcessError):
        return "?"


# ---------------------------------------------------------------------- página
def json_script(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--saida", type=Path, default=SAIDA)
    args = ap.parse_args()

    print("== peças do CAD (OpenSCAD)")
    pecas, cotas = exportar_pecas()
    print("== guia de montagem e desenhos TikZ")
    g = guia()
    print("== ligações")
    md = (RAIZ / "docs" / "ligacoes.md").read_text()
    tabs = tabelas_md(md)
    ligacoes = {
        "pinagem": tabs["Pinagem da Black Pill"],
        "modulos": tabs["Alimentação dos módulos"],
        "led": tabs["LED da placa (PC13)"],
        "regras": regras_de_ouro(md),
    }
    massas = json.loads((CAD / "stl" / "massas.json").read_text())

    dados = {
        "pecas": pecas, "cotas": cotas, "massas": massas, "ligacoes": ligacoes,
        "tarefas": g["tarefas"], "secoes": g["secoes"], "figuras": g["figuras"],
        "tikz": g["tikz"], "resumo": resumo_readme(),
        "versao": versao(), "data": date.today().strftime("%d/%m/%Y"),
    }
    vendor = MODELO / "vendor" / "three-r147"
    modelo = (MODELO / "modelo.html").read_text()
    trocas = {
        "/*ESTILO*/": (MODELO / "estilo.css").read_text(),
        "/*THREE*/": (vendor / "three.min.js").read_text() + "\n" + (vendor / "OrbitControls.js").read_text(),
        "/*DADOS*/": "const DADOS = " + json_script(dados) + ";",
        "<!--GUIA-->": g["html"],
        "/*CENA3D*/": (MODELO / "cena3d.js").read_text(),
        "/*PAGINA*/": (MODELO / "pagina.js").read_text(),
    }
    for k in trocas:
        assert modelo.count(k) == 1, k
    # uma passada só: o texto inserido nunca é relido como marcador
    padrao = re.compile("|".join(re.escape(k) for k in trocas))
    args.saida.write_text(padrao.sub(lambda m: trocas[m.group(0)], modelo))
    print(f"Pronto: {args.saida.relative_to(RAIZ)} ({args.saida.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
