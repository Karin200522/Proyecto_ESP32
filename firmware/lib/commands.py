# commands.py — Interpretación de comandos de texto (BLE y consola USB).
#
# Los comandos no distinguen mayúsculas ni acentos: "música 2" == "MUSICA 2".
# parse() solo traduce el texto a (acción, argumentos); la acción la ejecuta
# app.py en el método _cmd_<accion>.

_ACCENTS = (
    ("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ü", "u"),
    ("ñ", "n"), ("Á", "A"), ("É", "E"), ("Í", "I"), ("Ó", "O"), ("Ú", "U"),
    ("Ü", "U"), ("Ñ", "N"),
)

# palabra -> acción
ACTIONS = {
    "AYUDA": "help", "HELP": "help", "?": "help", "COMANDOS": "help",
    "MODO": "mode", "MODE": "mode",
    "SIG": "next", "SIGUIENTE": "next", "NEXT": "next",
    "ON": "on", "ENCENDER": "on", "PRENDER": "on",
    "OFF": "off", "APAGAR": "off",
    "AUTO": "auto", "AUTOMATICO": "auto",
    "MUSICA": "play", "PLAY": "play", "TOCAR": "play", "VILLANCICO": "play",
    "STOP": "stop", "SILENCIO": "stop", "PARAR": "stop",
    "VOL": "volume", "VOLUMEN": "volume",
    "BRILLO": "bright", "BRIGHT": "bright",
    "VEL": "speed", "VELOCIDAD": "speed", "SPEED": "speed",
    "AUTOMUSICA": "automusic",
    "LUZ": "light", "LDR": "light",
    "UMBRAL": "threshold", "UMBRALES": "threshold",
    "ESTADO": "status", "STATUS": "status", "INFO": "status",
    "REINICIAR": "reboot", "RESET": "reboot",
}

HELP = (
    "COMANDOS:\n"
    "MODO n|nombre  SIG\n"
    "ON  OFF  AUTO (sensor de luz)\n"
    "MUSICA [1-3]  STOP\n"
    "VOL 0-100  BRILLO 10-100  VEL 1-5\n"
    "AUTOMUSICA SI|NO\n"
    "LUZ  UMBRAL oscuro claro\n"
    "ESTADO  REINICIAR\n"
    "MODOS: 1 Fijo 2 Alterno 3 Cascada 4 Respira 5 Latido "
    "6 Onda 7 Destello 8 Persecucion 9 Demo\n"
    "MELODIAS: 1 Jingle Bells 2 We Wish You 3 Noche de Paz"
)

YES = ("SI", "ON", "1", "YES", "S")
NO = ("NO", "OFF", "0", "N")


def normalize(text):
    for accented, plain in _ACCENTS:
        text = text.replace(accented, plain)
    return text.strip().upper()


def parse(text):
    """'modo 3' -> ('mode', ['3'])
       'cascada' / '3' -> ('mode_direct', ['CASCADA']) (atajo para el modo)
       '' -> (None, [])"""
    words = normalize(text).split()
    if not words:
        return (None, [])
    action = ACTIONS.get(words[0])
    if action is not None:
        return (action, words[1:])
    return ("mode_direct", words)


def parse_bool(word):
    if word in YES:
        return True
    if word in NO:
        return False
    raise ValueError(word)
