# leds.py — Control PWM de los 3 canales de LEDs (amarillo, rojo, verde).
#
# Cada GPIO maneja la base de un 2N2222A que conmuta el lado bajo de 12 LEDs.
# GPIO en alto → transistor saturado → LEDs encendidos. Por eso el ciclo de
# trabajo del PWM equivale directamente al brillo.
#
# Se aplica corrección gamma: el ojo percibe el brillo de forma logarítmica,
# así que sin ella los fundidos se ven "pegados" arriba y bruscos abajo.

from array import array

from machine import PWM, Pin


def _gamma_table(gamma=2.2):
    table = array("H", [0] * 256)
    for i in range(256):
        table[i] = int(((i / 255) ** gamma) * 65535 + 0.5)
    return table


class LedChannels:
    NAMES = ("amarillo", "rojo", "verde")

    def __init__(self, pins, freq):
        self._pins = tuple(pins)
        self._pwm = []
        for p in self._pins:
            Pin(p, Pin.OUT, value=0)
            # duty_u16=0 en el constructor evita un destello al 50 % al crear el PWM
            self._pwm.append(PWM(Pin(p), freq=freq, duty_u16=0))
        self._gamma = _gamma_table()
        self._levels = [0, 0, 0]

    def write(self, levels, scale=1.0):
        """levels: 3 valores 0-255 (amarillo, rojo, verde).
        scale: 0.0-1.0 (brillo global × fundido)."""
        g = self._gamma
        for i in range(3):
            v = int(levels[i] * scale + 0.5)
            if v < 0:
                v = 0
            elif v > 255:
                v = 255
            if v != self._levels[i]:
                self._levels[i] = v
                self._pwm[i].duty_u16(g[v])

    def off(self):
        self.write((0, 0, 0))

    @property
    def levels(self):
        return tuple(self._levels)

    def deinit(self):
        for pwm in self._pwm:
            try:
                pwm.duty_u16(0)
                pwm.deinit()
            except Exception:
                pass
        for p in self._pins:
            Pin(p, Pin.OUT, value=0)
