# ble_uart.py — Periférico BLE con el servicio Nordic UART (NUS).
#
# nRF Connect reconoce este servicio como "Nordic UART Service":
#   Servicio  6E400001-B5A3-F393-E0A9-E50E24DCCA9E
#   RX        6E400002-…  (el celular ESCRIBE aquí los comandos)
#   TX        6E400003-…  (el ESP32 NOTIFICA aquí las respuestas)
#
# El manejador de interrupciones (IRQ) solo encola el texto recibido; los
# comandos se procesan en el bucle principal. Así nunca se bloquea la pila BLE.

import struct

import bluetooth
from micropython import const

try:
    import asyncio
except ImportError:
    import uasyncio as asyncio

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_MTU_EXCHANGED = const(21)

_FLAG_READ = const(0x0002)
_FLAG_WRITE_NO_RESPONSE = const(0x0004)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)

_ADV_TYPE_FLAGS = const(0x01)
_ADV_TYPE_NAME = const(0x09)
_ADV_TYPE_UUID128_COMPLETE = const(0x07)
_ADV_MAX = const(31)

_UART_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
_UART_TX = (bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E"),
            _FLAG_READ | _FLAG_NOTIFY)
_UART_RX = (bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E"),
            _FLAG_WRITE | _FLAG_WRITE_NO_RESPONSE)
_UART_SERVICE = (_UART_UUID, (_UART_TX, _UART_RX))


def _adv_field(adv_type, value):
    return struct.pack("BB", len(value) + 1, adv_type) + value


class BLEUart:
    def __init__(self, name, adv_interval_ms=500, rx_buffer=128, max_queue=8):
        self._ble = bluetooth.BLE()
        self._ble.active(True)
        try:
            self._ble.config(gap_name=name)
            self._ble.config(mtu=185)      # permite respuestas más largas
        except Exception:
            pass
        self._ble.irq(self._irq)
        ((self._tx, self._rx),) = self._ble.gatts_register_services((_UART_SERVICE,))
        # append=True: varias escrituras rápidas se acumulan sin perderse
        self._ble.gatts_set_buffer(self._rx, rx_buffer, True)

        self._conns = {}            # conn_handle -> MTU negociado
        self._queue = []
        self._max_queue = max_queue
        self._interval_us = adv_interval_ms * 1000

        # El nombre va en el anuncio; el UUID de 128 bits, en la respuesta al
        # escaneo (los dos juntos no caben en los 31 bytes de un anuncio).
        self._adv = (_adv_field(_ADV_TYPE_FLAGS, b"\x06")
                     + _adv_field(_ADV_TYPE_NAME, name.encode()))
        self._resp = _adv_field(_ADV_TYPE_UUID128_COMPLETE, bytes(_UART_UUID))
        if len(self._adv) > _ADV_MAX:
            raise ValueError("BLE_NAME demasiado largo")
        self.advertise()

    # ------------------------------------------------------------ eventos
    def _irq(self, event, data):
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            self._conns[conn_handle] = 23   # MTU por defecto
            print("[BLE] conectado")
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            self._conns.pop(conn_handle, None)
            print("[BLE] desconectado")
            self.advertise()
        elif event == _IRQ_GATTS_WRITE:
            conn_handle, value_handle = data
            if value_handle == self._rx:
                self._enqueue(self._ble.gatts_read(self._rx))
        elif event == _IRQ_MTU_EXCHANGED:
            conn_handle, mtu = data
            if conn_handle in self._conns:
                self._conns[conn_handle] = mtu

    def _enqueue(self, raw):
        try:
            text = bytes(raw).decode()
        except Exception:      # bytes que no son UTF-8 válido
            return
        # Un comando por escritura; también se aceptan varios separados
        # por salto de línea o ';'
        for part in text.replace("\r", "\n").replace(";", "\n").split("\n"):
            part = part.strip()
            if part and len(self._queue) < self._max_queue:
                self._queue.append(part)

    # ------------------------------------------------------------ API
    @property
    def connected(self):
        return len(self._conns) > 0

    def advertise(self, interval_ms=None):
        """(Re)inicia el anuncio. Si hay un celular conectado, no hace nada."""
        if interval_ms is not None:
            self._interval_us = interval_ms * 1000
        if self._conns:
            return
        try:
            self._ble.gap_advertise(self._interval_us, adv_data=self._adv,
                                    resp_data=self._resp, connectable=True)
            print("[BLE] anunciando cada {} ms".format(self._interval_us // 1000))
        except OSError as e:
            print("[BLE] error al anunciar:", e)

    def get_command(self):
        """Devuelve el siguiente comando recibido (str) o None."""
        if self._queue:
            return self._queue.pop(0)
        return None

    async def send(self, text):
        """Envía texto por notificaciones, en trozos del tamaño del MTU."""
        data = text.encode() if isinstance(text, str) else bytes(text)
        for conn, mtu in list(self._conns.items()):
            step = max(20, mtu - 3)
            for i in range(0, len(data), step):
                chunk = data[i:i + step]
                for _ in range(3):      # reintenta si la pila está ocupada
                    try:
                        self._ble.gatts_notify(conn, self._tx, chunk)
                        break
                    except OSError:
                        await asyncio.sleep_ms(30)
                await asyncio.sleep_ms(10)

    def deinit(self):
        try:
            self._ble.gap_advertise(None)
            self._ble.active(False)
        except Exception:
            pass
