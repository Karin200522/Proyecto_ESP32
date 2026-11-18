# errlog.py — Registro de errores en consola y en un archivo de la flash.
#
# Sirve para saber qué falló aunque el ESP32 se haya reiniciado:
# abre error.log desde Thonny o con `mpremote cat error.log`.

import os
import sys
import time


def log_exception(where, exc, path="error.log", max_bytes=4096):
    print("[ERROR] en", where)
    try:
        sys.print_exception(exc)
    except AttributeError:  # CPython (pruebas en la PC)
        print(repr(exc))
    try:
        try:
            size = os.stat(path)[6]
        except OSError:
            size = 0
        # Si el archivo creció demasiado, empezar de nuevo (protege la flash).
        with open(path, "w" if size > max_bytes else "a") as f:
            f.write("--- {} t={}ms\n".format(where, time.ticks_ms()))
            sys.print_exception(exc, f)
    except Exception:
        pass  # registrar nunca debe tumbar el programa
