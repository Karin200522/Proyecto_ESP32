# display.py — Capa de pantalla tolerante a fallos sobre lcd_i2c.
#
# - Autodetecta la dirección I2C (PCF8574: 0x20-0x27, PCF8574A: 0x38-0x3F).
# - Solo reescribe las líneas que cambiaron (sin parpadeo y con poco I2C).
# - Si la LCD se desconecta o falla, el árbol sigue funcionando y la app
#   reintenta conectarla periódicamente.

from lcd_i2c import LcdI2C

# Caracteres propios (5x8). Se usan dentro del texto como TREE, BT y NOTE.
TREE = "\x00"
BT = "\x01"
NOTE = "\x02"
_GLYPHS = (
    bytes((0x04, 0x0E, 0x1F, 0x04, 0x0E, 0x1F, 0x04, 0x04)),  # pino
    bytes((0x04, 0x06, 0x15, 0x0E, 0x0E, 0x15, 0x06, 0x04)),  # Bluetooth
    bytes((0x02, 0x03, 0x02, 0x02, 0x0E, 0x1E, 0x0C, 0x00)),  # nota musical
)


class Display:
    def __init__(self, i2c, addr=None, cols=16, rows=2):
        self._i2c = i2c
        self._addr = addr
        self.cols = cols
        self.rows = rows
        self._lcd = None
        self._lines = [None] * rows
        self._powered = None
        self._warned = False
        self.connect()

    @property
    def ok(self):
        return self._lcd is not None

    def _scan(self):
        for a in self._i2c.scan():
            if 0x20 <= a <= 0x27 or 0x38 <= a <= 0x3F:
                return a
        return None

    def connect(self):
        try:
            addr = self._addr if self._addr is not None else self._scan()
            if addr is None:
                raise OSError("no se encontro la LCD en el bus I2C")
            lcd = LcdI2C(self._i2c, addr, self.cols, self.rows)
            for slot, pattern in enumerate(_GLYPHS):
                lcd.custom_char(slot, pattern)
            self._lcd = lcd
            self._lines = [None] * self.rows
            self._powered = True
            self._warned = False
            print("[LCD] OK en 0x{:02X}".format(addr))
            return True
        except OSError as e:
            self._fail(e)
            return False

    def _fail(self, err):
        if not self._warned:
            print("[LCD] no disponible:", err)
            self._warned = True
        self._lcd = None

    def show(self, *lines):
        """Muestra hasta `rows` líneas; recorta o rellena a `cols` caracteres."""
        if self._lcd is None:
            return
        try:
            for row in range(min(len(lines), self.rows)):
                text = (lines[row] + " " * self.cols)[:self.cols]
                if text != self._lines[row]:
                    self._lcd.move_to(0, row)
                    self._lcd.putstr(text)
                    self._lines[row] = text
        except OSError as e:
            self._fail(e)

    def power(self, on):
        """Enciende o apaga pantalla y retroiluminación (bajo consumo)."""
        if self._lcd is None or on == self._powered:
            return
        try:
            self._lcd.backlight(on)
            self._lcd.display(on)
            self._powered = on
        except OSError as e:
            self._fail(e)
