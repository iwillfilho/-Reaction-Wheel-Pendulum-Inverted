#!/usr/bin/env python3
"""Grava a telemetria do firmware em CSV e permite mandar comandos.

Uso (com a .venv ativa):
    python tools/telemetry_log.py                      # /dev/ttyUSB0, grava em logs/
    python tools/telemetry_log.py --porta /dev/ttyACM0 --saida ensaio_motor.csv

Digite os comandos do firmware (a, s, m 20, k1 -250, cfg, diag, ?) e Enter.
Ctrl+C encerra. As linhas que começam com '#' são mensagens do firmware.
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path

import serial

CABECALHO = "t_s,estado,falha,theta_graus,vel_graus_s,roda_rpm,u_V,vbus_V,trim_graus,encoder"


def converter(campos: list[str]) -> str:
    """Linha 'D,...' do firmware (inteiros escalados) -> unidades do cabeçalho."""
    t, est, falha, th, thd, w, u, vb, trim, enc = (int(c) for c in campos)
    return (f"{t / 1000:.3f},{est},{falha},{th / 1000:.3f},{thd / 1000:.2f},{w / 10:.1f},"
            f"{u / 1000:.3f},{vb / 1000:.2f},{trim / 1000:.3f},{enc}")


def leitor(porta: serial.Serial, arquivo, parar: threading.Event) -> None:
    n = 0
    while not parar.is_set():
        bruto = porta.readline()
        if not bruto:
            continue
        linha = bruto.decode("ascii", errors="replace").strip()
        if linha.startswith("D,"):
            try:
                arquivo.write(converter(linha.split(",")[1:]) + "\n")
            except ValueError:
                continue  # linha cortada por ruído na serial
            n += 1
            if n % 200 == 0:
                arquivo.flush()
        elif linha:
            print(linha, flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--porta", default="/dev/ttyUSB0")
    ap.add_argument("--baud", type=int, default=460800)
    ap.add_argument("--saida", default=None, help="arquivo CSV (padrão: logs/AAAAMMDD_HHMMSS.csv)")
    a = ap.parse_args()

    saida = Path(a.saida) if a.saida else Path("logs") / time.strftime("%Y%m%d_%H%M%S.csv")
    saida.parent.mkdir(parents=True, exist_ok=True)
    try:
        porta = serial.Serial(a.porta, a.baud, timeout=0.2)
    except serial.SerialException as e:
        sys.exit(f"Não abriu {a.porta}: {e}\nConfira o adaptador USB-serial (ls /dev/ttyUSB* /dev/ttyACM*).")

    parar = threading.Event()
    with porta, open(saida, "w", encoding="ascii") as arq:
        arq.write(CABECALHO + "\n")
        t = threading.Thread(target=leitor, args=(porta, arq, parar), daemon=True)
        t.start()
        print(f"Gravando em {saida}. Comandos: a, s, m <pct>, cfg, diag, ?  (Ctrl+C sai)")
        try:
            for linha in sys.stdin:
                porta.write((linha.strip() + "\n").encode("ascii", errors="ignore"))
        except KeyboardInterrupt:
            pass
        finally:
            porta.write(b"s\n")   # ao sair, manda parar
            parar.set()
            t.join(timeout=1.0)
    print(f"\nLog salvo em {saida}")


if __name__ == "__main__":
    main()
