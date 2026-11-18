# buzzer.py — Buzzer pasivo por PWM (a través del transistor Q4).
#
# Un buzzer pasivo no tiene oscilador: suena a la frecuencia del PWM.
# - Nota  = frecuencia del PWM
# - Volumen ≈ ciclo de trabajo (50 % es el máximo; más de eso no suena más fuerte)
# Las melodías se tocan como tarea asyncio, sin bloquear las animaciones.

from machine import PWM, Pin

try:
    import asyncio
except ImportError:
    import uasyncio as asyncio

from melodies import note_freq

_MAX_DUTY = 32768   # 50 % de 65535


class Buzzer:
    def __init__(self, pin, volume=60):
        self._pin = pin
        Pin(pin, Pin.OUT, value=0)
        self._pwm = PWM(Pin(pin), freq=1000, duty_u16=0)
        self._volume = 0
        self.volume = volume
        self._task = None
        self._gen = 0           # identifica la reproducción vigente
        self.playing = False
        self.current = None     # nombre de la melodía en curso

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value):
        self._volume = max(0, min(100, int(value)))

    def tone(self, freq):
        if freq <= 0 or self._volume == 0:
            self._pwm.duty_u16(0)
            return
        self._pwm.freq(int(freq))
        self._pwm.duty_u16(self._volume * _MAX_DUTY // 100)

    def silence(self):
        self._pwm.duty_u16(0)

    async def _play(self, melody, gen):
        beat_ms = 60000 / melody["tempo"]
        try:
            for note, beats in melody["notas"]:
                if gen != self._gen:
                    return
                dur = int(beats * beat_ms)
                gap = dur // 10        # 10 % de silencio separa notas repetidas
                f = note_freq(note)
                if f:
                    self.tone(f)
                    await asyncio.sleep_ms(dur - gap)
                    self.silence()
                    await asyncio.sleep_ms(gap)
                else:
                    self.silence()
                    await asyncio.sleep_ms(dur)
        finally:
            if gen == self._gen:       # no pisar una melodía más nueva
                self.silence()
                self.playing = False
                self.current = None

    def start(self, melody):
        """Toca una melodía en segundo plano; cancela la anterior si la había."""
        self.stop()
        self._gen += 1
        self.playing = True
        self.current = melody["nombre"]
        self._task = asyncio.create_task(self._play(melody, self._gen))

    def stop(self):
        self._gen += 1
        if self._task is not None:
            try:
                self._task.cancel()
            except Exception:
                pass  # la tarea ya había terminado
            self._task = None
        self.silence()
        self.playing = False
        self.current = None

    def deinit(self):
        self.stop()
        try:
            self._pwm.deinit()
        except Exception:
            pass
        Pin(self._pin, Pin.OUT, value=0)
