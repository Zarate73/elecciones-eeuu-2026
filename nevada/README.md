# Nevada 2026 · Gobernador

Elección general del 3 de noviembre de 2026 entre **Aaron Ford (D, fiscal general)** y **Joe Lombardo (R, gobernador en funciones)**. En la boleta también aparecen Danielle Ford (independiente) y la opción «None of these candidates».

<!-- PRONOSTICO:INICIO -->
Pendiente de la primera corrida automática.
<!-- PRONOSTICO:FIN -->

GitHub Actions actualiza el bloque anterior dos veces al día ([flujo](../.github/workflows/pronostico_nevada.yml)).

## Modelo general (elegido por backtest)
Base: el modelo de Florida v1.1.0 (Georgia V11). Se validó con un backtest *leave-one-year-out* de 848 contiendas (1998–2024, 23 de Nevada) a 12 días de la elección, con la misma ventana que producción, más una validación estrictamente cronológica.

| Pieza | Cómo entra | Por qué |
|---|---|---|
| Promedio de encuestas | V11: efecto de casa contraído (k = 8), √n, vida media de 14 días, cada firma pesa ~1; ventana de 21 días, ampliada si hay menos de 2 encuestadoras | Mejor CRPS nacional (3.375) |
| Sesgo estatal | Contraído por Bayes empírico: hoy +0.58 pp pro-D (pequeño) | En NV el error cambia de signo entre ciclos (8 de 23 contiendas pro-D, autocorrelación −0.11). Quitarlo no es ni mejor ni peor (CRPS 3.265 vs 3.321, P = 0.62; cronológico P = 0.55), así que se usa la regla nacional. «Sin sesgo» se reporta siempre |
| Encuestas internas de campaña | Con su efecto de casa; el ajuste por patrocinador queda como escenario | Descartarlas, pesarlas a la mitad o ajustarlas por patrocinador empeora el CRPS en NV (P ≤ 0.006) |
| Terceros | `real = a + c·(otros en las encuestas que los reportan)`; si ninguna los reporta, media histórica. Incluye a Danielle Ford y «None of these candidates» | Calibrado con el resultado real (100 − D − R) |
| Indecisos | 50/50 | El reparto proporcional gana en NV (3.166) pero es el peor a nivel nacional (3.650, P = 0.000): sería sobreajuste |
| σ | `√(τ² + s²/k)` calibrada a los días que faltan, t de Student, más una deriva de 0.25 pp/día si las encuestas son más viejas que ese horizonte | Cobertura del 80 % correcta en el backtest |
| Mercados | Promedio de **Kalshi y Polymarket**, mezcla logit con peso 0.30; la distribución del margen se desplaza para que P(margen > 0) sea la probabilidad publicada | En NV no son el mismo precio (cambios diarios con correlación −0.03). Peso estimado con 40 contiendas de 2024 ([detalle](../arizona/docs/03_peso_mercados.md)) |
| Resultado muy estrecho | P(\|margen\| ≤ 0.5 pp) | NV no tiene recuento automático (lo puede pedir un candidato) |
| Voto ya emitido (civicAPI) | Diagnóstico, peso 0 | Es registro de partido, no intención de voto; el 39 % del padrón es no partidista |

## Carpetas
| Carpeta | Contenido |
|---|---|
| [`produccion/`](produccion/) | Paquete `nv_pronostico`. Todas las fuentes en vivo: Wikipedia, 270toWin, Kalshi, Polymarket, civicAPI y FiveThirtyEight. Incluye CLI, pruebas sin red y tarea programada de Windows |
| [`backtest/`](backtest/) | Backtest de variantes (sesgo estatal, indecisos, encuestas internas, terceros) y errores históricos de las encuestas en NV |
| [`docs/`](docs/) | Investigación del electorado (registro, no partidistas, voto anticipado, indecisos), fuentes y decisiones del modelo |
