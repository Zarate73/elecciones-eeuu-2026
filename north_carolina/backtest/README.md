# Backtest North Carolina (general · Senado)

- **`backtest_north_carolina.py`** corre las variantes y escribe `salida/` (`consola.txt` tiene el resumen):
  - leave-one-year-out, H = 7 (corte 27-oct) y ventana de producción de 7 a 21 días;
  - 992 contiendas (1998–2024): 383 de Senado, 23 de North Carolina (9 de Senado);
  - errores históricos de las encuestas en NC y validación estrictamente cronológica del sesgo estatal (también Senado);
  - reglas de terceros e indecisos, encuestas partidistas.
- **`revision_senado_north_carolina.py`**: ¿sirve el modelo de gobernador para el Senado? Variantes S1 (σ por cargo),
  S2 (sesgo por cargo), S3 (sesgo nacional del cargo), S4 (fundamentales), S5 (escala del margen) frente a G →
  `salida/revision_senado.csv` y `revision_senado.txt`.
- **`revision_sesgo_north_carolina.py`**: de dónde estimar el sesgo estatal (todas, mismo cargo, k ≥ 2), LOYO.
- **`revision_cargo_cronologico_north_carolina.py`**: cronológico del sesgo por cargo.
- **`revision_escala_north_carolina.py`**: ¿las encuestas comprimen las ventajas grandes? (después de `backtest_north_carolina.py`).
- **`revision_north_carolina.py`**: cronológico de «todas» frente a «k ≥ 2» y emulación de la ventana ampliada.
- **Módulos de apoyo:** `motor_backtest.py` (ahora con ámbitos de Senado), `base_florida.py`, `base_georgia.py`,
  `revision_observaciones.py` (usa el paquete `nc_pronostico`).

Resultados y decisión: [`../docs/01_investigacion_y_modelo.md`](../docs/01_investigacion_y_modelo.md).
