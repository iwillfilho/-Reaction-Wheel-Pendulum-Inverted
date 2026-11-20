#!/usr/bin/env python3
"""Confere folgas e interferências do CAD sem precisar do OpenSCAD.

Lê os números de cad/params.scad e cad/dimensoes_geradas.scad, refaz as contas
de cad/derivados.scad e testa as distâncias críticas, inclusive com o pêndulo
girando até os batentes.

Uso:  python cad/folgas.py        (sai com código 1 se alguma folga falhar)
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import numpy as np

PASTA = Path(__file__).resolve().parent
LINHA = re.compile(r"^\s*([A-Za-z_]\w*)\s*=\s*(-?\d+(?:\.\d+)?)\s*;")


def ler_parametros() -> dict[str, float]:
    p: dict[str, float] = {}
    for nome in ("dimensoes_geradas.scad", "params.scad"):
        for linha in (PASTA / nome).read_text(encoding="utf-8").splitlines():
            m = LINHA.match(linha)
            if m:
                p[m.group(1)] = float(m.group(2))
    return p


def derivar(p: dict[str, float]) -> dict[str, float]:
    """Mesmas contas de derivados.scad."""
    d = dict(p)
    d["eixo_fora"] = p["motor_eixo_comp"] + p["motor_ressalto_h"] - p["esp_face_motor"]
    d["ressalto_fim"] = p["motor_ressalto_h"] - p["esp_face_motor"]
    d["y_roda_frente"] = p["y_roda"] + p["esp_roda"]
    d["y_alma"] = d["y_roda_frente"] - p["esp_alma"]
    d["y_flange"] = d["y_alma"] - p["flange_esp"]
    d["y_cubo"] = d["y_flange"] - p["flange_cubo_comp"]
    d["y_aleta"] = d["y_roda_frente"] - p["esp_aleta"] / 2
    d["r_feixe"] = p["r_aleta"] - p["sens_penetra"] + p["sens_feixe"]
    d["h_prateleira"] = p["l_w"] - (p["r_aleta"] - p["sens_penetra"] + p["sens_torre_h"] + p["sens_pcb"])
    ang = 1.25 * 360 / p["n_ranhuras"]
    d["dist_sensores"] = 2 * d["r_feixe"] * math.sin(math.radians(ang / 2))
    d["sup_larg"] = d["dist_sensores"] + 2 * (p["sens_comp"] - p["sens_cabeca"] / 2) + 6
    d["sup_prof"] = d["y_aleta"] + p["sens_larg"] / 2 + 2
    d["y_mancal_frente"] = p["colar_esp"] + 1
    d["y_mancal_tras"] = -(p["tubo_comp"] + p["colar_esp"] + 1) - p["mancal_esp"]
    d["z_prat_base"] = d["h_prateleira"] - p["sup_esp"]
    d["aba_topo"] = p["sup_furos_h"] + p["sup_rasgo"] / 2 + 3.5
    d["z_base"] = -p["h_pivo"]
    d["y_bandeja"] = -p["base_y_tras"] + 4 + p["bandeja_y"] / 2
    d["barra_comp"] = (d["y_mancal_frente"] + p["mancal_esp"]) - d["y_mancal_tras"] + 6
    return d


def rot(pontos: np.ndarray, graus: float) -> np.ndarray:
    """Mesma rotação de rotate([0, graus, 0]) do OpenSCAD (em torno do pivô)."""
    a = math.radians(graus)
    x, y, z = pontos[:, 0], pontos[:, 1], pontos[:, 2]
    return np.column_stack([x * math.cos(a) + z * math.sin(a), y, -x * math.sin(a) + z * math.cos(a)])


def caixa(x0, x1, y0, y1, z0, z1, n=9) -> np.ndarray:
    g = np.meshgrid(np.linspace(x0, x1, n), np.linspace(y0, y1, n), np.linspace(z0, z1, n), indexing="ij")
    return np.column_stack([v.ravel() for v in g])


def dist_caixa(pts: np.ndarray, x0, x1, y0, y1, z0, z1) -> float:
    """Menor distância dos pontos até a caixa (negativa = dentro)."""
    lo, hi = np.array([x0, y0, z0]), np.array([x1, y1, z1])
    fora = np.maximum(np.maximum(lo - pts, pts - hi), 0.0)
    d = np.linalg.norm(fora, axis=1)
    dentro = np.all((pts >= lo) & (pts <= hi), axis=1)
    prof = np.min(np.minimum(pts - lo, hi - pts), axis=1)
    return float(np.min(np.where(dentro, -prof, d)))


def verificar(d: dict[str, float]) -> list[tuple[str, float, float]]:
    """Lista de (descrição, folga medida, mínimo exigido) em mm."""
    c: list[tuple[str, float, float]] = []
    a = d["angulo_batente"]
    sa, ca = math.sin(math.radians(a)), math.cos(math.radians(a))
    passo_m8 = d["m8_comp"] - d["m8_arruela_h"]
    ponta_m8 = d["y_roda"] - (passo_m8 - d["esp_roda"])           # Y da ponta dos M8 atrás da roda
    cabeca_m8 = d["y_roda_frente"] + d["m8_arruela_h"] + d["m8_cabeca_h"]
    r_cabeca_m8 = d["r_parafusos"] + d["m8_chave"] / math.cos(math.radians(30)) / 2

    # --- eixo, flange e roda ---
    c.append(("cubo do flange <-> ressalto do motor", d["y_cubo"] - d["ressalto_fim"], 0.8))
    c.append(("eixo dentro do flange (comprimento)", min(d["eixo_fora"], d["y_alma"]) - max(d["y_cubo"], d["ressalto_fim"]), 8.0))
    c.append(("ponta do eixo <-> face da frente da roda", d["y_roda_frente"] - d["eixo_fora"], 0.5))
    c.append(("cabeças M4 do motor <-> disco do flange", d["y_flange"] - d["m4_cabeca_h"], 2.0))
    c.append(("parafuso M8 atravessa a porca inteira", passo_m8 - d["esp_roda"], 0.0))
    c.append(("ponta dos M8 <-> face da frente do braço", ponta_m8, 3.0))
    c.append(("porca M8 dentro do aro (radial, lado de dentro)",
              d["r_parafusos"] - (d["m8_chave"] + 0.4) / math.cos(math.radians(30)) / 2 - d["r_aro_int"], 0.8))
    c.append(("porca M8 dentro do aro (radial, lado de fora)",
              d["r_ext"] - d["r_parafusos"] - (d["m8_chave"] + 0.4) / math.cos(math.radians(30)) / 2, 0.8))
    c.append(("porcas M8 vizinhas",
              2 * math.pi * d["r_parafusos"] / d["n_parafusos"] - (d["m8_chave"] + 0.4) / math.cos(math.radians(30)), 2.0))

    # --- sensores e suporte ---
    c.append(("topo das torres <-> aro da roda", d["r_aleta"] - d["sens_penetra"] - d["r_ext"], 1.0))
    c.append(("anel dentado <-> paredes da fenda", (d["sens_fenda"] - d["esp_aleta"]) / 2, 1.0))
    c.append(("feixe acima da raiz dos dentes", d["r_feixe"] - (d["r_ext"] + 1.5), 0.7))
    c.append(("feixe abaixo da ponta dos dentes", d["r_aleta"] - d["r_feixe"], 0.7))
    c.append(("cabeças M8 da frente <-> topo das torres (radial)", d["r_aleta"] - d["sens_penetra"] - r_cabeca_m8, 2.0))
    c.append(("blocos dos 2 sensores lado a lado", d["dist_sensores"] - d["sens_cabeca"], 1.0))
    c.append(("placa do sensor cabe na prateleira", d["sup_prof"] - (d["y_aleta"] + d["sens_larg"] / 2), 1.0))
    c.append(("cabeças M3 do suporte <-> face de trás da roda", d["y_roda"] - (d["sup_aba_esp"] + 3.0), 1.5))
    c.append(("aba do suporte <-> ponta dos M8 (em Y)", ponta_m8 - d["sup_aba_esp"], 1.0))
    c.append(("cabeças M3 do suporte <-> ponta dos M8 (altura, rasgo no topo)",
              (d["l_w"] - d["r_parafusos"] - 4) - (d["sup_furos_h"] + d["sup_rasgo"] / 2 + 3), 2.0))

    # --- braço ---
    c.append(("MPU6050 acima do tubo dos rolamentos", (d["mpu_h"] - 3) - d["tubo_d"] / 2, 2.0))
    c.append(("MPU6050 abaixo da carcaça do motor", (d["l_w"] - d["motor_d"] / 2) - (d["mpu_h"] + 13), 2.0))
    c.append(("parede do braço em volta do motor", 6.0 - d["folga"], 4.0))

    # --- base, pivô e curso até o batente ---
    c.append(("colar da frente <-> suporte da barra", d["y_mancal_frente"] - d["colar_esp"], 0.5))
    c.append(("colar de trás <-> suporte da barra",
              -(d["tubo_comp"] + d["colar_esp"]) - (d["y_mancal_tras"] + d["mancal_esp"]), 0.5))
    c.append(("pé alargado do suporte <-> colares", (d["z_base"] + d["h_pivo"] - 25) * -1 - d["colar_d"] / 2, 3.0))

    # batente: pontos da região ocupada, distância ao eixo do pivô (tubo dos rolamentos)
    pts = caixa(-d["base_x"] / 2 + 5, 0, -14, 6, d["z_base"], d["batente_topo"], n=40)
    x_braco = pts[:, 0] * ca - pts[:, 2] * sa   # coordenada x no referencial do braço encostado
    dentro = pts[x_braco <= -(d["larg_cauda"] / 2 + d["tpu_esp"])]
    raio = np.hypot(dentro[:, 0], dentro[:, 2])
    c.append(("batente <-> tubo dos rolamentos", float(raio.min()) - d["tubo_d"] / 2, 2.0))
    # almofada de TPU (montagem.scad): começa 2 mm acima do tampo e tem tpu_comp de comprimento
    x_tpu = d["larg_cauda"] / 2 + d["tpu_esp"] / 2
    tpu_comp = (d["batente_topo"] - d["z_base"]) / ca - 3
    z_tpu_topo = (d["z_base"] + 2 - x_tpu * sa) / ca + tpu_comp     # no referencial do braço
    c.append(("almofada de TPU <-> tubo dos rolamentos",
              math.hypot(d["larg_cauda"] / 2, z_tpu_topo) - d["tubo_d"] / 2, 2.0))
    c.append(("comprimento de contato cauda/almofada", d["cauda"] + z_tpu_topo, 12.0))

    cauda = np.array([[s * d["larg_cauda"] / 2, 0.0, -d["cauda"]] for s in (-1, 1)])
    roda = np.array([[d["r_aleta"] * math.cos(t), y, d["l_w"] + d["r_aleta"] * math.sin(t)]
                     for t in np.linspace(0, 2 * math.pi, 180) for y in (d["y_roda"], d["y_roda_frente"])])
    prat = caixa(-d["sup_larg"] / 2, d["sup_larg"] / 2, 0, d["sup_prof"], d["z_prat_base"], d["h_prateleira"])
    mf = (-d["mancal_larg"] / 2, d["mancal_larg"] / 2, d["y_mancal_frente"], d["y_mancal_frente"] + d["mancal_esp"],
          d["z_base"], d["mancal_topo"])
    piores = {"cauda": 1e9, "roda": 1e9, "prat": 1e9, "prot": 1e9}
    for ang in np.linspace(-a, a, 21):
        piores["cauda"] = min(piores["cauda"], float(rot(cauda, ang)[:, 2].min()) - d["z_base"])
        piores["roda"] = min(piores["roda"], dist_caixa(rot(roda, ang), *mf))
        piores["prat"] = min(piores["prat"], dist_caixa(rot(prat, ang), *mf))
        r_ext = rot(roda, ang)
        piores["prot"] = min(piores["prot"], d["prot_larg"] / 2 - float(np.abs(r_ext[:, 0]).max()))
    c.append(("cauda <-> tampo da base (curso todo)", piores["cauda"], 3.0))
    c.append(("roda <-> suporte da frente da barra (curso todo)", piores["roda"], 5.0))
    c.append(("prateleira dos sensores <-> suporte da barra (curso todo)", piores["prat"], 3.0))

    # --- proteção ---
    c.append(("cabeças M8 <-> placa de policarbonato", d["prot_y"] - d["prot_rasgo"] / 2 - cabeca_m8, 5.0))
    c.append(("placa cobre a roda na largura (curso todo)", piores["prot"], 5.0))
    c.append(("placa cobre a roda na altura", d["z_base"] + d["prot_alt"] - (d["l_w"] + d["r_aleta"]), 5.0))

    # --- base: eletrônica e fixação ---
    col = [(sx * (d["bandeja_x"] / 2 - 6), d["y_bandeja"] + sy * (d["bandeja_y"] / 2 - 6)) for sx in (-1, 1) for sy in (-1, 1)]
    furos = [(sx * (d["base_x"] / 2 - 7), y) for sx in (-1, 1) for y in (-d["base_y_tras"] + 7, d["base_y_frente"] - 7)]
    c.append(("colunas da bandeja <-> furos de fixação",
              min(math.dist(p, q) for p in col for q in furos) - 4.5 - d["furo_fixacao"] / 2, 1.0))
    c.append(("bandeja <-> pé do suporte de trás", (d["y_mancal_tras"] - 8) - (d["y_bandeja"] + d["bandeja_y"] / 2), 1.0))
    c.append(("bandeja dentro da base (atrás)", d["y_bandeja"] - d["bandeja_y"] / 2 + d["base_y_tras"], 2.0))

    # --- impressão (mesa de 220 mm) ---
    c.append(("roda cabe na mesa", 210 - 2 * d["r_aleta"], 0.0))
    c.append(("base cabe na mesa", 210 - max(d["base_x"], d["base_y_frente"] + d["base_y_tras"]), 0.0))
    c.append(("braço cabe na mesa", 210 - (d["l_w"] + d["motor_d"] / 2 + 6 + d["cauda"]), 0.0))
    return c


def main() -> int:
    d = derivar(ler_parametros())
    falhas = 0
    print(f"{'verificação':<60} {'folga':>8} {'mínimo':>8}")
    for nome, folga, minimo in verificar(d):
        ok = folga >= minimo - 1e-9
        falhas += not ok
        print(f"{nome:<60} {folga:7.2f}  {minimo:7.2f}  {'ok' if ok else 'FALHOU'}")
    print(f"\nBarra de 8 mm: cortar com {d['barra_comp']:.0f} mm (a comprada tem 250 mm).")
    print(f"Sensores: centros ópticos a {d['dist_sensores']:.1f} mm um do outro (1 1/4 dente = quadratura).")
    print("\nTODAS AS FOLGAS OK" if falhas == 0 else f"\n{falhas} FOLGA(S) FALHARAM")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
