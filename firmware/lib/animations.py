# animations.py — Modos de animación de los 3 canales de LEDs.
#
# Cada modo es un objeto con frame(t) que devuelve (amarillo, rojo, verde)
# en niveles 0-255. «t» es el tiempo de animación en ms (entero), ya escalado
# por la velocidad elegida. Este módulo no toca hardware, por eso se puede
# probar en la PC (ver tests/).
#
# Para agregar un modo: crea una clase que herede de Mode, define name/label
# y frame(), y agrégala a la lista de build_modes().

import math

try:
    from random import getrandbits
except ImportError:  # firmwares antiguos
    from urandom import getrandbits

# El reloj de animación vuelve a 0 cada WRAP_MS para no perder precisión con
# el tiempo (los float del ESP32 son de 32 bits). Todos los periodos de los
# modos dividen exactamente este valor, así que el salto no se nota.
WRAP_MS = 960000

_TWO_PI = 2 * math.pi
_THIRD = _TWO_PI / 3


def _clamp255(x):
    x = int(x + 0.5)
    if x < 0:
        return 0
    return 255 if x > 255 else x


def _trapezoid(x, rise, hold, fall):
    """Envolvente 0→1→1→0 sobre x en [0, 1)."""
    if x < rise:
        return x / rise
    x -= rise
    if x < hold:
        return 1.0
    x -= hold
    if x < fall:
        return 1.0 - x / fall
    return 0.0


def _pulse(x, center, half_width):
    """Pulso triangular de altura 1 centrado en «center»."""
    d = abs(x - center)
    return 0.0 if d >= half_width else 1.0 - d / half_width


class Mode:
    name = "base"      # identificador: minúsculas, sin acentos
    label = "Base"     # texto para la LCD (máx. 12 caracteres, solo ASCII)
    aliases = ()

    def reset(self):
        pass

    def frame(self, t):
        return (0, 0, 0)


class Solid(Mode):
    """Todos los LEDs encendidos fijos."""
    name = "fijo"
    label = "Fijo"
    aliases = ("todos", "encendido", "solid")

    def frame(self, t):
        return (255, 255, 255)


class Alternate(Mode):
    """Parpadeo alterno: (amarillo + verde) <-> rojo."""
    name = "alterno"
    label = "Alterno"
    aliases = ("parpadeo", "blink")
    HALF = 500

    def frame(self, t):
        if (t // self.HALF) % 2 == 0:
            return (255, 0, 255)
        return (0, 255, 0)


class Cascade(Mode):
    """Los colores se encienden uno tras otro y se apagan en el mismo orden."""
    name = "cascada"
    label = "Cascada"
    aliases = ("cascade",)
    PERIOD = 4000
    OFFSET = 500

    def frame(self, t):
        out = []
        for i in range(3):
            x = ((t - i * self.OFFSET) % self.PERIOD) / self.PERIOD
            out.append(_clamp255(255 * _trapezoid(x, 0.12, 0.40, 0.12)))
        return tuple(out)


class Breathe(Mode):
    """Respiración suave de todo el árbol."""
    name = "respira"
    label = "Respira"
    aliases = ("respiracion", "breathe", "fade")
    PERIOD = 4000
    FLOOR = 0.06

    def frame(self, t):
        s = 0.5 - 0.5 * math.cos(_TWO_PI * (t % self.PERIOD) / self.PERIOD)
        v = _clamp255(255 * (self.FLOOR + (1 - self.FLOOR) * s))
        return (v, v, v)


class Heartbeat(Mode):
    """Palpitación: doble pulso (lub-dub) y pausa. El rojo late más fuerte."""
    name = "latido"
    label = "Latido"
    aliases = ("palpitacion", "palpita", "heartbeat", "corazon")
    PERIOD = 1200
    FLOOR = 0.08

    def frame(self, t):
        x = t % self.PERIOD
        p = max(_pulse(x, 90, 90), 0.65 * _pulse(x, 330, 100))
        v = self.FLOOR + (1 - self.FLOOR) * p
        return (_clamp255(180 * v), _clamp255(255 * v), _clamp255(180 * v))


class Wave(Mode):
    """Onda senoidal desfasada 120° entre colores."""
    name = "onda"
    label = "Onda"
    aliases = ("ola", "wave", "arcoiris")
    PERIOD = 3000

    def frame(self, t):
        ph = _TWO_PI * (t % self.PERIOD) / self.PERIOD
        return tuple(_clamp255(127.5 + 127.5 * math.sin(ph - i * _THIRD))
                     for i in range(3))


class Twinkle(Mode):
    """Destellos aleatorios, como luces de verdad."""
    name = "destello"
    label = "Destello"
    aliases = ("destellos", "aleatorio", "twinkle", "random")
    SMOOTH_MS = 120

    def __init__(self):
        self.reset()

    def reset(self):
        self._cur = [0.0, 0.0, 0.0]
        self._target = [0, 0, 0]
        self._next = [0, 0, 0]
        self._last = None

    def frame(self, t):
        if self._last is None or t < self._last:
            # primer cuadro, o el reloj de animación dio la vuelta (WRAP_MS)
            self._last = t
            self._next = [t, t, t]
        dt = t - self._last
        self._last = t
        k = dt / self.SMOOTH_MS
        if k > 1:
            k = 1.0
        out = []
        for i in range(3):
            if t >= self._next[i]:
                r = getrandbits(8)
                # 1 de cada 4 veces destello a tope; si no, un nivel medio
                self._target[i] = 255 if r < 64 else 20 + ((r * 180) >> 8)
                self._next[i] = t + 150 + getrandbits(9)   # 150-661 ms
            self._cur[i] += (self._target[i] - self._cur[i]) * k
            out.append(_clamp255(self._cur[i]))
        return tuple(out)


class Chase(Mode):
    """Persecución: un color a la vez, rápido."""
    name = "persecucion"
    label = "Persecucion"
    aliases = ("secuencia", "chase", "carrera")
    STEP = 250

    def frame(self, t):
        idx = (t // self.STEP) % 3
        return tuple(255 if i == idx else 0 for i in range(3))


class Demo(Mode):
    """Recorre todos los modos, 12 s cada uno."""
    name = "demo"
    label = "Demo"
    aliases = ("ciclo", "show")
    SLOT = 12000

    def __init__(self, modes):
        self._modes = modes
        self._idx = -1

    def reset(self):
        self._idx = -1

    def frame(self, t):
        idx = (t // self.SLOT) % len(self._modes)
        if idx != self._idx:
            self._idx = idx
            self._modes[idx].reset()
        return self._modes[idx].frame(t)


def build_modes():
    """Lista ordenada de modos. El número de cada modo es su posición + 1."""
    base = [Solid(), Alternate(), Cascade(), Breathe(),
            Heartbeat(), Wave(), Twinkle(), Chase()]
    return base + [Demo(base)]


def find_mode(modes, key):
    """Busca un modo por número (1..n), nombre, alias o prefijo de 3+ letras.
    Devuelve None si no existe."""
    if key is None:
        return None
    if isinstance(key, int):
        idx = key
    else:
        key = str(key).strip().lower()
        if not key.isdigit():
            for m in modes:
                if key == m.name or key in m.aliases:
                    return m
            if len(key) >= 3:
                for m in modes:
                    if m.name.startswith(key):
                        return m
            return None
        idx = int(key)
    if 1 <= idx <= len(modes):
        return modes[idx - 1]
    return None
