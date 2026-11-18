# melodies.py — Villancicos (dominio público) en notación de notas.
#
# Cada melodía: nombre, tempo (pulsos por minuto) y una tupla de
# (nota, duración_en_pulsos). Notas: "C5", "F#5", "Bb4"...; "R" = silencio.
# Están una octava arriba de lo habitual porque los buzzers pasivos
# pequeños suenan más fuerte y claro entre 500 y 2000 Hz.

_SEMITONES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_cache = {}


def note_freq(note):
    """'A4' -> 440, 'C5' -> 523, 'F#5' -> 740, 'R' -> 0 (silencio). Hz enteros."""
    f = _cache.get(note)
    if f is not None:
        return f
    n = note.strip().upper()
    if n in ("R", "-", ""):
        f = 0
    else:
        if n[0] not in _SEMITONES:
            raise ValueError("nota invalida: " + note)
        semis = _SEMITONES[n[0]]
        rest = n[1:]
        if rest[:1] == "#":
            semis += 1
            rest = rest[1:]
        elif rest[:1] == "B":       # bemol ("Bb4".upper() == "BB4")
            semis -= 1
            rest = rest[1:]
        octave = int(rest)          # ValueError si no es un número
        midi = 12 * (octave + 1) + semis
        f = int(440 * 2 ** ((midi - 69) / 12) + 0.5)
    _cache[note] = f
    return f


MELODIES = (
    {
        "nombre": "Jingle Bells",
        "tempo": 180,   # pulso = negra
        "notas": (
            ("E5", 1), ("E5", 1), ("E5", 2),
            ("E5", 1), ("E5", 1), ("E5", 2),
            ("E5", 1), ("G5", 1), ("C5", 1.5), ("D5", 0.5),
            ("E5", 4),
            ("F5", 1), ("F5", 1), ("F5", 1.5), ("F5", 0.5),
            ("F5", 1), ("E5", 1), ("E5", 1), ("E5", 0.5), ("E5", 0.5),
            ("E5", 1), ("D5", 1), ("D5", 1), ("E5", 1),
            ("D5", 2), ("G5", 2),
            ("E5", 1), ("E5", 1), ("E5", 2),
            ("E5", 1), ("E5", 1), ("E5", 2),
            ("E5", 1), ("G5", 1), ("C5", 1.5), ("D5", 0.5),
            ("E5", 4),
            ("F5", 1), ("F5", 1), ("F5", 1.5), ("F5", 0.5),
            ("F5", 1), ("E5", 1), ("E5", 1), ("E5", 0.5), ("E5", 0.5),
            ("G5", 1), ("G5", 1), ("F5", 1), ("D5", 1),
            ("C5", 4),
        ),
    },
    {
        "nombre": "We Wish You a Merry Christmas",
        "tempo": 170,   # 3/4, pulso = negra
        "notas": (
            ("D5", 1),
            ("G5", 1), ("G5", 0.5), ("A5", 0.5), ("G5", 0.5), ("F#5", 0.5),
            ("E5", 1), ("E5", 1), ("E5", 1),
            ("A5", 1), ("A5", 0.5), ("B5", 0.5), ("A5", 0.5), ("G5", 0.5),
            ("F#5", 1), ("D5", 1), ("D5", 1),
            ("B5", 1), ("B5", 0.5), ("C6", 0.5), ("B5", 0.5), ("A5", 0.5),
            ("G5", 1), ("E5", 1), ("D5", 0.5), ("D5", 0.5),
            ("E5", 1), ("A5", 1), ("F#5", 1),
            ("G5", 3),
        ),
    },
    {
        "nombre": "Noche de Paz",
        "tempo": 200,   # 6/8, pulso = corchea
        "notas": (
            ("G5", 3), ("A5", 1), ("G5", 2), ("E5", 6),
            ("G5", 3), ("A5", 1), ("G5", 2), ("E5", 6),
            ("D6", 4), ("D6", 2), ("B5", 6),
            ("C6", 4), ("C6", 2), ("G5", 6),
            ("A5", 4), ("A5", 2), ("C6", 3), ("B5", 1), ("A5", 2),
            ("G5", 3), ("A5", 1), ("G5", 2), ("E5", 6),
            ("A5", 4), ("A5", 2), ("C6", 3), ("B5", 1), ("A5", 2),
            ("G5", 3), ("A5", 1), ("G5", 2), ("E5", 6),
            ("D6", 4), ("D6", 2), ("F6", 3), ("D6", 1), ("B5", 2),
            ("C6", 6), ("E6", 6),
            ("C6", 3), ("G5", 1), ("E5", 2), ("G5", 3), ("F5", 1), ("D5", 2),
            ("C5", 12),
        ),
    },
)
