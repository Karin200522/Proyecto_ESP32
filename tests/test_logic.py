"""Pruebas de la lógica pura del firmware, en la PC (CPython 3).

Ejecutar desde la raíz del repositorio:
    python -m unittest discover -s tests -v
No necesitan el ESP32: solo prueban los módulos que no tocan hardware.
"""
import json
import os
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "firmware" / "lib"))

import animations  # noqa: E402
import commands  # noqa: E402
from light_sensor import DarkDetector  # noqa: E402
from melodies import MELODIES, note_freq  # noqa: E402
from settings import Settings  # noqa: E402


class TestMelodies(unittest.TestCase):
    def test_note_freq(self):
        self.assertEqual(note_freq("A4"), 440)
        self.assertEqual(note_freq("A5"), 880)
        self.assertEqual(note_freq("C5"), 523)
        self.assertEqual(note_freq("F#5"), 740)
        self.assertEqual(note_freq("Bb4"), 466)
        self.assertEqual(note_freq("R"), 0)
        with self.assertRaises(ValueError):
            note_freq("H4")
        with self.assertRaises(ValueError):
            note_freq("C")

    def test_melodies_are_valid(self):
        self.assertEqual(len(MELODIES), 3)
        for m in MELODIES:
            beat_ms = 60000 / m["tempo"]
            total = 0
            for note, beats in m["notas"]:
                f = note_freq(note)
                self.assertTrue(f == 0 or 400 <= f <= 2000, (m["nombre"], note, f))
                self.assertGreater(beats, 0)
                total += beats * beat_ms
            self.assertLess(total, 60000, m["nombre"])  # menos de 1 minuto


class TestAnimations(unittest.TestCase):
    def test_all_modes_return_valid_levels(self):
        modes = animations.build_modes()
        self.assertEqual(len(modes), 9)
        for m in modes:
            m.reset()
            for t in range(0, 200000, 37):
                levels = m.frame(t)
                self.assertEqual(len(levels), 3, m.name)
                for v in levels:
                    self.assertIsInstance(v, int, m.name)
                    self.assertTrue(0 <= v <= 255, (m.name, t, levels))

    def test_periods_divide_wrap(self):
        w = animations.WRAP_MS
        self.assertEqual(w % (animations.Alternate.HALF * 2), 0)
        self.assertEqual(w % animations.Cascade.PERIOD, 0)
        self.assertEqual(w % animations.Breathe.PERIOD, 0)
        self.assertEqual(w % animations.Heartbeat.PERIOD, 0)
        self.assertEqual(w % animations.Wave.PERIOD, 0)
        self.assertEqual(w % (animations.Chase.STEP * 3), 0)
        self.assertEqual(w % (animations.Demo.SLOT * 8), 0)

    def test_twinkle_survives_wrap(self):
        tw = animations.Twinkle()
        for t in range(0, 5000, 20):
            tw.frame(t)
        for t in range(0, 2000, 20):  # el reloj volvió a 0
            for v in tw.frame(t):
                self.assertTrue(0 <= v <= 255)

    def test_labels_fit_lcd(self):
        for m in animations.build_modes():
            self.assertLessEqual(len(m.label), 12)
            self.assertTrue(all(ord(c) < 128 for c in m.label))

    def test_find_mode(self):
        modes = animations.build_modes()
        f = animations.find_mode
        self.assertEqual(f(modes, 1).name, "fijo")
        self.assertEqual(f(modes, "3").name, "cascada")
        self.assertEqual(f(modes, "CASCADA").name, "cascada")
        self.assertEqual(f(modes, "palpitacion").name, "latido")
        self.assertEqual(f(modes, "pers").name, "persecucion")
        self.assertEqual(f(modes, "9").name, "demo")
        self.assertIsNone(f(modes, "0"))
        self.assertIsNone(f(modes, "10"))
        self.assertIsNone(f(modes, "xx"))
        self.assertIsNone(f(modes, ""))
        self.assertIsNone(f(modes, None))


class TestDarkDetector(unittest.TestCase):
    def test_initial_decision(self):
        d = DarkDetector(25, 45, 5000)
        self.assertTrue(d.update(10, 0))
        self.assertTrue(d.is_dark)
        d2 = DarkDetector(25, 45, 5000)
        d2.update(80, 0)
        self.assertFalse(d2.is_dark)

    def test_hysteresis_and_confirmation(self):
        d = DarkDetector(25, 45, 5000)
        d.update(80, 0)                     # claro
        self.assertFalse(d.update(35, 1000))  # zona intermedia: sin cambio
        self.assertFalse(d.update(20, 2000))  # empieza a contar
        self.assertFalse(d.update(20, 6000))  # 4 s: todavía no
        self.assertTrue(d.update(20, 7000))   # 5 s: cambia a oscuro
        self.assertTrue(d.is_dark)
        # la luz de los LEDs sube la lectura a 40 %: debajo de 45, sigue oscuro
        for t in range(8000, 30000, 500):
            self.assertFalse(d.update(40, t))
        self.assertTrue(d.is_dark)

    def test_brief_flash_is_ignored(self):
        d = DarkDetector(25, 45, 5000)
        d.update(10, 0)                      # oscuro
        d.update(90, 1000)                   # alguien enciende una lámpara...
        d.update(90, 3000)
        d.update(10, 4000)                   # ...y la apaga antes de 5 s
        self.assertFalse(d.update(90, 9000))  # el conteo se reinició
        self.assertTrue(d.is_dark)

    def test_invalid_thresholds(self):
        with self.assertRaises(ValueError):
            DarkDetector(50, 40, 1000)
        d = DarkDetector(25, 45, 1000)
        with self.assertRaises(ValueError):
            d.set_thresholds(30, 30)


class TestCommands(unittest.TestCase):
    def test_parse(self):
        p = commands.parse
        self.assertEqual(p("modo 3"), ("mode", ["3"]))
        self.assertEqual(p("  Música 2 "), ("play", ["2"]))
        self.assertEqual(p("MÚSICA"), ("play", []))
        self.assertEqual(p("umbral 20 40"), ("threshold", ["20", "40"]))
        self.assertEqual(p("cascada"), ("mode_direct", ["CASCADA"]))
        self.assertEqual(p("palpitación"), ("mode_direct", ["PALPITACION"]))
        self.assertEqual(p("?"), ("help", []))
        self.assertEqual(p(""), (None, []))

    def test_parse_bool(self):
        self.assertTrue(commands.parse_bool("SI"))
        self.assertFalse(commands.parse_bool("NO"))
        with self.assertRaises(ValueError):
            commands.parse_bool("TAL VEZ")


class TestSettings(unittest.TestCase):
    DEFAULTS = {"modo": "demo", "brillo": 80, "auto_musica": True}

    def _validator(self, key, value):
        return not (key == "brillo" and not 10 <= value <= 100)

    def test_missing_and_corrupt_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "s.json")
            s = Settings(path, self.DEFAULTS, self._validator)
            self.assertEqual(s.get("brillo"), 80)
            with open(path, "w") as f:
                f.write("{esto no es json")
            s = Settings(path, self.DEFAULTS, self._validator)
            self.assertEqual(s.get("modo"), "demo")

    def test_validation_and_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "s.json")
            s = Settings(path, self.DEFAULTS, self._validator)
            with self.assertRaises(ValueError):
                s.set("brillo", 150)
            with self.assertRaises(ValueError):
                s.set("brillo", True)        # bool no es un int válido
            with self.assertRaises(ValueError):
                s.set("auto_musica", 1)
            with self.assertRaises(ValueError):
                s.set("inexistente", 1)
            s.set("brillo", 55)
            self.assertTrue(s.dirty)
            self.assertTrue(s.save())
            self.assertFalse(s.dirty)
            self.assertFalse(os.path.exists(path + ".tmp"))
            s2 = Settings(path, self.DEFAULTS, self._validator)
            self.assertEqual(s2.get("brillo"), 55)

    def test_ignores_bad_values_in_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "s.json")
            with open(path, "w") as f:
                json.dump({"brillo": 999, "modo": "fijo", "extra": 1}, f)
            s = Settings(path, self.DEFAULTS, self._validator)
            self.assertEqual(s.get("brillo"), 80)
            self.assertEqual(s.get("modo"), "fijo")


if __name__ == "__main__":
    unittest.main()
