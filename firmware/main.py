# main.py — Punto de entrada del Pino de Navidad.
#
# Modo seguro: presiona y suelta EN (reset) y, en el primer segundo,
# mantén presionado BOOT. La app no arranca y queda libre el REPL para
# cargar archivos. (Si BOOT ya está presionado al soltar EN, el ESP32 entra
# en modo de descarga del bootloader; eso es otra cosa.)

import time

import machine

import config
from errlog import log_exception


def _safe_mode_requested():
    boot_btn = machine.Pin(config.PIN_BOOT, machine.Pin.IN, machine.Pin.PULL_UP)
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < config.SAFE_MODE_WINDOW_MS:
        if boot_btn.value() == 0:
            return True
        time.sleep_ms(20)
    return False


def _start():
    if _safe_mode_requested():
        print("== MODO SEGURO: la aplicacion no se inicio. REPL disponible. ==")
        return
    try:
        import app
        app.run()
    except KeyboardInterrupt:
        print("Detenido por el usuario (Ctrl-C).")
    except Exception as exc:  # cualquier fallo inesperado
        log_exception("main", exc, config.ERROR_LOG, config.ERROR_LOG_MAX_BYTES)
        if config.AUTO_RESET_ON_ERROR:
            print("Reiniciando en 10 s (Ctrl-C para cancelar)...")
            time.sleep(10)
            machine.reset()


_start()
