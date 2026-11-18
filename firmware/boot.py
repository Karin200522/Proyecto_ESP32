# boot.py — Se ejecuta en cada arranque, antes de main.py.
#
# Solo prepara el hardware de forma segura. La aplicación arranca en main.py.
# Nota: aquí NO se importa `network`. En el ESP32, crear un objeto WLAN
# inicializa el driver Wi-Fi y gasta ~40 KB de RAM aunque quede inactivo.
# Este proyecto solo usa BLE, así que el Wi-Fi ni se toca.

import gc
import machine

import config

# 1) Salidas de potencia en bajo lo antes posible. Las resistencias de 10 kΩ
#    ya mantienen apagados los transistores, esto es una segunda protección.
for _pin in (config.PIN_LED_AMARILLO, config.PIN_LED_ROJO,
             config.PIN_LED_VERDE, config.PIN_BUZZER):
    machine.Pin(_pin, machine.Pin.OUT, value=0)

# 2) Silenciar los mensajes de depuración del sistema por el UART.
try:
    import esp
    esp.osdebug(None)
except Exception:
    pass

# 3) Frecuencia de CPU (menos MHz = menos consumo y calor).
try:
    machine.freq(config.CPU_FREQ_HZ)
except Exception:
    pass

gc.collect()
