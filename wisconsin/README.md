# Wisconsin 2026 · Gobernador

Elección general del 3 de noviembre de 2026 entre **David Crowley (D, ejecutivo del condado de Milwaukee)** y **Tom Tiffany (R, congresista del distrito 7)**. Solo ellos dos están en la boleta (más votos por escrito). El gobernador Tony Evers (D) no busca un tercer periodo. Gana la mayoría simple.

<!-- PRONOSTICO:INICIO -->
Se llena con la primera corrida automática.
<!-- PRONOSTICO:FIN -->

GitHub Actions actualiza el bloque anterior dos veces al día ([flujo](../.github/workflows/pronostico_wisconsin.yml)).

## Modelo general (elegido por backtest)
Base: el modelo de North Carolina v1.0.0 / Ohio v1.2.0 (Georgia V11) con la **regla de Arizona: sin sesgo estatal**. Se validó con un backtest *leave-one-year-out* de 1003 contiendas (1998–2024, 25 de Wisconsin) a 6 días de la elección, con la misma ventana que producción, más una validación estrictamente cronológica.

| Pieza | Cómo entra | Por qué |
|---|---|---|
| Promedio de encuestas | V11: efecto de casa contraído (k = 8), √n, vida media de 14 días, cada firma pesa ~1; ventana de 21 días (hoy, 2 encuestadoras: Marquette y Wick) | Mejor CRPS nacional (3.158) |
| Identidad de las encuestas | Firma + periodo de campo; Marquette, TIPP, Badger Battleground/Platform, RMG y YouGov/City Forward con sus alias | Conservan su efecto de casa y no se cuentan dos veces |
| Sesgo estatal | **No se aplica** (escenario: −0.50 pp) | El error de las encuestas en WI cambia de signo (presidente 2016 +5.9 y 2020 +7.4 pro-D; gobernador 2022 −4.1 pro-R); LOYO WI 2.630 sin sesgo vs 2.822 (P = 0.88); gobernador WI 2.924 vs 3.147 (P = 0.93) |
| Terceros | Solo dos candidatos en la boleta: votos por escrito fijos (0.10 ± 0.05 %) | Como Nueva York |
| Indecisos | 50/50 | El reparto proporcional y la cuota R son peores |
| Ventajas grandes | Sin ajuste de escala | b = 1.00 fuera de muestra |
| σ | `√(τ² + s²/k)` calibrada a los días que faltan, t de Student, más una deriva (paseo aleatorio, 0.25 pp por √día) | Cobertura del 80 % correcta en el backtest |
| Mercados | Promedio de **Kalshi y Polymarket**, mezcla logit con peso 0.30 | Peso estimado con 40 contiendas de 2024 ([detalle](../arizona/docs/03_peso_mercados.md)) |
| Recuento | P(\|margen\| ≤ 1 pp) | Recuento a petición si se pierde por ≤ 1 % |
| Voto anticipado | civicAPI por condado (72), sin partido | Diagnóstico, peso 0 |

## Carpetas
| Carpeta | Contenido |
|---|---|
| [`produccion/`](produccion/) | Paquete `wi_pronostico`. Fuentes en vivo: Wikipedia, 270toWin, Kalshi, Polymarket, civicAPI y FiveThirtyEight. Incluye CLI, pruebas sin red y tarea programada de Windows |
| [`backtest/`](backtest/) | Backtest de variantes (sesgo estatal, indecisos, encuestas partidistas, terceros), variantes por cargo, validación cronológica del sesgo y escala de ventajas grandes |
| [`docs/`](docs/) | Investigación del electorado (independientes, participación, voto anticipado), indecisos, contexto, fuentes y decisiones del modelo |
