# light_sensor.py — Lectura de la LDR y detección de día/noche con histéresis.
#
# Divisor: 3V3 ── LDR ──┬── GPIO34 ── 10 kΩ ── GND
# Más luz → menor resistencia de la LDR → más voltaje → mayor porcentaje.
#
# Dos clases:
#   LightSensor   → hardware: promedia el ADC y devuelve % de luz (0-100).
#   DarkDetector  → lógica pura: decide "oscuro"/"claro" sin parpadeos.

try:
    from time import ticks_diff
except ImportError:  # CPython (pruebas en la PC)
    def ticks_diff(a, b):
        return a - b


class LightSensor:
    def __init__(self, pin, samples=16, invert=False):
        from machine import ADC, Pin
        self._adc = ADC(Pin(pin))
        # 11 dB de atenuación → rango útil de ~0.15 V a ~3.1 V
        self._adc.atten(ADC.ATTN_11DB)
        self._n = max(1, samples)
        self._invert = invert
        self._filtered = None

    def read_raw_pct(self):
        """Promedio de N lecturas, en % de la escala del ADC."""
        acc = 0
        for _ in range(self._n):
            acc += self._adc.read_u16()
        pct = acc * 100 / (self._n * 65535)
        return 100 - pct if self._invert else pct

    def read_pct(self):
        """Lectura con filtro exponencial (atenúa ruido y destellos breves)."""
        pct = self.read_raw_pct()
        if self._filtered is None:
            self._filtered = pct
        else:
            self._filtered += 0.3 * (pct - self._filtered)
        return self._filtered


class DarkDetector:
    """Histéresis + tiempo de confirmación.

    - Está CLARO y la luz baja de `dark_pct` durante `confirm_ms` → OSCURO.
    - Está OSCURO y la luz sube de `light_pct` durante `confirm_ms` → CLARO.
    - Entre ambos umbrales no cambia nada: así el árbol no "tiembla" al
      atardecer ni cuando alguien pasa frente al sensor.
    """

    def __init__(self, dark_pct, light_pct, confirm_ms):
        self.set_thresholds(dark_pct, light_pct)
        self.confirm_ms = confirm_ms
        self.is_dark = None          # desconocido hasta la primera lectura
        self._since = None

    def set_thresholds(self, dark_pct, light_pct):
        if not (0 <= dark_pct < light_pct <= 100):
            raise ValueError("se requiere 0 <= oscuro < claro <= 100")
        self.dark_pct = dark_pct
        self.light_pct = light_pct
        self._since = None

    def update(self, pct, now_ms):
        """Procesa una lectura. Devuelve True si el estado cambió."""
        if self.is_dark is None:
            # Arranque: decidir de inmediato con el punto medio
            self.is_dark = pct < (self.dark_pct + self.light_pct) / 2
            return True
        if self.is_dark:
            wants_change = pct > self.light_pct
        else:
            wants_change = pct < self.dark_pct
        if not wants_change:
            self._since = None
            return False
        if self._since is None:
            self._since = now_ms
            return False
        if ticks_diff(now_ms, self._since) >= self.confirm_ms:
            self.is_dark = not self.is_dark
            self._since = None
            return True
        return False
