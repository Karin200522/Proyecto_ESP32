# config.py — Configuración de hardware y valores por defecto
# Pino de Navidad inteligente · ESP32 + MicroPython
#
# Todo lo que dependa del cableado está aquí. Si cambias un pin en la
# protoboard, cámbialo también en este archivo (y en hardware/CONEXIONES.md).

# ---------------------------------------------------------------- Pines
PIN_LED_AMARILLO = 25   # Base de Q1 (2N2222A) vía 330 Ω
PIN_LED_ROJO = 26       # Base de Q2 vía 330 Ω
PIN_LED_VERDE = 27      # Base de Q3 vía 330 Ω
PIN_BUZZER = 18         # Base de Q4 vía 1 kΩ
PIN_I2C_SDA = 21
PIN_I2C_SCL = 22
PIN_LDR = 34            # ADC1_CH6 (solo entrada). No usar pines ADC2.
PIN_BOOT = 0            # Botón BOOT de la placa → modo seguro

# ---------------------------------------------------------------- Sistema
CPU_FREQ_HZ = 160_000_000   # 160 MHz sobra para esta app y gasta menos que 240
SAFE_MODE_WINDOW_MS = 1000  # tiempo para presionar BOOT tras reiniciar
USE_WDT = False             # pon True en la versión final (ver README)
WDT_TIMEOUT_MS = 8000
AUTO_RESET_ON_ERROR = True  # si la app falla, guarda el error y reinicia
ERROR_LOG = "error.log"
ERROR_LOG_MAX_BYTES = 4096
SERIAL_COMMANDS = True      # acepta los mismos comandos por la consola USB

# ---------------------------------------------------------------- LEDs
LED_PWM_FREQ = 5000         # Hz. No coincide con ninguna nota de las melodías
ANIM_FRAME_MS = 20          # 50 cuadros por segundo
FADE_MS = 800               # fundido al encender y apagar el árbol
SPEED_FACTORS = (0.5, 0.75, 1.0, 1.5, 2.0)  # VEL 1..5

# ---------------------------------------------------------------- LCD I2C
I2C_FREQ = 100_000          # 100 kHz: más tolerante a cables largos en protoboard
LCD_ADDR = None             # None = autodetectar (0x27 / 0x3F); o p. ej. 0x27
LCD_COLS = 16
LCD_ROWS = 2

# ---------------------------------------------------------------- BLE
BLE_NAME = "PinoNavidad"    # nombre visible en nRF Connect (máx. ~20 caracteres)
BLE_ADV_ACTIVE_MS = 250     # intervalo de anuncio con el árbol encendido
BLE_ADV_STANDBY_MS = 1000   # intervalo más largo en reposo → menos consumo

# ---------------------------------------------------------------- LDR
LDR_SAMPLES = 16            # lecturas promediadas por medición
LDR_PERIOD_MS = 500         # cada cuánto se mide
LDR_CONFIRM_MS = 5000       # el cambio claro/oscuro debe sostenerse este tiempo
LDR_INVERT = False          # True si la LDR va a GND y la 10 kΩ a 3V3

# ---------------------------------------------------------------- Ajustes
SETTINGS_FILE = "settings.json"
SETTINGS_SAVE_DELAY_MS = 5000   # espera tras el último cambio (cuida la flash)

# Valores por defecto. Se guardan en settings.json cuando se cambian por BLE.
DEFAULTS = {
    "modo": "demo",         # fijo, alterno, cascada, respira, latido, onda,
                            # destello, persecucion, demo
    "brillo": 80,           # % (10-100)
    "velocidad": 3,         # 1-5
    "volumen": 60,          # % (0-100)
    "melodia": 1,           # 1-3
    "auto_musica": True,    # tocar la melodía al encenderse el árbol
    "umbral_oscuro": 25,    # % de luz por debajo del cual se considera oscuro
    "umbral_claro": 45,     # % de luz por encima del cual se considera de día
}
