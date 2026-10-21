# Backtest Arizona · general 2026

- `python backtest_arizona.py`: compara Georgia V11, la primaria de AZ tal cual y 8 híbridos (LOYO, H = 13 días; ~4 min). Escribe:
  - `salida/metricas_margen.csv`: CRPS, MAE, sesgo, cobertura y Brier, nacional y AZ;
  - `salida/bootstrap_vs_V11.csv`: P(variante mejor que V11), remuestreando años;
  - `salida/metricas_porcentajes.csv`: % D y % R con 4 reglas para terceros;
  - `salida/predicciones_LOYO.csv`.
- `python mercados_kalshi_polymarket.py`: Kalshi contra Polymarket (AZ Gob 2026, Pres 2024, Sen 2024).
- `python backtest_onpoint.py`: prueba las ideas de On Point Politics (penalización e exclusión por indecisos, recorte de atípicas, calidad de la encuestadora, terceros con historial). Escribe `salida/onpoint_*.csv`.
- `data/onpoint_civicapi/`: JSON de encuestas de On Point; voto anticipado y pronóstico de civicAPI (21-oct).
- `base_georgia.py`: copia de `backtest_georgia.py` de Georgia (carga de datos, efectos de casa, σ).
- `data/`:
  - FiveThirtyEight raw polls;
  - GA Pres 2024;
  - AZ 2024 (Pres y Sen, de Wikipedia, una versión por encuesta);
  - páginas de Wikipedia y 270toWin;
  - mercados (velas de Kalshi e historia de Polymarket), capturados vía GitHub Actions el 21-oct.

Resultado: ver `../docs/01_investigacion_y_modelo.md`, sección 2.
