#!/usr/bin/env python3
"""Massa e inércia das peças impressas, calculadas dos STLs (rodar depois de build.sh).

Compara com as estimativas de sim/params.py e diz o que atualizar lá. A conta
usa a fração de material de cada peça (perímetros + preenchimento); depois de
imprimir, PESE as peças e use o valor da balança, que é o que vale.

Uso:  python cad/massas.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import trimesh

PASTA = Path(__file__).resolve().parent
sys.path.insert(0, str(PASTA.parent))
from sim.params import NOMINAL, RHO_PETG  # noqa: E402

RHO_TPU = 1210.0
# fração de material estimada para cada peça (perímetros grossos + preenchimento)
PECAS = {
    "roda": (RHO_PETG, NOMINAL.roda.preenchimento),
    "braco": (RHO_PETG, 0.75),
    "suporte_sensores": (RHO_PETG, 0.9),
    "base": (RHO_PETG, 0.45),
    "bandeja": (RHO_PETG, 0.6),
    "batente_tpu": (RHO_TPU, 1.0),
}
M_ROLAMENTO = 0.012      # 608-ZZ
M_FIXADORES_BRACO = 0.012  # 2 M4 do motor + insertos + parafusos do suporte e do MPU


def main() -> int:
    res, faltando = {}, []
    print(f"{'peça':<18} {'fechada':>8} {'volume':>10} {'massa':>8}  dimensões (mm)")
    for nome, (rho, frac) in PECAS.items():
        arq = PASTA / "stl" / f"{nome}.stl"
        if not arq.exists():
            faltando.append(nome)
            continue
        m = trimesh.load_mesh(arq)
        vol = abs(m.volume) * 1e-9          # mm³ -> m³
        massa = vol * rho * frac
        ext = m.bounding_box.extents
        res[nome] = {"estanque": bool(m.is_watertight), "volume_cm3": vol * 1e6, "massa_g": massa * 1e3,
                     "dimensoes_mm": [round(float(v), 1) for v in ext]}
        if nome == "roda":
            m.density = rho * frac * 1e-9     # kg/mm³
            res[nome]["I_eixo_gm2"] = float(m.moment_inertia[2, 2]) * 1e-6 * 1e3   # kg·mm² -> g·m²
        if nome == "braco":
            res[nome]["cm_ao_longo_mm"] = float(m.center_mass[1])
        print(f"{nome:<18} {'sim' if m.is_watertight else 'NÃO':>8} {vol * 1e6:8.1f} cm³ {massa * 1e3:6.0f} g  "
              f"{ext[0]:.0f} x {ext[1]:.0f} x {ext[2]:.0f}")
    if faltando:
        print(f"\nSTLs que faltam: {', '.join(faltando)}. Rode cad/build.sh antes.")
        return 1

    r = NOMINAL.roda
    i_impressa_modelo = sum(i for _, i in r._pecas()[:4]) * 1e3
    braco_total = res["braco"]["massa_g"] / 1e3 + 2 * M_ROLAMENTO + M_FIXADORES_BRACO
    print("\nComparação com sim/params.py:")
    print(f"  roda impressa: {res['roda']['massa_g']:.0f} g (modelo {r.massa_impressa * 1e3:.0f} g), "
          f"inércia {res['roda']['I_eixo_gm2']:.3f} g·m² (modelo {i_impressa_modelo:.3f})")
    print(f"  braço com rolamentos e parafusos: {braco_total * 1e3:.0f} g (modelo m_braco = {NOMINAL.m_braco * 1e3:.0f} g)")
    cm = (res["braco"]["massa_g"] / 1e3 * res["braco"]["cm_ao_longo_mm"]) / braco_total / (NOMINAL.l_w * 1e3)
    print(f"  centro de massa do braço: {cm:.2f} de l_w (modelo frac_cm_braco = {NOMINAL.frac_cm_braco:.2f})")
    print("\nSe a diferença passar de ~15 %, atualize m_braco / frac_cm_braco em sim/params.py,")
    print("rode `python -m sim.export_gains` e os testes. Depois de imprimir, use o peso da balança.")
    for nome, v in res.items():
        if not v["estanque"]:
            print(f"ATENÇÃO: {nome}.stl não é uma malha fechada; o fatiador pode reclamar.")

    (PASTA / "stl" / "massas.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
