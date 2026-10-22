# Backtest Nevada (general)

- **`backtest_nevada.py`** corre las 9 variantes y escribe `salida/` (`consola.txt` tiene el resumen):
  - leave-one-year-out, H = 12 y ventana de producción de 12 a 21 días;
  - 848 contiendas, 23 de NV;
  - validación estrictamente cronológica del sesgo estatal;
  - reglas de terceros.
- **Variantes:**
  - G: V11 con sesgo estatal contraído (regla de Florida);
  - H8: sin sesgo (regla de Arizona);
  - F1: sesgo sin contraer;
  - H2 y H3: reparto de indecisos;
  - P1, P2 y P3: tratamiento de encuestas internas de campaña.
- **Módulos de apoyo:**
  - `motor_backtest.py`: motor común;
  - `base_florida.py`: carga del histórico 538 + 2024;
  - `revision_observaciones.py`: ventana de producción, validación cronológica y terceros (usa el paquete `nv_pronostico`);
  - `base_georgia.py`: utilidades de Georgia.

Resultados y decisión: `../docs/01_investigacion_y_modelo.md`.
