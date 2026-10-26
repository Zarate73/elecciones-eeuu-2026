# Backtest Ohio (general)

- **`backtest_ohio.py`** corre las variantes y escribe `salida/` (`consola.txt` tiene el resumen):
  - leave-one-year-out, H = 8 (corte 26-oct) y ventana de producción de 8 a 21 días;
  - 957 contiendas (1998–2024), 24 de Ohio;
  - errores históricos de las encuestas en Ohio y validación estrictamente cronológica del sesgo estatal;
  - reglas de terceros e indecisos.
- **`revision_sesgo_ohio.py`**: de dónde estimar el sesgo estatal (todas, mismo cargo, sin contiendas de una sola
  encuestadora), LOYO.
- **`revision_ohio.py`**: cronológico de «todas» frente a «k ≥ 2» y emulación de la ventana ampliada.
- **`revision_cargo_cronologico_ohio.py`**: cronológico del sesgo por cargo.
- **`revision_escala_ohio.py`**: ¿las encuestas comprimen las ventajas grandes? (después de `backtest_ohio.py`).
- **Variantes:** G (sesgo contraído), H8 (sin sesgo), F1 (sin contraer), H2/H3 (indecisos), P1/P2/P3/P2s (encuestas partidistas).
- **Datos:** `data/encuestas_2024_wiki.csv` sin Axis Research (oct-2024, distrito 2 de Maine).
- **Módulos de apoyo:** `motor_backtest.py`, `base_florida.py`, `base_georgia.py`, `revision_observaciones.py` (usa el
  paquete `oh_pronostico`).

Resultados y decisión: [`../docs/01_investigacion_y_modelo.md`](../docs/01_investigacion_y_modelo.md).
