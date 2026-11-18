# lcd_i2c.py — Driver mínimo para LCD HD44780 con módulo I2C PCF8574.
#
# Mapeo del PCF8574 en los módulos comunes (LCM1602 / FC-113):
#   P0 = RS   P1 = RW   P2 = E   P3 = retroiluminación   P4..P7 = D4..D7
# La LCD trabaja en modo de 4 bits: cada byte se envía en dos nibbles.
# Cada carácter se manda en una sola transacción I2C de 4 bytes, con el
# pulso de E incluido. A 100 kHz cada byte tarda ~90 µs, más que los 37 µs
# que necesita la LCD por instrucción.

import time

_RS = 0x01
_EN = 0x04
_BL = 0x08

_CLEAR = 0x01
_ENTRY_INC = 0x06       # cursor avanza, sin desplazar la pantalla
_DISPLAY_ON = 0x0C      # pantalla encendida, sin cursor ni parpadeo
_DISPLAY_OFF = 0x08
_FUNCTION_4BIT_2L = 0x28
_SET_CGRAM = 0x40
_SET_DDRAM = 0x80


class LcdI2C:
    ROW_OFFSETS = (0x00, 0x40, 0x14, 0x54)

    def __init__(self, i2c, addr, cols=16, rows=2):
        self.i2c = i2c
        self.addr = addr
        self.cols = cols
        self.rows = rows
        self._bl = _BL
        self._buf = bytearray(4)
        self._init_sequence()

    # ------------------------------------------------------------ bajo nivel
    def _expander(self, value):
        self.i2c.writeto(self.addr, bytes((value | self._bl,)))

    def _nibble(self, high_bits):
        b = (high_bits & 0xF0) | self._bl
        self.i2c.writeto(self.addr, bytes((b | _EN, b)))

    def _send(self, value, rs):
        hi = (value & 0xF0) | rs | self._bl
        lo = ((value << 4) & 0xF0) | rs | self._bl
        buf = self._buf
        buf[0] = hi | _EN
        buf[1] = hi
        buf[2] = lo | _EN
        buf[3] = lo
        self.i2c.writeto(self.addr, buf)

    def _init_sequence(self):
        # Secuencia de "inicialización por instrucciones" del datasheet HD44780
        time.sleep_ms(50)
        self._expander(0)
        for delay in (5, 1, 1):
            self._nibble(0x30)
            time.sleep_ms(delay)
        self._nibble(0x20)              # pasa a modo de 4 bits
        time.sleep_ms(1)
        self.command(_FUNCTION_4BIT_2L)
        self.command(_DISPLAY_OFF)
        self.clear()
        self.command(_ENTRY_INC)
        self.command(_DISPLAY_ON)

    # ------------------------------------------------------------ API pública
    def command(self, cmd):
        self._send(cmd, 0)
        if cmd <= 3:                    # clear / home tardan ~1.5 ms
            time.sleep_ms(2)

    def clear(self):
        self.command(_CLEAR)

    def move_to(self, col, row):
        self.command(_SET_DDRAM | (self.ROW_OFFSETS[row] + col))

    def putstr(self, text):
        """Escribe el texto en una sola transacción I2C."""
        data = bytearray(4 * len(text))
        bl = self._bl
        i = 0
        for ch in text:
            c = ord(ch)
            if c > 127:                 # la ROM no tiene acentos → '?'
                c = 0x3F
            hi = (c & 0xF0) | _RS | bl
            lo = ((c << 4) & 0xF0) | _RS | bl
            data[i] = hi | _EN
            data[i + 1] = hi
            data[i + 2] = lo | _EN
            data[i + 3] = lo
            i += 4
        if data:
            self.i2c.writeto(self.addr, data)

    def custom_char(self, slot, pattern):
        """Define un carácter propio (slot 0-7, 8 filas de 5 bits).
        Se usa luego como chr(slot) dentro del texto."""
        self.command(_SET_CGRAM | ((slot & 7) << 3))
        for row in pattern[:8]:
            self._send(row & 0x1F, _RS)
        self.command(_SET_DDRAM)        # regresar a la memoria de pantalla

    def backlight(self, on):
        self._bl = _BL if on else 0
        self._expander(0)

    def display(self, on):
        self.command(_DISPLAY_ON if on else _DISPLAY_OFF)
