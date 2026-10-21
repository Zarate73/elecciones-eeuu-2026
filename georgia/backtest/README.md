# Backtest Georgia · selección de modelo (corte 19-oct-2026, T−15)

```
py -m pip install pandas numpy scipy matplotlib
py backtest_georgia.py          # 4 agregadores × 5 variantes, LOYO, horizontes T−0 y T−15
py analisis_complementario.py   # indecisos, bootstrap por año, sesgo estatal con decaimiento
py aplicar_2026.py              # pronóstico 2026 con el modelo ganador
py analisis_indecisos_kalshi.py  # indecisos dentro del modelo ganador
py figura_resumen.py
```

## Datos (`data/`)
| archivo | contenido | fuente |
|---|---|---|
| fte_raw_polls_2023.csv | encuestas de los últimos 21 días, Gob/Sen/Pres 1998–2022, todos los estados, con resultado | github.com/fivethirtyeight/data · pollster-ratings/2023 |
| ga_pres2024_polls.csv | 37 encuestas GA Presidente 14-oct a 4-nov-2024 (LV) | Wikipedia; resultado SOS: Harris 48.53, Trump 50.73 |
| kalshi_GOVPARTYGA-26-D_diario.csv | velas diarias del mercado Bottoms (17-jun a 20-oct-2026) | API pública Kalshi `/series/GOVPARTYGA/markets/GOVPARTYGA-26-D/candlesticks` |
| kalshi_PRESPARTYGA-24-D_diario.csv | velas GA Presidente 2024 (Harris), 15-oct a 5-nov | API Kalshi `/historical/markets/.../candlesticks` |
| ga_gob2026_encuestas.csv | 14 encuestas Bottoms–Jackson (incluye G-Ratings 24–29 sep) | Wikipedia, DDHQ, WRDW, Excel G-Ratings |

## Validación
- Unidad de validación = **año** (leave-one-year-out): los errores de un mismo año están correlacionados (≈20% de la varianza es común al año).
- 980 contiendas nacionales (701 con encuestas a T−15), 24 en Georgia (21 generales).
- Métricas: MAE, RMSE, CRPS (principal), log-score, cobertura 80/95, Brier del ganador.

## Modelo ganador
`mu = promedio(encuestas − efecto de casa) − sesgo_GA` y `sigma = sqrt(3.0² + 7.4²/k)`.
- El promedio pondera por recencia (vida media de 14 días) y √n, y cada encuestadora pesa como una sola.
- Los efectos de casa son relativos a la media de cada contienda, contraídos con k=8 y estimados sin el año evaluado.
- El sesgo de GA usa solo ciclos pasados, con vida media de 4 años y contracción bayes empírica. Hoy vale +0.70 (bruto +0.92 × 0.76).
- En sigma, k es el número de encuestadoras distintas.
- Los indecisos se reparten 50/50 y no hay terceros en la boleta 2026.

## Salidas clave (`salida_backtest/`)
`metricas_h15.csv`, `B_bootstrap_crps.csv`, `C_sesgo_estado_decaimiento.csv`, `A_indecisos.csv`, `2026_pronostico.csv`, `2026_encuestas_corregidas.csv`, `resumen_backtest_georgia.png`.

## Limitaciones
- La base de FiveThirtyEight termina en 2022 (más GA-2024 agregado a mano); a nivel nacional no hay 2024.
- La composición del voto anticipado por raza no se pudo validar: solo hay un ciclo comparable al mismo día (2022), así que queda como diagnóstico.
- Quantus, Big Data Poll, Wedgewood, State Navigate y G-Ratings no tienen historial y entran sin ajuste de casa.

## Agregado 20-oct-2026
- **Contendientes:** en la boleta solo están Bottoms (D) y Jackson (R). Los libertarios no lograron el acceso (WABE, 10-jul). El SOS certificó 7 write-ins para Gobernador (15-sep) y ninguno es Chase Oliver; WSB lo lista por error. Los write-ins históricos fueron 81 votos en 2018 y 25 en 2022, así que P(segunda vuelta) ≈ 0.1%.
- **Indecisos:** se reparten 50/50. Dentro del modelo ganador, el reparto ajustado (0.545 a R) empeora el CRPS de 3.455 a 3.489 y el de V9 (0.436) lo lleva a 3.545. El sesgo estatal ya captura la dirección del error.
- **Kalshi:** se mezcla en logit con w=0.30, el mismo peso que California M5. Ese peso **no está validado**: el mercado solo existe desde 2025 y en GA-2024 Kalshi (0.395 a Harris a T−15) quedó por detrás del modelo (0.14). Para validarlo hacen falta los mercados estatales de 2024 junto con promedios de encuestas a T−15.
- **Sentimiento:** no entra al modelo. No hay serie histórica para GA (la API DOC de GDELT cubre ~3 meses y BigQuery requiere un proyecto propio), y en California M3/M4 solo ensancharon la varianza.
