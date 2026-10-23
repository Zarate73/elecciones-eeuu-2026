# Pennsylvania 2026 · Gobernador

Elección general del 3 de noviembre de 2026 entre **Josh Shapiro (D, gobernador en funciones)** y **Stacy Garrity (R, tesorera estatal)**. En la boleta también aparece Ken Krawchuk (libertario).

<!-- PRONOSTICO:INICIO -->
Pendiente de la primera corrida automática.
<!-- PRONOSTICO:FIN -->

GitHub Actions actualiza el bloque anterior dos veces al día ([flujo](../.github/workflows/pronostico_pennsylvania.yml)).

## Modelo general (elegido por backtest)
Base: el modelo de Nevada v1.1.0 (Florida v1.1.0 / Georgia V11). Se validó con un backtest *leave-one-year-out* de 902 contiendas (1998–2024, 24 de Pennsylvania) a 11 días de la elección, con la misma ventana que producción, más una validación estrictamente cronológica.

| Pieza | Cómo entra | Por qué |
|---|---|---|
| Promedio de encuestas | V11: efecto de casa contraído (k = 8), √n, vida media de 14 días, cada firma pesa ~1; ventana de 21 días, ampliada si hay menos de 2 encuestadoras. Si una encuesta trae LV y RV se usa la LV | Mejor CRPS nacional (3.391) |
| Encuestadoras con varios nombres | PennLive = Bravo Group; NYT/Inquirer/Siena con una sola clave | Evita contar dos veces la misma encuesta y separar su efecto de casa |
| Sesgo estatal | Contraído por Bayes empírico: hoy se restan ~1.0 pp (las encuestas en PA sobreestimaron al demócrata) | En PA quitarlo no es mejor ni peor (3.312 vs 3.320, P = 0.52; cronológico P = 0.52). Gana a nivel nacional (P = 0.002 cronológico). Desde 2016 las encuestas sobreestimaron al demócrata salvo en 2022. «Sin sesgo» se reporta siempre |
| Encuestas internas de campaña | Con su efecto de casa; el ajuste por patrocinador queda como escenario | P1, P2 y P3 son peores en PA |
| Terceros | `real = a + c·(otros en las encuestas que los reportan)`; si ninguna los reporta, media histórica | Calibrado con el resultado real (100 − D − R) |
| Indecisos | 50/50 | El reparto proporcional es el peor en PA (3.912) y a nivel nacional |
| Ventajas grandes | Sin ajuste por paliza | En 357 contiendas con ventaja ≥ 15 pp, la escala estimada del margen es 0.99 y no mejora |
| σ | `√(τ² + s²/k)` calibrada a los días que faltan, t de Student, más una deriva de 0.25 pp/día si las encuestas son más viejas que ese horizonte | Cobertura del 80 % correcta en el backtest |
| Mercados | Promedio de **Kalshi y Polymarket**, mezcla logit con peso 0.30; la distribución del margen se desplaza para que P(margen > 0) sea la probabilidad publicada | Peso óptimo 0.30 también en las contiendas de 2024 con mercados extremos (< 0.1 o > 0.9). Con probabilidades cercanas a 1 la mezcla baja el margen aunque los mercados también den ganador a Shapiro: para el margen, «sin mercados» y Polymarket por rangos son lecturas igual de defendibles |
| Recuento automático | P(\|margen\| ≤ 0.5 pp) | Ley de PA |
| Escenarios | Cruce 2 × 2 de sesgo × mercados, influencia de cada encuesta, terceros, peso de mercados 0.15 y 0.50 | Igual que Nevada |
| Boletas por correo (civicAPI) | Diagnóstico, peso 0 | PA no tiene voto anticipado en persona y el correo es muy demócrata por hábito |

## Carpetas
| Carpeta | Contenido |
|---|---|
| [`produccion/`](produccion/) | Paquete `pa_pronostico`. Todas las fuentes en vivo: Wikipedia, 270toWin, Kalshi, Polymarket, civicAPI y FiveThirtyEight. Incluye CLI, pruebas sin red y tarea programada de Windows |
| [`backtest/`](backtest/) | Backtest de variantes (sesgo estatal, indecisos, encuestas internas, terceros, escala del margen) y errores históricos de las encuestas en PA |
| [`docs/`](docs/) | Investigación del electorado (registro, correo, indecisos), contexto de la campaña, fuentes y decisiones del modelo |
