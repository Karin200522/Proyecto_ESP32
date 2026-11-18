# Control por Bluetooth (BLE) con nRF Connect

El ESP32 se anuncia como **`PinoNavidad`** con el servicio **Nordic UART (NUS)**.
No requiere emparejamiento ni PIN.

## Conectarse desde el celular

1. Instala **nRF Connect for Mobile** (Nordic Semiconductor) en Android o iOS.
2. Pestaña **SCANNER** → **SCAN** → busca `PinoNavidad` → **CONNECT**.
3. Abre el servicio **Nordic UART Service** (`6E400001-…`).
4. En **TX Characteristic** (`6E400003-…`), toca el ícono de **notificaciones** (las tres flechas hacia abajo).
   Ahí aparecerán las respuestas del árbol.
5. En **RX Characteristic** (`6E400002-…`), toca la **flecha hacia arriba** (escribir):
   - En Android elige el formato **TEXT (UTF-8)**. En iOS, **UTF8**.
   - Escribe el comando, por ejemplo `MODO 3`, y toca **SEND**.
6. *(Opcional, Android)* Menú ⋮ → **Request MTU** → 185. Así las respuestas largas llegan en menos trozos.

> **Tip:** en Android puedes guardar comandos frecuentes en las *macros* de nRF Connect,
> o usar la app **nRF Toolbox → UART**, que trae botones configurables.

Los comandos **no distinguen mayúsculas ni acentos**. Puedes mandar varios en una sola escritura
separándolos con `;`, por ejemplo `MODO 5; BRILLO 60`. Los mismos comandos funcionan escribiéndolos
en la consola de Thonny con el ESP32 conectado por USB.

## Lista de comandos

| Comando | Qué hace | Ejemplo |
|---|---|---|
| `AYUDA` o `?` | Lista de comandos | `AYUDA` |
| `MODO n` / `MODO nombre` | Cambia la animación | `MODO 3`, `MODO latido` |
| `n` o `nombre` (solo) | Atajo para cambiar de modo | `5`, `cascada` |
| `SIG` | Pasa al siguiente modo | `SIG` |
| `ON` | Fuerza el encendido (ignora la LDR) | `ON` |
| `OFF` | Fuerza el apagado (ignora la LDR) | `OFF` |
| `AUTO` | Vuelve al control por luz (LDR) | `AUTO` |
| `MUSICA [1-3]` | Toca un villancico | `MUSICA 3` |
| `STOP` | Detiene la música | `STOP` |
| `VOL 0-100` | Volumen del buzzer | `VOL 40` |
| `BRILLO 10-100` | Brillo general de los LEDs | `BRILLO 70` |
| `VEL 1-5` | Velocidad de la animación | `VEL 4` |
| `AUTOMUSICA SI/NO` | Tocar música al encenderse el árbol | `AUTOMUSICA NO` |
| `LUZ` | Lectura actual de la LDR y umbrales | `LUZ` |
| `UMBRAL osc claro` | Ajusta los umbrales de la LDR (%) | `UMBRAL 20 40` |
| `ESTADO` | Resumen completo del sistema | `ESTADO` |
| `REINICIAR` | Reinicia el ESP32 | `REINICIAR` |

Los cambios de modo, brillo, velocidad, volumen, melodía, música automática y umbrales
**se guardan en la flash** (`settings.json`) y se conservan al apagar el árbol.
`ON`, `OFF` y `AUTO` no se guardan: el árbol siempre arranca en `AUTO`.

## Modos de animación

| # | Nombre | Descripción |
|---|---|---|
| 1 | `fijo` | Todos los LEDs encendidos |
| 2 | `alterno` | Parpadeo alterno: amarillo + verde ↔ rojo |
| 3 | `cascada` | Los colores se encienden uno tras otro y se apagan en el mismo orden |
| 4 | `respira` | Respiración suave de todo el árbol |
| 5 | `latido` | Palpitación de doble pulso ("lub-dub"); el rojo late más fuerte |
| 6 | `onda` | Onda senoidal desfasada 120° entre los tres colores |
| 7 | `destello` | Destellos aleatorios |
| 8 | `persecucion` | Un color a la vez, rápido |
| 9 | `demo` | Recorre todos los modos, 12 s cada uno (modo por defecto) |

## Melodías

| # | Melodía |
|---|---|
| 1 | Jingle Bells |
| 2 | We Wish You a Merry Christmas |
| 3 | Noche de Paz |

## Calibrar el sensor de luz

1. Con la habitación **iluminada** como de costumbre, envía `LUZ` y anota el %. Por ejemplo, 75 %.
2. Apaga la luz, envía `ON` para encender el árbol y luego `LUZ`. Ese valor (por ejemplo, 18 %)
   ya incluye la luz que los propios LEDs le dan a la LDR.
3. Elige el umbral **claro** entre ambos valores, con margen sobre el segundo. Elige el **oscuro** por debajo del segundo.
   Con los ejemplos: `UMBRAL 15 45`.
4. Envía `AUTO`. El cambio de estado tarda unos 5–8 s en confirmarse; así se ignoran destellos breves.

Si el árbol se enciende y apaga solo en ciclos, la LDR está viendo la luz de los LEDs:
cámbiala de lugar o ponle una visera (ver `hardware/CONEXIONES.md`, sección 4).
