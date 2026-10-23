# Backtest Pennsylvania (general)

- **`backtest_pennsylvania.py`** corre las variantes y escribe `salida/` (`consola.txt` tiene el resumen):
  - leave-one-year-out, H = 11 y ventana de producción de 12 a 21 días;
  - 902 contiendas, 24 de PA (7 de gobernador);
  - validación estrictamente cronológica del sesgo estatal;
  - reglas de terceros;
  - contiendas con ventaja ≥ 15 pp y variante E (escala del margen).
- **Variantes:**
  - G: V11 con sesgo estatal contraído (regla de Florida y Nevada);
  - H8: sin sesgo (regla de Arizona);
  - F1: sesgo sin contraer;
  - H2 y H3: reparto de indecisos;
  - P1, P2 y P3: tratamiento de encuestas internas de campaña;
  - E: G con escala del margen estimada fuera de muestra.
- **Módulos de apoyo:**
  - `motor_backtest.py`: motor común;
  - `base_florida.py`: carga del histórico 538 + 2024;
  - `revision_observaciones.py`: ventana de producción, validación cronológica y terceros (usa el paquete `pa_pronostico`);
  - `base_georgia.py`: utilidades de Georgia.

Resultados y decisión: `../docs/01_investigacion_y_modelo.md`.
