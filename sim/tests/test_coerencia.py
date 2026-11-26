"""Coerência entre as partes do projeto: arquivos gerados em dia, folgas do CAD
e pinagem igual na documentação e no firmware."""
import re
from pathlib import Path

from cad.folgas import derivar, ler_parametros, verificar
from sim.controlador import projetar
from sim.export_gains import gerar_ganhos, gerar_scad
from sim.params import NOMINAL

RAIZ = Path(__file__).resolve().parents[2]


def test_arquivos_gerados_estao_em_dia():
    """Se falhar: mudaram sim/params.py sem rodar `python -m sim.export_gains`."""
    g = projetar(NOMINAL)
    assert (RAIZ / "firmware/lib/control/lqr_gains.h").read_text(encoding="utf-8") == gerar_ganhos(NOMINAL, g)
    assert (RAIZ / "cad/dimensoes_geradas.scad").read_text(encoding="utf-8") == gerar_scad(NOMINAL)


def test_numeros_do_relatorio_em_dia():
    """Se falhar: mudaram sim/params.py sem rodar `python -m sim.export_relatorio`."""
    from sim.export_relatorio import SAIDA, gerar

    assert SAIDA.read_text(encoding="utf-8") == gerar()


def test_folgas_do_cad():
    falhas = [(n, f, m) for n, f, m in verificar(derivar(ler_parametros())) if f < m - 1e-9]
    assert not falhas, falhas


def _pinos_do_firmware() -> dict[str, str]:
    """Tabela do comentário de firmware/include/board.h: função -> pino."""
    texto = (RAIZ / "firmware/include/board.h").read_text(encoding="utf-8")
    pinos = {}
    for linha in texto.splitlines():
        m = re.match(r"\s*\*\s+(.+?)\s{2,}(P[ABC]\d+)\b", linha)
        if m:
            pinos[m.group(2)] = m.group(1).strip()
    return pinos


def test_pinagem_da_documentacao_igual_ao_firmware():
    pinos_fw = _pinos_do_firmware()
    assert len(pinos_fw) >= 14
    doc = (RAIZ / "docs/ligacoes.md").read_text(encoding="utf-8")
    tabela = dict(re.findall(r"^\|\s*\*\*(P[ABC]\d+)\*\*\s*\|\s*([^|]+?)\s*\|", doc, flags=re.M))
    assert set(tabela) == set(pinos_fw), (set(tabela) ^ set(pinos_fw))


def test_matlab_em_dia():
    """Se falhar: mudaram sim/params.py sem atualizar matlab/rwp_params.m ou sem
    rodar `python -m sim.export_matlab` (a referência do matlab/verificar_python.m)."""
    import json

    texto = (RAIZ / "matlab/rwp_params.m").read_text(encoding="utf-8")
    texto = texto.split("substituições")[0]
    lidos = dict(re.findall(r"^p\.(\w+)\s*=\s*([-+0-9.eE]+);", texto, flags=re.M))
    assert len(lidos) == 36  # 9 do motor, 16 da roda, 11 do pêndulo
    for campo, valor in lidos.items():
        obj, nome = ((NOMINAL.motor, campo[6:]) if campo.startswith("motor_")
                     else (NOMINAL.roda, campo[5:]) if campo.startswith("roda_") else (NOMINAL, campo))
        assert float(valor) == getattr(obj, nome), f"matlab/rwp_params.m: {campo} = {valor}"

    ref = json.loads((RAIZ / "matlab/referencia_python.json").read_text(encoding="utf-8"))
    g = projetar(NOMINAL)
    assert ref["ganhos"]["K"] == [g.k1, g.k2, g.k3]
    assert ref["ganhos"]["KI"] == [g.q1, g.q2, g.q3, g.q4]
    assert ref["derivados"]["J"] == NOMINAL.J and ref["derivados"]["Mgl"] == NOMINAL.Mgl
