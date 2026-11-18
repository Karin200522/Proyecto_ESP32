# Stub de `machine` para simular el firmware en MicroPython (puerto unix).
# Incluye un emulador de LCD HD44780 detrás del PCF8574 para comprobar
# qué texto aparecería realmente en la pantalla.


class Pin:
    IN = 0
    OUT = 1
    PULL_UP = 2

    def __init__(self, id, mode=-1, pull=-1, value=None):
        self.id = id
        if value is not None:
            self._v = value
        else:
            self._v = 1 if id == 0 else 0   # BOOT sin presionar

    def value(self, v=None):
        if v is None:
            return self._v
        self._v = v


class PWM:
    instances = {}

    def __init__(self, pin, freq=5000, duty_u16=0):
        self.pin = pin.id
        self._freq = freq
        self._duty = duty_u16
        self.freq_history = []
        PWM.instances[self.pin] = self

    def freq(self, f=None):
        if f is None:
            return self._freq
        self._freq = f
        self.freq_history.append(f)

    def duty_u16(self, d=None):
        if d is None:
            return self._duty
        self._duty = d

    def deinit(self):
        self._duty = 0


class ADC:
    ATTN_11DB = 3
    value = 60000          # la simulación cambia este valor (0-65535)

    def __init__(self, pin):
        pass

    def atten(self, a):
        pass

    def read_u16(self):
        return ADC.value


class LcdEmulator:
    """Decodifica los bytes del PCF8574 como lo haría un HD44780."""
    EN = 0x04

    def __init__(self):
        self.mode8 = True
        self.pending = None
        self.last = 0
        self.ddram = bytearray(b" " * 0x68)
        self.addr = 0
        self.cgram_mode = False
        self.cgram = bytearray(64)
        self.display_on = False
        self.backlight = False

    def feed(self, byte):
        self.backlight = bool(byte & 0x08)
        if (self.last & self.EN) and not (byte & self.EN):   # flanco de bajada de E
            nib = (self.last >> 4) & 0x0F
            rs = self.last & 0x01
            if self.mode8:
                if nib == 0x2:
                    self.mode8 = False
            elif self.pending is None:
                self.pending = nib
            else:
                self._process((self.pending << 4) | nib, rs)
                self.pending = None
        self.last = byte

    def _process(self, v, rs):
        if rs == 0:
            if v == 0x01:
                self.ddram = bytearray(b" " * 0x68)
                self.addr = 0
                self.cgram_mode = False
            elif v & 0x80:
                self.addr = v & 0x7F
                self.cgram_mode = False
            elif v & 0x40:
                self.addr = v & 0x3F
                self.cgram_mode = True
            elif v & 0xF8 == 0x08:
                self.display_on = bool(v & 0x04)
        elif self.cgram_mode:
            self.cgram[self.addr & 0x3F] = v
            self.addr += 1
        else:
            self.ddram[self.addr % 0x68] = v
            self.addr += 1

    def line(self, row):
        base = 0x00 if row == 0 else 0x40
        return "".join(chr(c) for c in self.ddram[base:base + 16])


LCD = LcdEmulator()


class I2C:
    present = [0x27]

    def __init__(self, id, scl=None, sda=None, freq=100000):
        pass

    def scan(self):
        return list(I2C.present)

    def writeto(self, addr, buf):
        if addr not in I2C.present:
            raise OSError(19)
        for b in buf:
            LCD.feed(b)
        return len(buf)


class WDT:
    def __init__(self, timeout=5000):
        pass

    def feed(self):
        pass


def freq(f=None):
    return 160000000


def reset():
    raise SystemExit("machine.reset()")
