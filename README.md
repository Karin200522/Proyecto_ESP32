# 🎄 Proyecto_ESP32 — Pino de Navidad inteligente

Árbol de Navidad con **ESP32 + MicroPython** armado en protoboard:

- **36 LEDs** en 3 canales (12 amarillos, 12 rojos y 12 verdes) con PWM, cada canal a través de un transistor **2N2222A**.
- **9 animaciones**: fijo, alterno, cascada, respira, latido (palpitación), onda, destello, persecución y demo.
- **Modo automático por luz (LDR)**: se enciende cuando la habitación está oscura y pasa a bajo consumo de día.
  Usa histéresis y tiempo de confirmación para no parpadear.
- **Control por Bluetooth LE** (Nordic UART) desde la app **nRF Connect**.
- **Buzzer pasivo** con 3 villancicos por PWM. Suena al encenderse el árbol o al pedirlo por BLE.
- **LCD 16x2 I2C** con "Feliz Navidad", el modo actual e íconos de música y Bluetooth.
- Firmware **robusto**: tareas asyncio supervisadas, registro de errores en `error.log`,
  ajustes persistentes con escritura atómica, LCD reconectable, modo seguro y *watchdog* opcional.

> ⚠️ El esquemático en **KiCad** está pendiente (`hardware/kicad/`). Mientras tanto,
> el cableado completo y los cálculos están en [`hardware/CONEXIONES.md`](hardware/CONEXIONES.md).

---

## Estructura del repositorio

```
Proyecto_ESP32/
├── README.md                  ← este archivo
├── .gitignore
├── firmware/                  ← TODO lo que se copia al ESP32
│   ├── boot.py                  arranque seguro (salidas en 0, CPU a 160 MHz)
│   ├── main.py                  punto de entrada, modo seguro y manejo de errores
│   ├── config.py                pines y parámetros (edítalo si cambias el cableado)
│   ├── app.py                   orquestador asyncio y comandos
│   └── lib/
│       ├── animations.py        modos de animación (lógica pura)
│       ├── ble_uart.py          periférico BLE con el servicio Nordic UART
│       ├── buzzer.py            notas y melodías por PWM
│       ├── commands.py          interpretación de comandos de texto
│       ├── display.py           pantalla tolerante a fallos e íconos propios
│       ├── errlog.py            registro de errores en error.log
│       ├── lcd_i2c.py           driver HD44780 + PCF8574
│       ├── leds.py              PWM de los 3 canales con corrección gamma
│       ├── light_sensor.py      LDR (ADC) + detector día/noche con histéresis
│       ├── melodies.py          villancicos en notación de notas
│       └── settings.py          ajustes persistentes (JSON con escritura atómica)
├── hardware/
│   ├── CONEXIONES.md            pinout, esquemas de cada etapa, cálculos, BOM y montaje
│   ├── BOM.csv                  lista de materiales
│   └── kicad/                   esquemático KiCad (pendiente)
├── docs/
│   └── COMANDOS_BLE.md          guía de nRF Connect, comandos y calibración de la LDR
├── tools/
│   └── deploy.py                copia el firmware al ESP32 con mpremote
└── tests/
    ├── test_logic.py            pruebas de lógica en la PC (CPython)
    ├── sim_micropython.py       simulación completa con MicroPython (puerto unix)
    └── mp_stubs/                hardware simulado (machine, bluetooth, esp)
```

---

## Puesta en marcha

### 1. Instalar MicroPython en el ESP32 (una sola vez)
1. Descarga el firmware **ESP32_GENERIC** (v1.22 o más reciente; trae BLE) desde
   <https://micropython.org/download/ESP32_GENERIC/>.
2. Grábalo (cambia `COM5` por tu puerto: `/dev/ttyUSB0` en Linux, `/dev/cu.usbserial-…` en macOS):
   ```bash
   pip install esptool
   python -m esptool --chip esp32 --port COM5 erase_flash
   python -m esptool --chip esp32 --port COM5 --baud 460800 write_flash -z 0x1000 ESP32_GENERIC-<versión>.bin
   ```
   Thonny también puede hacerlo: *Herramientas → Opciones → Intérprete → Instalar o actualizar MicroPython*.

### 2. Copiar el firmware
**Opción A — script (recomendado):**
```bash
pip install mpremote
python tools/deploy.py --port COM5
```
**Opción B — Thonny:** con *Ver → Archivos*, sube `boot.py`, `main.py`, `config.py` y `app.py` a la raíz del ESP32.
Crea la carpeta `lib` y sube ahí todo el contenido de `firmware/lib/`.

> Mientras el ESP32 esté conectado por USB, **desconecta el cable VIN** de la fuente de 4.5 V
> (deja GND conectado). La explicación está en `hardware/CONEXIONES.md`, sección 1.

### 3. Probar
Al reiniciar, la consola debe mostrar algo así:
```
=== Pino de Navidad ESP32 ===
[LCD] OK en 0x27
[BLE] anunciando cada 1000 ms
[PINO] listo. Escribe AYUDA (por BLE o aqui en la consola).
[LDR] OSCURO (luz 12%)
[PINO] ENCENDIDO (auto)
```
Escribe `ESTADO` en la consola de Thonny o conéctate con nRF Connect ([guía](docs/COMANDOS_BLE.md)).

---

## Funcionamiento

| Condición | Árbol | LEDs | LCD | Buzzer | BLE |
|---|---|---|---|---|---|
| `AUTO` + habitación oscura | **Encendido** | Animación activa (fundido de 0.8 s) | "Feliz Navidad" + modo + íconos | Melodía al encender (si `AUTOMUSICA SI`) | Anuncio cada 250 ms |
| `AUTO` + luz de día | **Reposo** | Apagados | Pantalla y retroiluminación apagadas | Silencio | Anuncio cada 1 s (sigue aceptando comandos) |
| `ON` / `OFF` | Forzado | — | — | — | — |

La línea 2 de la LCD muestra el modo actual, una ♪ mientras suena música y el ícono de Bluetooth si hay un celular conectado.

### Personalización (`firmware/config.py`)
- Pines, frecuencia del PWM, nombre BLE, tiempos de la LDR y valores por defecto (`DEFAULTS`).
- `LDR_INVERT = True` si conectaste la LDR del lado de GND.
- `LCD_ADDR = 0x27` (u otra) si no quieres la autodetección.

### Robustez
- **Modo seguro:** presiona y suelta **EN** y, durante el primer segundo, mantén **BOOT**. La app no arranca y el REPL queda libre para cargar archivos.
- **Errores:** si una tarea falla, se registra en `error.log` y la tarea se reinicia sola. Si falla el arranque, el ESP32 se reinicia a los 10 s.
- **Watchdog:** para la versión final, pon `USE_WDT = True` en `config.py`. Si el programa se congela, el ESP32 se reinicia solo.
  Déjalo en `False` mientras desarrollas: con el watchdog activo, detener el programa con Ctrl-C provoca un reinicio a los 8 s.
- **Sin LCD o sin BLE**, el árbol sigue funcionando con el sensor de luz. La LCD se reintenta cada 5 s.

---

## Pruebas (en la PC, sin ESP32)
```bash
python -m unittest discover -s tests -v       # lógica: animaciones, LDR, comandos, melodías, ajustes
micropython tests/sim_micropython.py          # simulación completa (requiere MicroPython para PC)
```
La simulación ejecuta `app.py` con hardware simulado. Recorre el ciclo día → noche → comandos BLE → amanecer → persistencia → desconexión y reconexión de la LCD, y decodifica los bytes I2C para verificar el texto que mostraría la pantalla.

---

## Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| La LCD enciende pero sin texto | Contraste | Gira el potenciómetro azul del módulo I2C |
| `[LCD] no disponible` | SDA/SCL invertidos, sin GND común o dirección distinta | Revisa el cableado; `ESTADO` muestra si la LCD responde |
| El árbol se enciende y apaga en ciclos | La LDR ve la luz de los LEDs | Cambia la LDR de lugar o recalibra (`docs/COMANDOS_BLE.md`) |
| Reinicios al encender todos los LEDs | Caída de voltaje (*brownout*) | C1 más grande, cables más cortos, `BRILLO 60` |
| Un canal no enciende | Transistor con otro orden de patas | Verifica E-B-C con el datasheet o el multímetro |
| No aparece `PinoNavidad` en nRF Connect | Firmware sin BLE o la app falló al iniciar | Usa el firmware ESP32_GENERIC; revisa `error.log` |
| Buzzer muy bajo | Es piezoeléctrico o la R serie es alta | Agrega 1 kΩ en paralelo (piezo), baja la R de 47 Ω, `VOL 100` |
