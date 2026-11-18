#!/usr/bin/env python3
"""Copia el firmware al ESP32 con mpremote y lo reinicia.

Uso (desde la raíz del repositorio):
    python tools/deploy.py                  # autodetecta el puerto
    python tools/deploy.py --port COM5      # Windows
    python tools/deploy.py --port /dev/ttyUSB0
    python tools/deploy.py --no-reset       # copia sin reiniciar

Requisito: pip install mpremote
Cierra Thonny (u otro programa que use el puerto serie) antes de ejecutarlo.
"""
import argparse
import importlib.util
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIRMWARE = ROOT / "firmware"


def mpremote_cmd():
    local_mpremote = pathlib.Path(sys.executable).with_name("mpremote")
    if local_mpremote.exists():
        return [str(local_mpremote)]
    if importlib.util.find_spec("mpremote") is not None:
        return [sys.executable, "-m", "mpremote"]
    if shutil.which("mpremote"):
        return ["mpremote"]
    return None


def run(args):
    print("$", " ".join(args))
    return subprocess.run(args).returncode


def main():
    ap = argparse.ArgumentParser(description="Carga el firmware del Pino al ESP32")
    ap.add_argument("--port", default="auto", help="COMx, /dev/ttyUSBx o 'auto'")
    ap.add_argument("--no-reset", action="store_true", help="no reiniciar al terminar")
    args = ap.parse_args()

    base = mpremote_cmd()
    if base is None:
        print("No se encontró mpremote. Instálalo con:  pip install mpremote")
        return 1
    base += ["connect", args.port]

    files = [(f, ":" + f.name) for f in sorted(FIRMWARE.glob("*.py"))]
    files += [(f, ":lib/" + f.name) for f in sorted((FIRMWARE / "lib").glob("*.py"))]

    run(base + ["mkdir", ":lib"])  # si ya existe da error; no importa

    cmd = list(base)
    for local, remote in files:
        cmd += ["cp", str(local), remote, "+"]
    if args.no_reset:
        cmd.pop()                  # quita el último "+"
    else:
        cmd += ["reset"]
    code = run(cmd)
    print("Listo." if code == 0 else "Hubo un error al copiar (código {}).".format(code))
    return code


if __name__ == "__main__":
    sys.exit(main())
