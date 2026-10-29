# Backtest Wisconsin (general · gobernador)

- **`backtest_wisconsin.py`** corre las variantes y escribe `salida/` (`consola.txt` tiene el resumen):
  - leave-one-year-out, H = 6 (corte 28-oct) y ventana de producción de 6 a 21 días;
  - 1003 contiendas (1998–2024), 25 de Wisconsin (8 de gobernador);
  - errores históricos de las encuestas en WI y validación estrictamente cronológica del sesgo estatal;
  - reglas de terceros e indecisos, encuestas partidistas.
- **`revision_variantes_cargo_wisconsin.py`**: variantes por cargo (σ por cargo, sesgo por cargo, sesgo nacional del cargo,
  fundamentales, escala) frente a G → `salida/revision_variantes_cargo.csv` y `.txt`.
- **`revision_sesgo_wisconsin.py`**: de dónde estimar el sesgo estatal (todas, mismo cargo, k ≥ 2, sin sesgo), LOYO.
- **`revision_cargo_cronologico_wisconsin.py`**: cronológico del sesgo por cargo.
- **`revision_escala_wisconsin.py`**: ¿las encuestas comprimen las ventajas grandes? (después de `backtest_wisconsin.py`).
- **`revision_wisconsin.py`**: cronológico de «todas» frente a «k ≥ 2» y emulación de la ventana ampliada.
- **Decisión:** sin sesgo estatal (regla de Arizona): en WI el error cambia de signo y el sesgo empeora el CRPS
  (LOYO 2.630 sin sesgo vs 2.822; gobernador WI 2.924 vs 3.147).
- **Módulos de apoyo:** `motor_backtest.py`, `base_florida.py`, `base_georgia.py`, `revision_observaciones.py` (usa el
  paquete `wi_pronostico`).

Resultados y decisión: [`../docs/01_investigacion_y_modelo.md`](../docs/01_investigacion_y_modelo.md).
