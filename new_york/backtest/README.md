# Backtest Nueva York (general)

- **`backtest_new_york.py`** corre las variantes y escribe `salida/` (`consola.txt` tiene el resumen):
  - leave-one-year-out, H = 9 y ventana de producción de 9 a 21 días;
  - 945 contiendas (1998–2024), 20 de Nueva York;
  - errores históricos de las encuestas en Nueva York y validación estrictamente cronológica del sesgo estatal;
  - reglas de terceros e indecisos.
- **`revision_sesgo_new_york.py`**: de dónde estimar el sesgo estatal (todas, mismo cargo, sin contiendas de una sola
  encuestadora), LOYO.
- **`revision_new_york.py`**: cronológico de «todas» frente a «k ≥ 2» y emulación de la ventana ampliada.
- **`revision_cargo_cronologico_new_york.py`**: cronológico del sesgo por cargo.
- **`revision_escala_new_york.py`**: ¿las encuestas comprimen las ventajas grandes? (después de `backtest_new_york.py`).
- **Variantes:** G (sesgo contraído), H8 (sin sesgo), F1 (sin contraer), H2/H3 (indecisos), P1/P2/P3/P2s (encuestas partidistas).
- **Datos:** `data/encuestas_2024_wiki.csv` sin Axis Research (oct-2024, distrito 2 de Maine).
- **Módulos de apoyo:** `motor_backtest.py`, `base_florida.py`, `base_georgia.py`, `revision_observaciones.py` (usa el
  paquete `ny_pronostico`).

Resultados y decisión: [`../docs/01_investigacion_y_modelo.md`](../docs/01_investigacion_y_modelo.md).
