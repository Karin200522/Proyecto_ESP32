# Conexiones y cálculos de hardware — Pino de Navidad ESP32

> El esquemático formal en KiCad queda **pendiente** (ver `hardware/kicad/README.md`).
> Este documento es la referencia de cableado para armar el proyecto en protoboard.

---

## 1. Alimentación y presupuesto de corriente

Fuente única de **4.5 V / 1.2 A** que alimenta todo:

```
 Fuente 4.5 V / 1.2 A
   (+) ──┬──────── riel +4.5 V ──┬── VIN (o "5V") del ESP32
         │                       ├── LEDs (a través de su resistencia)
     [C1 1000 µF / 10 V]         ├── VCC de la LCD y lado HV del convertidor de nivel
     [C2 100 nF]                 └── buzzer (a través de R 47 Ω)
         │
   (−) ──┴──────── riel GND ───── GND del ESP32, emisores de Q1–Q4, LCD, LDR, etc.
```

| Carga | Corriente típica | Peor caso |
|---|---|---|
| 36 LEDs a ~15 mA (los 3 canales al 100 %) | 540 mA | 560 mA |
| ESP32 con BLE (sin Wi-Fi) | 80–110 mA | 250 mA (picos de radio) |
| LCD 16x2 con retroiluminación | 25–35 mA | 40 mA |
| Buzzer pasivo (con R 47 Ω) | 20–30 mA | 70 mA |
| LDR + divisor | < 0.5 mA | < 0.5 mA |
| **Total** | **≈ 700 mA** | **≈ 920 mA (77 % de 1.2 A)** |

En reposo (de día) el consumo baja a ~70–90 mA: LEDs, buzzer y retroiluminación apagados; solo el ESP32 sigue anunciando BLE.

### Por qué 4.5 V en VIN funciona (y su límite)
- El pin **VIN** (DevKit de 30 pines) o **5V** (DevKitC de 38 pines) va directo al regulador **AMS1117-3.3** de la placa.
- El AMS1117 necesita ~1.0–1.1 V de caída: 4.5 V − 1.1 V ≈ **3.4 V**, suficiente para que entregue 3.3 V con la corriente del ESP32 en BLE. El margen es justo.
- **No pongas un diodo de protección en serie** con la fuente: sus 0.3–0.7 V de caída dejarían al ESP32 por debajo de 3.0 V. Revisa la polaridad antes de conectar.
- Si llegas a ver reinicios por *brownout* (el mensaje `Brownout detector was triggered` en la consola), sube C1 a 2200 µF, acorta los cables de alimentación o cambia la fuente por una de 5 V. Las resistencias de los LEDs se recalculan en la sección 3.

### ⚠️ USB y fuente externa al mismo tiempo
El riel de 4.5 V está unido a VIN. Si conectas el USB de la PC con la fuente encendida, los 5 V del USB (≈4.7 V tras el diodo de la placa) quedan **más altos** que tu fuente, y el USB terminaría alimentando los 36 LEDs (más de 500 mA, por encima de lo que da un puerto USB).

**Al programar o depurar por USB, desconecta el cable VIN** y deja GND conectado. Así el ESP32 se alimenta del USB y los LEDs de la fuente, con tierra común.

---

## 2. Asignación de pines del ESP32

| GPIO | Función | Conecta a | Notas |
|---|---|---|---|
| **GPIO25** | PWM canal amarillo | R 330 Ω → base de **Q1** | 10 kΩ de base a GND |
| **GPIO26** | PWM canal rojo | R 330 Ω → base de **Q2** | 10 kΩ de base a GND |
| **GPIO27** | PWM canal verde | R 330 Ω → base de **Q3** | 10 kΩ de base a GND |
| **GPIO18** | PWM buzzer | R 1 kΩ → base de **Q4** | 10 kΩ de base a GND |
| **GPIO21** | I2C SDA | LV1 del convertidor de nivel → SDA de la LCD | |
| **GPIO22** | I2C SCL | LV2 del convertidor de nivel → SCL de la LCD | |
| **GPIO34** | ADC1_CH6 (LDR) | Nodo del divisor LDR / 10 kΩ | Solo entrada, sin pull-up interno |
| GPIO0 | Botón BOOT de la placa | (ya está en la placa) | Modo seguro del firmware |
| **3V3** | 3.3 V regulado | LDR, lado LV del convertidor de nivel | Máx. ~500 mA del AMS1117 en total |
| **VIN / 5V** | Entrada 4.5 V | Riel +4.5 V | Desconéctalo cuando uses el USB |
| **GND** | Tierra | Riel GND | Usa 2 cables de GND en paralelo |

Pines que se evitaron a propósito:
- **GPIO 6–11**: memoria flash interna.
- **GPIO 0, 2, 5, 12, 15**: pines de arranque (*strapping*); si algo los fuerza al arrancar, la placa puede no iniciar.
- **ADC2 (GPIO 0, 2, 4, 12–15, 25–27)** para la LDR: por eso la LDR va en ADC1 (GPIO34). Los GPIO25–27 sí sirven como salidas PWM.

---

## 3. Etapa de potencia de los LEDs (Q1, Q2, Q3)

### Por qué hacen falta transistores
12 LEDs × 15 mA = **180 mA por canal**. Un GPIO del ESP32 da como máximo ~40 mA (se recomienda ≤ 20 mA). Por eso cada canal usa un **transistor NPN 2N2222A como interruptor del lado bajo**: el GPIO solo maneja la base (~7 mA) y la corriente de los LEDs sale de la fuente de 4.5 V.

### Esquema de UN canal (se repite 3 veces)

```
            riel +4.5 V
                 │
   ┌─────────────┼─────────────┬──── ··· (12 ramas iguales en paralelo)
   │             │             │
 [Rled]        [Rled]        [Rled]      Rled = 150 Ω (ver tabla)
   │             │             │
   ▼ LED1        ▼ LED2        ▼ LED12   (ánodo arriba, cátodo abajo)
   │             │             │
   └─────────────┴─────────────┴──────┐  "bus de cátodos" del canal
                                      │
                                    C │
 GPIO25 ──[330 Ω]──┬────────────── B ─┤  Q1 = 2N2222A
                   │                E │
                [10 kΩ]               │
                   │                  │
 riel GND ─────────┴──────────────────┴──── riel GND
```

- **Una resistencia por LED**, nunca una sola resistencia para los 12. Los LEDs no son idénticos (su Vf varía) y el que tenga Vf menor se llevaría casi toda la corriente.
- La **10 kΩ base-emisor** mantiene el transistor apagado mientras el ESP32 arranca y sus pines están flotando. Así los LEDs no destellan al encender.
- Identifica las patas del transistor: en **PN2222A / P2N2222A**, con la cara plana hacia ti y las patas hacia abajo, el orden es **E – B – C**. Hay clones con otro orden, así que confírmalo con el datasheet o con la prueba de diodo del multímetro.

### Cálculo de la resistencia de base (330 Ω)

- Corriente de colector: Ic = 12 × 15 mA = 180 mA.
- Para saturar bien un BJT se usa una ganancia forzada β ≈ 10–30. El 2N2222A tiene hFE ≥ 100 a 150 mA, así que con β forzada ≈ 25 queda saturado con margen.
- Ib ≈ (3.3 V − 0.85 V) / 330 Ω ≈ **7.4 mA** → β forzada = 180 / 7.4 ≈ 24 ✔
- Vce(sat) ≈ 0.1–0.25 V a 180 mA → disipación ≈ 0.2 V × 0.18 A ≈ **36 mW** (el TO-92 aguanta 625 mW).
- Con 1 kΩ (Ib ≈ 2.5 mA) el transistor quedaría al borde de la saturación y los LEDs brillarían menos. **No uses 1 kΩ en los canales de LEDs.**

### Cálculo de las resistencias de los LEDs

Fórmula: **R = (Vfuente − Vf − Vce(sat)) / I_LED**, con Vfuente = 4.5 V, Vce(sat) ≈ 0.2 V e I_LED = 15 mA.

| Color | Vf típica | R calculada | **R comercial** | I resultante | Potencia en R |
|---|---|---|---|---|---|
| Rojo | 2.0 V | 153 Ω | **150 Ω** | ≈ 15 mA | 35 mW |
| Amarillo | 2.1 V | 147 Ω | **150 Ω** | ≈ 15 mA | 33 mW |
| Verde clásico (GaP, verde-amarillento, difuso) | 2.2 V | 140 Ω | **150 Ω** | ≈ 14 mA | 30 mW |
| Verde brillante (InGaN, "verde puro" o alto brillo) | 3.0–3.2 V | 80 Ω | **82 Ω** | ≈ 13–16 mA | 20 mW |

Basta con resistencias de 1/4 W.

**Antes de comprar las del canal verde, mide la Vf de tus LEDs verdes.** Usa la prueba de diodo del multímetro, o conecta un LED con 220 Ω a 4.5 V y mide el voltaje en sus patas:
- ≈ 2 V → usa 150 Ω.
- ≈ 3 V → usa 82 Ω. Con 150 Ω quedarían muy tenues, a ~8 mA.

Si algún día cambias a una fuente de **5 V**: rojo y amarillo 180 Ω, verde GaP 180 Ω, verde InGaN 120 Ω.

### Alternativas de transistor
| Opción | ¿Sirve con 4.5 V? | Comentario |
|---|---|---|
| **2N2222A / PN2222A** (elegido) | ✔ | Barato, cabe en protoboard y cae solo 0.1–0.25 V |
| MOSFET logic-level (IRLZ44N, IRLB8721) | ✔ | Cambia la R de base por 100 Ω en la compuerta y 100 kΩ compuerta-GND. Casi no cae voltaje |
| TIP120 (Darlington) | ✘ No recomendado | Su Vce(sat) es de 0.7–1.5 V. Con 4.5 V solo quedaría ~1–1.5 V para la resistencia y el brillo variaría mucho de LED a LED |
| 2N7000 / BS170 | ✘ | Con 3.3 V en la compuerta su Rds(on) es de varios ohms y caerían más de 1 V a 180 mA |

---

## 4. Sensor de luz (LDR) — divisor de voltaje

```
 3V3 ──[ LDR GL5528 ]──┬──────── GPIO34 (ADC1_CH6)
                       │
                 ┌─────┴─────┐
              [10 kΩ]     [100 nF]   ← filtro contra ruido del PWM
                 │           │
 GND ────────────┴───────────┘
```

- **Más luz → menor resistencia de la LDR → mayor voltaje → mayor %.** El firmware considera "oscuro" un valor bajo.
- GL5528 típica: ~1–3 kΩ con la habitación iluminada (≈ 2.5–2.9 V, 75–90 %) y 30–100 kΩ con la luz apagada (≈ 0.3–0.8 V, 10–25 %).
- Umbrales por defecto: **oscuro < 25 %** y **claro > 45 %**, con 5 s de confirmación. Ajústalos por BLE (`LUZ`, `UMBRAL`).
- Si conectas la LDR al revés (LDR a GND y 10 kΩ a 3V3), pon `LDR_INVERT = True` en `config.py`.
- **Muy importante:** la LDR **no debe ver la luz del propio árbol**. Si la ve, el árbol se enciende, "ve luz" y se apaga solo. Apunta la LDR hacia la ventana o el techo, lejos de los LEDs. Puedes ponerle un tubito negro o termofit como visera. La histéresis del firmware ayuda, pero no sustituye una buena ubicación.

---

## 5. Buzzer pasivo (Q4)

```
 riel +4.5 V ──[47 Ω]──┬──────────────┐
                       │              │
                  (+) BZ1          ──┴── D1 1N4148
                  (−)  │             ▲   (cátodo/franja hacia +4.5 V)
                       ├─────────────┘
                       │ C
 GPIO18 ──[1 kΩ]──┬─── B   Q4 = 2N2222A
                  │      E
               [10 kΩ]   │
                  │      │
 riel GND ────────┴──────┴──── riel GND
```

- El buzzer pasivo **magnético** (el común de 12 mm) es una bobina de ~16 Ω. Conectado directo al GPIO pediría más de 100 mA, así que se maneja con un transistor.
- **D1 (1N4148 o 1N4001)** absorbe el pico de voltaje inverso de la bobina al apagarse. La franja (cátodo) va hacia +4.5 V.
- **R 47 Ω** limita la corriente y el volumen. Si quieres más volumen, bájala a 22 Ω o quítala. El volumen también se controla por software (`VOL 0–100`).
- Si tu buzzer es **piezoeléctrico** (disco cerámico), agrega 1 kΩ **en paralelo** al buzzer para que se descargue cuando el transistor se apaga. Sin esa resistencia suena débil.
- Las notas se generan cambiando la frecuencia del PWM (≈ 520–1400 Hz) con ciclo de trabajo de hasta el 50 %.

---

## 6. Pantalla LCD 16x2 con módulo I2C (PCF8574)

La LCD (controlador HD44780) necesita ~4.5–5 V para tener buen contraste, por eso se alimenta con **4.5 V**. Pero el ESP32 trabaja a 3.3 V y **sus pines no toleran 4.5 V**. El módulo PCF8574 suele traer resistencias *pull-up* de 4.7 kΩ hacia su VCC, y con ellas SDA y SCL quedarían a 4.5 V.

### Opción A (recomendada): convertidor de nivel bidireccional BSS138

```
                 Convertidor de nivel (4 canales, BSS138)
 ESP32 3V3 ─────── LV            HV ─────── riel +4.5 V
 GND ───────────── GND          GND ─────── GND
 GPIO21 ────────── LV1          HV1 ─────── SDA de la LCD
 GPIO22 ────────── LV2          HV2 ─────── SCL de la LCD

 LCD:  VCC → riel +4.5 V      GND → riel GND
```

### Opción B (sin convertidor): pull-ups a 3.3 V
1. Con el módulo **desconectado**, mide la resistencia entre SDA y VCC del PCF8574. Si marca ~4.7 kΩ (o 10 kΩ), el módulo trae pull-ups. Desuelda esas dos resistencias SMD (las que van a SDA y SCL).
2. Coloca **4.7 kΩ de SDA a 3V3** y **4.7 kΩ de SCL a 3V3** del ESP32.
3. Conecta SDA → GPIO21 y SCL → GPIO22 directo.

Funciona porque el PCF8574 reconoce un "1" lógico a partir de 0.7 × VCC = 0.7 × 4.5 V = 3.15 V, y 3.3 V supera ese valor. Mucha gente conecta el módulo directo sin hacer nada y "funciona", pero queda fuera de especificación y con el tiempo puede dañar los pines del ESP32.

### Notas de la LCD
- Dirección I2C: el firmware la **detecta sola** (0x27 o 0x3F son las más comunes). Para fijarla, usa `LCD_ADDR` en `config.py`.
- Si la pantalla enciende pero no se ven letras, gira el **potenciómetro azul de contraste** del módulo. A 4.5 V el punto óptimo cambia respecto a 5 V.
- El texto solo puede usar ASCII: la ROM de la LCD no tiene acentos ni "ñ". Por eso el firmware muestra "Persecucion" sin acento.

---

## 7. Lista de materiales (BOM)

Ver también `hardware/BOM.csv`.

| Cant. | Componente | Valor / Modelo | Uso |
|---|---|---|---|
| 1 | Placa ESP32 | DevKit V1 (30 pines) o DevKitC (38 pines) | Controlador |
| 12 | LED 5 mm | Amarillo | Canal 1 |
| 12 | LED 5 mm | Rojo | Canal 2 |
| 12 | LED 5 mm | Verde | Canal 3 |
| 24 | Resistencia 1/4 W | 150 Ω | Amarillo y rojo |
| 12 | Resistencia 1/4 W | 150 Ω (verde GaP) **o** 82 Ω (verde InGaN) | Verde |
| 4 | Transistor NPN | 2N2222A / PN2222A (TO-92) | Q1–Q3 LEDs, Q4 buzzer |
| 3 | Resistencia 1/4 W | 330 Ω | Base de Q1–Q3 |
| 1 | Resistencia 1/4 W | 1 kΩ | Base de Q4 |
| 5 | Resistencia 1/4 W | 10 kΩ | 4 pull-down de base + 1 del divisor LDR |
| 1 | Resistencia 1/4 W | 47 Ω | Serie con el buzzer (opcional) |
| 1 | Diodo | 1N4148 (o 1N4001) | Protección del buzzer |
| 1 | Fotorresistencia | GL5528 | Sensor de luz |
| 1 | Buzzer pasivo | 12 mm, 3–5 V | Audio |
| 1 | LCD 16x2 + módulo I2C | HD44780 + PCF8574 | Pantalla |
| 1 | Convertidor de nivel | BSS138 de 4 canales | I2C 3.3 V ↔ 4.5 V (opción A) |
| 2 | Resistencia 1/4 W | 4.7 kΩ | Solo para la opción B |
| 1 | Capacitor electrolítico | 1000 µF / 10 V (mínimo 470 µF) | Reserva de la fuente |
| 3 | Capacitor cerámico | 100 nF | Desacoplo de VIN y LCD, filtro de la LDR |
| 1 | Fuente | 4.5 V / 1.2 A + jack o bornera | Alimentación |
| 1–2 | Protoboard + cables | — | Montaje |

---

## 8. Orden de montaje y pruebas (recomendado)

1. **Rieles**: fuente → rieles +4.5 V y GND, con C1 y C2. Mide 4.5 V con el multímetro **antes** de conectar nada más.
2. **ESP32 solo** (por USB, con VIN desconectado): carga el firmware y comprueba que la consola diga `[LCD] no disponible` y `[BLE] anunciando`.
3. **Un canal de LEDs** (amarillo, Q1): conecta 2–3 LEDs, envía `ON` y `MODO 1`. Si funcionan, completa los 12.
4. Repite con los canales rojo y verde.
5. **Buzzer** (Q4, D1): envía `MUSICA 1`.
6. **LCD** con el convertidor de nivel: reinicia y debe aparecer "Feliz Navidad".
7. **LDR**: envía `LUZ` con la habitación iluminada y luego a oscuras. Ajusta con `UMBRAL` y finalmente envía `AUTO`.
8. Ya con todo armado, alimenta solo con la fuente (VIN conectado, USB desconectado).

Consejos para protoboard:
- Los 540 mA de los LEDs regresan por los emisores. Lleva **dos cables de GND** desde el riel hasta el ESP32 y pon los transistores cerca de la entrada de la fuente.
- Usa cables cortos para SDA y SCL (< 20 cm), lejos de los cables de los LEDs.
- Separa los colores de cable: rojo +4.5 V, naranja 3V3, negro GND, otro color para señales.
