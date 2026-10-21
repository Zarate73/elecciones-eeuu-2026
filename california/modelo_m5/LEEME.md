# ODISEO · California · Modelo híbrido M5

## Cómo correrlo
1. Esta carpeta debe estar junto a `CALIFORNIA_2026_NOTEBOOK_COMPLETO/`. De ahí se leen el Excel, `entrega_odiseo/` y el último snapshot de Civiq. Si prefieres que sea autónoma, copia esos archivos dentro de esta carpeta: siempre se busca aquí primero.
2. `python -m pip install -r requirements.txt` y, si Civiq lo pide, `python -m playwright install chromium`.
3. Abre `CALIFORNIA_Modelo_Hibrido_M5.ipynb` y ejecuta todo. Para actualizar, vuelve a correr la celda `resultado = await actualizar_m5(...)`.
4. Sin red: define la variable de entorno `CALIFORNIA_NOTEBOOK_OFFLINE=1`. En ese modo usa las cachés y lo indica en el reporte.

## Fuentes
| Fuente | Cómo se obtiene | Uso en M5 |
|---|---|---|
| Excel de encuestas | archivo local | media (agregado corregido) |
| Civiq | Brave/Playwright (igual que el original) | M2 corregido por edad; ahora guarda la historia diaria y la tabla partido×edad |
| Sentimiento ODISEO | `entrega_odiseo/serie_sentimiento_diaria.csv` | candidato a k_sent (no se aplica sin validar) |
| GDELT DOC 2.0 | API pública | acumula tono diario; candidato a k_sent (no se aplica sin validar) |
| Kalshi | API pública `trade-api/v2` | mezcla logit con W_KALSHI = 0.30 |
| PDI | captura manual en `data/pdi_retornos_manual.csv` | solo contraste de Civiq |
| Backtest CA 2018–2025 | `data/generales_*.csv` | calibra σ_sis en cada corrida |
| Conteo de la primaria 2026 | `data/conteo_primaria_2026.csv` | corrimiento tardío para la noche electoral |

## Interruptores
- `W_M2`: pásalo de 0 a un valor positivo solo si M2 corregido mejora el CRPS en 2022G y 2024G, usando `salida_m5/civiq_historia_diaria.csv`.
- `VALIDADO_SENTIMIENTO`: actívalo solo si la anomalía de tono predice fuera de muestra la volatilidad del promedio de encuestas.
- `MODO_CONTEO = True` la noche electoral: apaga Kalshi.

## Sentimiento histórico (para validar M4/k_sent)
La API DOC de GDELT solo cubre ~3 meses. Para 2018–2025 hay que usar BigQuery:
```sql
SELECT DATE(PARSE_TIMESTAMP('%Y%m%d%H%M%S', CAST(DATE AS STRING))) AS fecha,
       AVG(CAST(SPLIT(V2Tone, ',')[OFFSET(0)] AS FLOAT64)) AS tono, COUNT(*) AS n
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE _PARTITIONTIME BETWEEN '2022-08-01' AND '2022-11-09'
  AND V2Persons LIKE '%Gavin Newsom%'
GROUP BY fecha ORDER BY fecha
```
Repite la consulta por candidato y elección, y guarda el resultado en el mismo formato que `salida_m5/gdelt_tono_diario.csv`.

## Salidas (`salida_m5/`)
- `reporte_m5.json`: todo el corte (fuentes, estados, parámetros, componentes de varianza)
- `comparacion_modelos.csv` e `historial_m5.csv`: M1–M4 legados frente a M5
- `encuestas_pesos_m5.csv`: peso de cada encuesta, M5 frente al legado
- `calibracion_sigma_backtest.csv`, `civiq_historia_diaria.csv`, `gdelt_tono_diario.csv`, `kalshi_snapshots.csv`
- Gráficas: `comparacion_M1_M5.png`, `m5_componentes_varianza.png`, `m5_probabilidades.png`
