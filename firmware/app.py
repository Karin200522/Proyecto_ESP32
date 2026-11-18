# app.py — Orquestador del Pino de Navidad (asyncio).
#
# Tareas concurrentes:
#   animacion → calcula y escribe el brillo de los LEDs a 50 FPS (con fundidos)
#   sensor    → lee la LDR y decide encendido/reposo (modo AUTO)
#   ble       → atiende los comandos que llegan desde nRF Connect
#   serial    → atiende los mismos comandos por la consola USB (Thonny)
#   pantalla  → actualiza la LCD; la apaga en reposo; la reconecta si falla
#   servicio  → watchdog, guardado de ajustes, recolección de basura, reinicio
#
# Cada tarea está "supervisada": si lanza una excepción, se registra en
# error.log y se reinicia sola, sin tumbar el resto del árbol.

import gc
import sys
import time

from machine import I2C, Pin, reset

try:
    import asyncio
except ImportError:
    import uasyncio as asyncio

import commands
import config
from animations import WRAP_MS, build_modes, find_mode
from ble_uart import BLEUart
from buzzer import Buzzer
from display import BT, NOTE, TREE, Display
from errlog import log_exception
from leds import LedChannels
from light_sensor import DarkDetector, LightSensor
from melodies import MELODIES
from settings import Settings

_RANGES = {
    "brillo": (10, 100),
    "velocidad": (1, 5),
    "volumen": (0, 100),
    "melodia": (1, len(MELODIES)),
    "umbral_oscuro": (0, 99),
    "umbral_claro": (1, 100),
}

LINE_ACTIVE = TREE + "Feliz Navidad " + TREE      # 16 caracteres exactos


class ChristmasTree:
    def __init__(self):
        print("\n=== Pino de Navidad ESP32 ===")
        self.modes = build_modes()
        self.settings = Settings(config.SETTINGS_FILE, config.DEFAULTS, self._validate)
        s = self.settings
        if s.get("umbral_oscuro") >= s.get("umbral_claro"):
            s.reset_key("umbral_oscuro")
            s.reset_key("umbral_claro")

        # Salidas de potencia primero: así quedan en 0 cuanto antes
        self.leds = LedChannels(
            (config.PIN_LED_AMARILLO, config.PIN_LED_ROJO, config.PIN_LED_VERDE),
            config.LED_PWM_FREQ)
        self.buzzer = Buzzer(config.PIN_BUZZER, s.get("volumen"))

        self.sensor = LightSensor(config.PIN_LDR, config.LDR_SAMPLES, config.LDR_INVERT)
        self.detector = DarkDetector(s.get("umbral_oscuro"), s.get("umbral_claro"),
                                     config.LDR_CONFIRM_MS)

        i2c = I2C(0, scl=Pin(config.PIN_I2C_SCL), sda=Pin(config.PIN_I2C_SDA),
                  freq=config.I2C_FREQ)
        self.display = Display(i2c, config.LCD_ADDR, config.LCD_COLS, config.LCD_ROWS)
        self.display.show(TREE + " Pino Navidad " + TREE, "Iniciando...")

        # Sin BLE el árbol sigue funcionando con el sensor de luz
        self.ble = None
        try:
            self.ble = BLEUart(config.BLE_NAME, config.BLE_ADV_STANDBY_MS)
        except Exception as e:
            log_exception("BLE init", e, config.ERROR_LOG, config.ERROR_LOG_MAX_BYTES)

        self.mode = find_mode(self.modes, s.get("modo")) or self.modes[0]
        self.override = "auto"      # "auto" (LDR) | "on" | "off"
        self.active = False         # árbol encendido (no en reposo)
        self.light_pct = 0.0
        self._fade = 0.0            # 0.0-1.0, fundido de encendido/apagado
        self._t_anim = 0            # reloj de animación (ms, entero)
        self._t_frac = 0.0
        self._reboot_at = None
        self._wdt = None
        if config.USE_WDT:
            from machine import WDT
            self._wdt = WDT(timeout=config.WDT_TIMEOUT_MS)

    # ================================================================ estado
    def _validate(self, key, value):
        rng = _RANGES.get(key)
        if rng is not None:
            return rng[0] <= value <= rng[1]
        if key == "modo":
            return find_mode(self.modes, value) is not None
        return True

    def _target_active(self):
        if self.override == "on":
            return True
        if self.override == "off":
            return False
        return bool(self.detector.is_dark)

    def _apply_state(self):
        """Enciende o manda a reposo el árbol si cambió la condición."""
        want = self._target_active()
        if want == self.active:
            return
        self.active = want
        if want:
            print("[PINO] ENCENDIDO ({})".format(self.override))
            self.mode.reset()
            if self.ble:
                self.ble.advertise(config.BLE_ADV_ACTIVE_MS)
            if self.settings.get("auto_musica"):
                self._play(self.settings.get("melodia"))
        else:
            print("[PINO] REPOSO ({})".format(self.override))
            self.buzzer.stop()
            if self.ble:
                self.ble.advertise(config.BLE_ADV_STANDBY_MS)
        # Los LEDs hacen el fundido en la tarea de animación; la LCD se
        # enciende o apaga en la tarea de pantalla.

    def _set_mode(self, mode):
        self.mode = mode
        mode.reset()
        self.settings.set("modo", mode.name)

    def _play(self, number):
        melody = MELODIES[number - 1]
        self.buzzer.start(melody)
        return melody["nombre"]

    # ================================================================ tareas
    async def _task_animation(self):
        last = time.ticks_ms()
        while True:
            now = time.ticks_ms()
            dt = time.ticks_diff(now, last)
            last = now
            if dt < 0 or dt > 1000:     # protección ante saltos raros del reloj
                dt = config.ANIM_FRAME_MS

            step = dt / config.FADE_MS
            if self.active:
                self._fade = min(1.0, self._fade + step)
            else:
                self._fade = max(0.0, self._fade - step)

            if self._fade > 0:
                factor = config.SPEED_FACTORS[self.settings.get("velocidad") - 1]
                acc = self._t_frac + dt * factor
                inc = int(acc)
                self._t_frac = acc - inc
                self._t_anim = (self._t_anim + inc) % WRAP_MS
                levels = self.mode.frame(self._t_anim)
                scale = self._fade * self.settings.get("brillo") / 100
                self.leds.write(levels, scale)
                await asyncio.sleep_ms(config.ANIM_FRAME_MS)
            else:
                self.leds.off()
                await asyncio.sleep_ms(100)     # en reposo basta con 10 Hz

    async def _task_sensor(self):
        while True:
            self.light_pct = self.sensor.read_pct()
            if self.detector.update(self.light_pct, time.ticks_ms()):
                print("[LDR] {} (luz {:.0f}%)".format(
                    "OSCURO" if self.detector.is_dark else "CLARO", self.light_pct))
            self._apply_state()
            await asyncio.sleep_ms(config.LDR_PERIOD_MS)

    async def _task_ble(self):
        if self.ble is None:
            return
        while True:
            cmd = self.ble.get_command()
            while cmd is not None:
                print("[BLE] <", cmd)
                reply = self.execute(cmd)
                if reply:
                    await self.ble.send(reply + "\n")
                cmd = self.ble.get_command()
            await asyncio.sleep_ms(50)

    async def _task_serial(self):
        import select
        poller = select.poll()
        poller.register(sys.stdin, select.POLLIN)
        buf = ""
        while True:
            while poller.poll(0):
                ch = sys.stdin.read(1)
                if ch in ("\n", "\r"):
                    if buf.strip():
                        reply = self.execute(buf)
                        if reply:
                            print(reply)
                    buf = ""
                elif len(buf) < 64:
                    buf += ch
            await asyncio.sleep_ms(50)

    async def _task_display(self):
        retry_at = time.ticks_ms()
        while True:
            if not self.display.ok:
                if time.ticks_diff(time.ticks_ms(), retry_at) >= 0:
                    self.display.connect()
                    retry_at = time.ticks_add(time.ticks_ms(), 5000)
            elif self.active:
                self.display.power(True)
                status = ((NOTE if self.buzzer.playing else " ") + " "
                          + (BT if self.ble and self.ble.connected else " "))
                self.display.show(LINE_ACTIVE, (self.mode.label + " " * 13)[:13] + status)
            else:
                self.display.power(False)
            await asyncio.sleep_ms(250)

    async def _task_service(self):
        ticks = 0
        while True:
            if self._wdt is not None:
                self._wdt.feed()
            self.settings.save_if_due(config.SETTINGS_SAVE_DELAY_MS)
            if self._reboot_at is not None and \
                    time.ticks_diff(time.ticks_ms(), self._reboot_at) >= 0:
                self.shutdown()
                reset()
            ticks += 1
            if ticks % 30 == 0:
                gc.collect()
            await asyncio.sleep_ms(1000)

    async def _supervise(self, name, task_fn):
        while True:
            try:
                await task_fn()
                return                  # la tarea terminó normalmente
            except Exception as e:
                log_exception("tarea " + name, e, config.ERROR_LOG,
                              config.ERROR_LOG_MAX_BYTES)
                await asyncio.sleep_ms(1000)

    async def main(self):
        tasks = [
            self._supervise("animacion", self._task_animation),
            self._supervise("sensor", self._task_sensor),
            self._supervise("ble", self._task_ble),
            self._supervise("pantalla", self._task_display),
            self._supervise("servicio", self._task_service),
        ]
        if config.SERIAL_COMMANDS:
            tasks.append(self._supervise("serial", self._task_serial))
        print("[PINO] listo. Escribe AYUDA (por BLE o aqui en la consola).")
        await asyncio.gather(*tasks)

    def shutdown(self):
        """Deja todo apagado y seguro (Ctrl-C, reinicio o error)."""
        for action in (self.buzzer.deinit, self.leds.deinit,
                       lambda: self.display.power(False)):
            try:
                action()
            except Exception:
                pass
        if self.settings.dirty:
            self.settings.save()

    # ================================================================ comandos
    # Las respuestas van sin acentos: BLE las parte en trozos del tamaño del
    # MTU y un carácter UTF-8 de 2 bytes podría quedar cortado a la mitad.
    def execute(self, text):
        action, args = commands.parse(text)
        if action is None:
            return None
        handler = getattr(self, "_cmd_" + action, None)
        if handler is None:
            return "ERR comando desconocido. Escribe AYUDA"
        try:
            return handler(args)
        except (ValueError, IndexError, KeyError):
            return "ERR valor invalido. Escribe AYUDA"

    def _modes_list(self):
        return " ".join("{}={}".format(i + 1, m.name) for i, m in enumerate(self.modes))

    def _cmd_help(self, args):
        return commands.HELP

    def _cmd_mode(self, args):
        if not args:
            return "Modo actual: {}. Opciones: {}".format(self.mode.label, self._modes_list())
        mode = find_mode(self.modes, " ".join(args).lower())
        if mode is None:
            return "ERR modo desconocido. " + self._modes_list()
        self._set_mode(mode)
        return "OK modo {}".format(mode.label)

    def _cmd_mode_direct(self, args):
        mode = find_mode(self.modes, " ".join(args).lower())
        if mode is None:
            return "ERR comando desconocido. Escribe AYUDA"
        self._set_mode(mode)
        return "OK modo {}".format(mode.label)

    def _cmd_next(self, args):
        idx = (self.modes.index(self.mode) + 1) % len(self.modes)
        self._set_mode(self.modes[idx])
        return "OK modo {}".format(self.mode.label)

    def _cmd_on(self, args):
        self.override = "on"
        self._apply_state()
        return "OK encendido manual. AUTO para volver al sensor de luz"

    def _cmd_off(self, args):
        self.override = "off"
        self._apply_state()
        return "OK apagado manual. AUTO para volver al sensor de luz"

    def _cmd_auto(self, args):
        self.override = "auto"
        self._apply_state()
        return "OK control automatico por luz ({})".format(
            "oscuro: encendido" if self.detector.is_dark else "claro: reposo")

    def _cmd_play(self, args):
        number = int(args[0]) if args else self.settings.get("melodia")
        self.settings.set("melodia", number)        # valida 1..3
        name = self._play(number)
        warn = " (volumen en 0)" if self.buzzer.volume == 0 else ""
        return "OK tocando {}: {}{}".format(number, name, warn)

    def _cmd_stop(self, args):
        self.buzzer.stop()
        return "OK silencio"

    def _cmd_volume(self, args):
        value = int(args[0])
        self.settings.set("volumen", value)
        self.buzzer.volume = value
        return "OK volumen {}%".format(value)

    def _cmd_bright(self, args):
        value = int(args[0])
        self.settings.set("brillo", value)
        return "OK brillo {}%".format(value)

    def _cmd_speed(self, args):
        value = int(args[0])
        self.settings.set("velocidad", value)
        return "OK velocidad {}".format(value)

    def _cmd_automusic(self, args):
        value = commands.parse_bool(args[0])
        self.settings.set("auto_musica", value)
        return "OK musica al encender: {}".format("SI" if value else "NO")

    def _cmd_light(self, args):
        return "Luz {:.0f}% ({}). Umbrales: oscuro<{}% claro>{}%. Control {}".format(
            self.light_pct, "oscuro" if self.detector.is_dark else "claro",
            self.detector.dark_pct, self.detector.light_pct, self.override.upper())

    def _cmd_threshold(self, args):
        dark, light = int(args[0]), int(args[1])
        self.detector.set_thresholds(dark, light)   # valida oscuro < claro
        self.settings.set("umbral_oscuro", dark)
        self.settings.set("umbral_claro", light)
        return "OK umbrales: oscuro<{}% claro>{}%".format(dark, light)

    def _cmd_status(self, args):
        s = self.settings
        return ("Estado: {} | control {}\n"
                "Modo {} | brillo {}% | vel {}\n"
                "Musica al encender: {} | vol {}% | melodia {}\n"
                "Luz {:.0f}% | LCD {} | RAM libre {} B").format(
            "ENCENDIDO" if self.active else "REPOSO", self.override.upper(),
            self.mode.label, s.get("brillo"), s.get("velocidad"),
            "SI" if s.get("auto_musica") else "NO", s.get("volumen"), s.get("melodia"),
            self.light_pct, "OK" if self.display.ok else "sin conexion", gc.mem_free())

    def _cmd_reboot(self, args):
        self._reboot_at = time.ticks_add(time.ticks_ms(), 1500)
        return "OK reiniciando..."


tree = None     # instancia accesible desde el REPL: import app; app.tree


def run():
    global tree
    tree = ChristmasTree()
    try:
        asyncio.run(tree.main())
    finally:
        tree.shutdown()
        asyncio.new_event_loop()
