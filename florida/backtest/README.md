# Backtest Florida (general)

- `backtest_florida.py`: corre las 11 variantes (LOYO, H = 12, 848 contiendas, 23 de FL) y escribe `salida/`.
- `motor_backtest.py`: motor común, generalizado del de Arizona. `base_georgia.py`: utilidades de Georgia.
- `construir_2024.py`: arma `data/encuestas_2024_wiki.csv` (encuestas finales de 2024 desde Wikipedia). Ya está construido.
- Resultados:
  - `salida/metricas_margen.csv` (CRPS, MAE, cobertura);
  - `salida/bootstrap_vs_G.csv`;
  - `salida/errores_encuestas_FL.csv`;
  - `salida/error_relativo_FL.csv`;
  - `salida/metricas_porcentajes.csv` (reglas de terceros).

El resultado está en [`../docs/01_investigacion_y_modelo.md`](../docs/01_investigacion_y_modelo.md), sección 4.
