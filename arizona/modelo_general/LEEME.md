# Arizona Gobernador 2026 · Modelo final (general)

- `ARIZONA_2026_MODELO_FINAL.ipynb`: notebook ejecutado. Pronóstico, encuestas, escenarios, mercados, backtest y electorado.
- `arizona_modelo_final.py`: el modelo. `import arizona_modelo_final as am; r = am.ejecutar()`.
- `encuestas_web.py`: parsers de Wikipedia y 270toWin (los mismos de la producción de Georgia).
- `pruebas.py`: 10 pruebas sin red (`python pruebas.py`).
- `datos/`: insumos.
  - Histórico de FiveThirtyEight, GA 2024 y AZ 2024.
  - Tu Excel.
  - Capturas de Wikipedia y 270toWin del 21-oct.
  - Mercados.
  - Diagnóstico del electorado.
  - `civicapi/`: snapshots del voto anticipado de civicAPI e historial diario.
- `salida/`: pronóstico, escenarios, encuestas combinadas y pesos, voto anticipado por condado, errores históricos de AZ y gráficas.

## Modelo
Georgia V11 sin sesgo estatal, más terceros calibrados, indecisos 50/50 y mercados (Kalshi + Polymarket) con peso 0.30. El porqué de cada pieza está en `../docs/01_investigacion_y_modelo.md` y en `../backtest`.

## Para actualizar
1. Agrega las encuestas nuevas a tu Excel, o vuelve a capturar Wikipedia y 270toWin. Las capturas se guardan como `datos/wikipedia_az_gob_<fecha>.json` y `datos/t270_az_gob_<fecha>.html`; actualiza los nombres en `encuestas_2026()`.
2. El voto anticipado se baja solo de civicAPI en cada corrida (`Config.civicapi_en_vivo = True`). Si falla, usa el último snapshot de `datos/civicapi/` y lo indica. Cada corrida agrega un día a `datos/civicapi/historial_az.csv`.
3. Agrega el último precio de los mercados en `datos/mercados_az_gob2026_diario.csv`.
4. Cambia `Config.corte` y vuelve a correr el notebook.

Requisitos: `pip install -r requirements.txt` (pandas, numpy, scipy, openpyxl, lxml, matplotlib).
