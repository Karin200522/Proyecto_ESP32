# Stub de `bluetooth` para simular el firmware en MicroPython (puerto unix).
# Permite simular un celular: conectar, escribir comandos y leer respuestas.


def UUID(text):
    # En el ESP32 es un objeto; aquí basta con sus 16 bytes little-endian.
    h = text.replace("-", "")
    return bytes(reversed(bytes.fromhex(h)))


class BLE:
    instance = None

    def __init__(self):
        BLE.instance = self
        self._irq = None
        self._rx = b""
        self.notified = []
        self.adv = None

    def active(self, v=None):
        return True

    def config(self, *args, **kwargs):
        pass

    def irq(self, handler):
        self._irq = handler

    def gatts_register_services(self, services):
        return ((10, 11),)          # (TX, RX)

    def gatts_set_buffer(self, handle, size, append=False):
        pass

    def gap_advertise(self, interval_us, adv_data=None, resp_data=None, connectable=True):
        self.adv = (interval_us, adv_data, resp_data)

    def gatts_read(self, handle):
        data, self._rx = self._rx, b""
        return data

    def gatts_notify(self, conn, handle, data):
        self.notified.append(bytes(data))

    # ---- ayudas de simulación
    def sim_connect(self, mtu=None):
        self._irq(1, (0, 0, b"\x00" * 6))
        if mtu:
            self._irq(21, (0, mtu))

    def sim_disconnect(self):
        self._irq(2, (0, 0, b"\x00" * 6))

    def sim_write(self, text):
        self._rx += text.encode()
        self._irq(3, (0, 11))

    def take_replies(self):
        text = b"".join(self.notified).decode()
        self.notified = []
        return text
