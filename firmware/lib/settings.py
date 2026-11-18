# settings.py — Ajustes persistentes en un archivo JSON de la flash.
#
# Robustez:
# - Si el archivo no existe o está dañado, se usan los valores por defecto.
# - Cada valor se valida (tipo y rango) antes de aceptarse.
# - Se escribe en un archivo temporal y luego se renombra: un corte de luz
#   a la mitad no deja el JSON corrupto.
# - Se guarda unos segundos después del último cambio, así mover el brillo
#   varias veces seguidas no desgasta la flash.

import json
import os

try:
    from time import ticks_diff, ticks_ms
except ImportError:  # CPython (pruebas en la PC)
    import time as _time

    def ticks_ms():
        return int(_time.monotonic() * 1000)

    def ticks_diff(a, b):
        return a - b


class Settings:
    def __init__(self, path, defaults, validator=None):
        self._path = path
        self._defaults = dict(defaults)
        self._data = dict(defaults)
        self._validator = validator
        self._changed_at = None
        self.load()

    def _is_valid(self, key, value):
        if key not in self._defaults:
            return False
        default = self._defaults[key]
        # mismo tipo que el valor por defecto (True no cuenta como int)
        if isinstance(default, bool):
            if not isinstance(value, bool):
                return False
        elif isinstance(default, int):
            if isinstance(value, bool) or not isinstance(value, int):
                return False
        elif isinstance(default, str):
            if not isinstance(value, str):
                return False
        return self._validator is None or bool(self._validator(key, value))

    def load(self):
        try:
            with open(self._path) as f:
                stored = json.load(f)
        except (OSError, ValueError):
            return False
        if not isinstance(stored, dict):
            return False
        for key, value in stored.items():
            if self._is_valid(key, value):
                self._data[key] = value
        return True

    def get(self, key):
        return self._data[key]

    def set(self, key, value):
        """Cambia un valor. Lanza ValueError si no es válido."""
        if not self._is_valid(key, value):
            raise ValueError(key)
        if self._data[key] != value:
            self._data[key] = value
            self._changed_at = ticks_ms()

    def reset_key(self, key):
        self.set(key, self._defaults[key])

    @property
    def dirty(self):
        return self._changed_at is not None

    def save_if_due(self, delay_ms):
        if self._changed_at is not None and \
                ticks_diff(ticks_ms(), self._changed_at) >= delay_ms:
            return self.save()
        return False

    def save(self):
        tmp = self._path + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump(self._data, f)
            try:
                os.rename(tmp, self._path)
            except OSError:
                # FAT no reemplaza un archivo existente al renombrar
                os.remove(self._path)
                os.rename(tmp, self._path)
            self._changed_at = None
            print("[AJUSTES] guardados")
            return True
        except OSError as e:
            print("[AJUSTES] no se pudo guardar:", e)
            return False
