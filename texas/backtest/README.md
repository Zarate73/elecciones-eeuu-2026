# Backtest Texas (general)

- **`backtest_texas.py`** corre las variantes y escribe `salida/` (`consola.txt` tiene el resumen):
  - leave-one-year-out, H = 9 y ventana de producción de 9 a 21 días;
  - 945 contiendas (1998–2024), 20 de Texas;
  - errores históricos de las encuestas en Texas y validación estrictamente cronológica del sesgo estatal;
  - reglas de terceros (el libertario se desinfla) e indecisos.
- **`revision_sesgo_texas.py`**: de dónde estimar el sesgo estatal (todas las contiendas, mismo cargo o sin contiendas
  de una sola encuestadora), como reglas nacionales, LOYO.
- **`revision_texas.py`**: validación cronológica de «todas» frente a «k ≥ 2» y emulación de la ventana ampliada.
- **`revision_cargo_cronologico_texas.py`**: validación cronológica del sesgo por cargo (gana en LOYO de TX).
- **Variantes:**
  - G: V11 con sesgo estatal contraído; H8: sin sesgo; F1: sesgo sin contraer;
  - H2 y H3: reparto de indecisos;
  - P1, P2 y P3: tratamiento de encuestas de patrocinio partidista; P2s: P2 sin sesgo.
- **Datos:** `data/encuestas_2024_wiki.csv` sin Axis Research (oct-2024, distrito 2 de Maine).
- **Módulos de apoyo:** `motor_backtest.py`, `base_florida.py`, `base_georgia.py`, `revision_observaciones.py` (usa el
  paquete `tx_pronostico`).

Resultados y decisión: [`../docs/01_investigacion_y_modelo.md`](../docs/01_investigacion_y_modelo.md).
