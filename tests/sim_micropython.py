# Simulación de extremo a extremo con MicroPython real (puerto unix).
#
# Ejecuta app.py tal cual con hardware simulado (tests/mp_stubs): cambia la
# luz de la LDR, conecta un "celular" BLE, envía comandos y revisa LEDs,
# buzzer, LCD (decodificada byte a byte) y el archivo de ajustes.
#
# Uso, desde la raíz del repositorio:
#     micropython tests/sim_micropython.py
# Tarda ~25 s porque corre en tiempo real.

import os
import sys

ROOT = os.getcwd()
sys.path.insert(0, ROOT + "/tests/mp_stubs")
sys.path.insert(1, ROOT + "/firmware")
sys.path.insert(2, ROOT + "/firmware/lib")

TMP = ROOT + "/tests/_sim_tmp"
try:
    os.mkdir(TMP)
except OSError:
    pass
for name in ("settings.json", "settings.json.tmp", "error.log"):
    try:
        os.remove(TMP + "/" + name)
    except OSError:
        pass
os.chdir(TMP)

import config  # noqa: E402

config.SERIAL_COMMANDS = False
config.LDR_CONFIRM_MS = 1000
config.SETTINGS_SAVE_DELAY_MS = 500

import asyncio  # noqa: E402

import app  # noqa: E402
import bluetooth  # noqa: E402
import machine  # noqa: E402

DAY = 60000      # ~92 % de luz
NIGHT = 5000     # ~8 % de luz
results = []


def check(cond, msg):
    results.append((bool(cond), msg))
    print(("  OK   " if cond else "  FALLA") + "  " + msg)


def led_duties():
    return [machine.PWM.instances[p].duty_u16() for p in (25, 26, 27)]


async def send(ble, text, wait=250):
    ble.sim_write(text)
    await asyncio.sleep_ms(wait)
    return ble.take_replies()


async def scenario(tree):
    ble = bluetooth.BLE.instance
    lcd = machine.LCD

    print("-- 1. Arranque de dia")
    machine.ADC.value = DAY
    await asyncio.sleep_ms(1500)
    check(not tree.active, "de dia el arbol queda en reposo")
    check(led_duties() == [0, 0, 0], "LEDs apagados en reposo")
    check(not lcd.backlight, "retroiluminacion LCD apagada en reposo")

    print("-- 2. Se hace de noche")
    machine.ADC.value = NIGHT
    # filtro de la LDR (~2.5 s para bajar de 92 % a <25 %) + confirmacion (1 s)
    await asyncio.sleep_ms(4500)
    check(tree.active, "se enciende al oscurecer (tras confirmar)")
    check(tree.buzzer.playing, "toca la melodia al encenderse")
    await asyncio.sleep_ms(1000)
    check(max(led_duties()) > 0, "LEDs con brillo tras el fundido")
    check(lcd.line(0) == "\x00Feliz Navidad \x00", "LCD linea 1: Feliz Navidad")
    check(lcd.line(1).startswith("Demo"), "LCD linea 2 muestra el modo")
    check(lcd.backlight and lcd.display_on, "LCD encendida")
    freqs = machine.PWM.instances[18].freq_history
    check(659 in freqs, "el buzzer genero la nota E5 (659 Hz)")

    print("-- 3. Comandos por BLE")
    ble.sim_connect(mtu=64)
    r = await send(ble, "modo cascada")
    check("OK modo Cascada" in r, "MODO CASCADA -> " + r.strip())
    await asyncio.sleep_ms(300)
    check("\x01" in lcd.line(1) and lcd.line(1).startswith("Cascada"),
          "LCD muestra Cascada y el icono BT")
    r = await send(ble, "MÚSICA 2")
    check("We Wish You" in r, "MUSICA 2 (con acento) -> " + r.strip())
    r = await send(ble, "vol 150")
    check(r.startswith("ERR"), "VOL 150 rechazado")
    r = await send(ble, "vol 30")
    check(tree.buzzer.volume == 30, "VOL 30 aplicado")
    r = await send(ble, "palpitación")
    check(tree.mode.name == "latido", "atajo 'palpitacion' -> modo Latido")
    r = await send(ble, "umbral 30 20")
    check(r.startswith("ERR"), "UMBRAL invertido rechazado")
    r = await send(ble, "umbral 20 40")
    check(tree.detector.dark_pct == 20 and tree.detector.light_pct == 40, "UMBRAL 20 40")
    r = await send(ble, "ayuda", 600)
    check("COMANDOS" in r and "Noche de Paz" in r, "AYUDA llega completa (varios trozos)")
    r = await send(ble, "estado")
    check("ENCENDIDO" in r, "ESTADO responde")
    r = await send(ble, "luz")
    check(r.startswith("Luz"), "LUZ -> " + r.strip())
    r = await send(ble, "xyz")
    check(r.startswith("ERR"), "comando desconocido -> ERR")
    r = await send(ble, "brillo 50;vel 5")
    check(tree.settings.get("brillo") == 50 and tree.settings.get("velocidad") == 5,
          "dos comandos en una escritura (separados por ';')")

    print("-- 4. Control manual")
    r = await send(ble, "off", 1200)
    check(not tree.active and led_duties() == [0, 0, 0], "OFF apaga aunque este oscuro")
    check(not tree.buzzer.playing, "OFF detiene la musica")
    r = await send(ble, "auto", 300)
    check(tree.active, "AUTO vuelve al sensor (oscuro -> encendido)")
    await send(ble, "stop")
    check(not tree.buzzer.playing, "STOP silencia")

    print("-- 5. Amanece")
    machine.ADC.value = DAY
    await asyncio.sleep_ms(3500)
    check(not tree.active, "se apaga al haber luz")
    check(led_duties() == [0, 0, 0], "LEDs en 0 tras el fundido")
    check(not lcd.backlight and not lcd.display_on, "LCD apagada (bajo consumo)")
    check(ble.adv is not None and
          tree.ble._interval_us == config.BLE_ADV_STANDBY_MS * 1000,
          "BLE sigue disponible en reposo (anuncio mas lento)")
    r = await send(ble, "on", 300)
    check(tree.active, "ON enciende aunque sea de dia")
    await send(ble, "auto", 300)

    print("-- 6. Persistencia")
    await asyncio.sleep_ms(1500)
    try:
        import json
        with open("settings.json") as f:
            saved = json.load(f)
        check(saved["modo"] == "latido" and saved["volumen"] == 30 and
              saved["umbral_claro"] == 40, "settings.json guardado con los cambios")
    except OSError:
        check(False, "settings.json guardado con los cambios")

    print("-- 7. LCD desconectada y reconectada")
    machine.I2C.present = []
    machine.ADC.value = NIGHT
    await asyncio.sleep_ms(5000)
    check(tree.active and max(led_duties()) > 0, "sin LCD el arbol sigue funcionando")
    machine.I2C.present = [0x27]
    await asyncio.sleep_ms(6000)
    check(tree.display.ok and lcd.line(0) == "\x00Feliz Navidad \x00",
          "la LCD se reconecta sola")

    try:
        os.stat("error.log")
        check(False, "sin errores registrados en error.log")
    except OSError:
        check(True, "sin errores registrados en error.log")


async def runner():
    tree = app.ChristmasTree()
    app.tree = tree
    main_task = asyncio.create_task(tree.main())
    await scenario(tree)
    main_task.cancel()
    tree.shutdown()


asyncio.run(runner())
failed = [m for ok, m in results if not ok]
print("\n{} pruebas, {} fallas".format(len(results), len(failed)))
sys.exit(1 if failed else 0)
