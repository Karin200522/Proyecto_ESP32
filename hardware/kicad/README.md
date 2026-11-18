# Esquemático KiCad — PENDIENTE

Esta carpeta guardará el proyecto de KiCad 10 (`Pino_Navidad.kicad_pro`, `.kicad_sch`, …),
que se generará con la habilidad **kicad-electronica** cuando el puente con la PC esté disponible.

Mientras tanto, la referencia de cableado completa está en [`../CONEXIONES.md`](../CONEXIONES.md)
y la lista de materiales en [`../BOM.csv`](../BOM.csv).

## Qué debe incluir el esquemático
- Hoja 1 — Alimentación: J1 (4.5 V), C1 1000 µF, C2 100 nF, rieles +4.5 V / 3V3 / GND.
- Hoja 2 — ESP32 (U1) con las etiquetas de red: `LED_AM`, `LED_RO`, `LED_VE`, `BUZZ`, `SDA`, `SCL`, `LDR`.
- Hoja 3 — Etapas de potencia: Q1–Q3 (2N2222A, 330 Ω / 10 kΩ) con las 12 ramas LED+R por canal; Q4 + D1 + R 47 Ω del buzzer.
- Hoja 4 — Interfaces: divisor LDR (GL5528 + 10 kΩ + 100 nF), convertidor BSS138 y conector de la LCD I2C.
