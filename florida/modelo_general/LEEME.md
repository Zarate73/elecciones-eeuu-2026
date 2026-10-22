# Florida Gobernador 2026 · Modelo final (general)

- `FLORIDA_2026_MODELO_FINAL.ipynb`: notebook ejecutado. Incluye pronóstico, encuestas, escenarios, mercados, backtest, errores históricos y voto anticipado.
- `florida_modelo_final.py`: el modelo. Se usa con `import florida_modelo_final as fm; r = fm.ejecutar()`.
- `encuestas_web.py`: parsers de Wikipedia y 270toWin, los mismos de la producción de Georgia.
- `pruebas.py`: 8 pruebas sin red (`python pruebas.py`).
- `datos/`:
  - histórico de FiveThirtyEight, 2024 (incluye FL Presidente y Senado) y AZ/GA 2024;
  - tu Excel;
  - capturas de Wikipedia y 270toWin del 22-oct;
  - mercados;
  - voto anticipado de civicAPI;
  - electorado.
- `salida/`: pronóstico, escenarios, encuestas combinadas y pesos, voto anticipado por condado y errores históricos de FL.

## Modelo
Georgia V11 **con** sesgo estatal contraído, más terceros calibrados, indecisos 50/50 y mercados (Kalshi + Polymarket) con peso 0.30. El porqué de cada pieza está en [`../docs/01_investigacion_y_modelo.md`](../docs/01_investigacion_y_modelo.md) y en [`../backtest/`](../backtest/).

## Para actualizar
1. Agrega las encuestas nuevas a tu Excel, o vuelve a capturar Wikipedia y 270toWin. Los nombres de los archivos están en `encuestas_2026()`.
2. El voto anticipado se baja solo de civicAPI si hay internet. Si falla, se usa el último snapshot.
3. Agrega el último precio de los mercados en `datos/mercados_fl_gob2026_diario.csv`.
4. Cambia `Config.corte` y vuelve a correr el notebook.

Requisitos: `pip install -r requirements.txt`.
