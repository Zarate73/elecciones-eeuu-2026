# Backtest Illinois (general)

- **`backtest_illinois.py`** corre las variantes y escribe `salida/` (`consola.txt` tiene el resumen):
  - leave-one-year-out, H = 9 y ventana de producción de 9 a 21 días;
  - 945 contiendas (1998–2024), 19 de Illinois;
  - errores históricos de las encuestas en Illinois y validación estrictamente cronológica del sesgo estatal;
  - reglas de terceros e indecisos.
- **`revision_sesgo_illinois.py`**: de dónde estimar el sesgo estatal (todas, mismo cargo, sin contiendas de una sola
  encuestadora), LOYO.
- **`revision_illinois.py`**: cronológico de «todas» frente a «k ≥ 2» y emulación de la ventana ampliada (hoy aplica en IL).
- **`revision_cargo_cronologico_illinois.py`**: cronológico del sesgo por cargo.
- **`revision_escala_illinois.py`**: ¿las encuestas comprimen las ventajas grandes? (correr después de `backtest_illinois.py`).
- **Variantes:** G (sesgo contraído), H8 (sin sesgo), F1 (sin contraer), H2/H3 (indecisos), P1/P2/P3/P2s (encuestas partidistas).
- **Datos:** `data/encuestas_2024_wiki.csv` sin Axis Research (oct-2024, distrito 2 de Maine). No hay contiendas de
  Illinois en 2024 ni 2018 con encuestas en la ventana de 9 a 21 días.
- **Módulos de apoyo:** `motor_backtest.py`, `base_florida.py`, `base_georgia.py`, `revision_observaciones.py` (usa el
  paquete `il_pronostico`).

Resultados y decisión: [`../docs/01_investigacion_y_modelo.md`](../docs/01_investigacion_y_modelo.md).
