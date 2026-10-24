# Backtest Maine (general)

- **`backtest_maine.py`** corre las variantes y escribe `salida/` (`consola.txt` tiene el resumen):
  - leave-one-year-out, H = 10 y ventana de producción de 10 a 21 días;
  - 923 contiendas, 13 de Maine (sin las que el segundo lugar fue un independiente: King, Cutler 2010);
  - validación estrictamente cronológica del sesgo estatal;
  - reglas de terceros e **independiente fuerte**: desinfle del tercero, hacia dónde va su voto y regla por tramos
    (contiendas con terceros ≥ 5 % en las encuestas).
- **`revision_sesgo_maine.py`**: de dónde estimar el sesgo estatal (todas las contiendas, mismo cargo o sin contiendas
  de una sola encuestadora), como reglas nacionales.
- **Variantes:**
  - G: V11 con sesgo estatal contraído; H8: sin sesgo; F1: sesgo sin contraer;
  - H2 y H3: reparto de indecisos;
  - P1, P2 y P3: tratamiento de encuestas internas de campaña.
- **Datos:** `data/encuestas_2024_wiki.csv` sin Axis Research (oct-2024), que era una encuesta del distrito 2 de Maine.
- **Módulos de apoyo:** `motor_backtest.py`, `base_florida.py`, `base_georgia.py`, `revision_observaciones.py` (usa el
  paquete `me_pronostico`).

Resultados y decisión: `../docs/01_investigacion_y_modelo.md`.
