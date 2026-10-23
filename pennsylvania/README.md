# Pennsylvania 2026 · Gobernador

Elección general del 3 de noviembre de 2026 entre **Josh Shapiro (D, gobernador en funciones)** y **Stacy Garrity (R, tesorera estatal)**. En la boleta también aparece Ken Krawchuk (libertario).

<!-- PRONOSTICO:INICIO -->
**Pronóstico al 2026-10-23** (11 días a la elección) · actualizado automáticamente 2026-10-23 17:18 ET · fuentes en vivo 8/8

| Gobernador | % de voto (IC80) | Probabilidad de ganar |
|---|---|---|
| Josh **Shapiro** (D, gobernador) | **58.4%** (54.1–62.6) | **>99%** |
| Stacy **Garrity** (R) | **39.5%** (35.3–43.7) | **<1%** |
| Terceros | 2.1% (0.1–4.5) | — |

Margen D−R +18.8 pp (σ 6.5) · solo encuestas: P(Shapiro) >99% · Kalshi 97% · Polymarket 98% (peso de mercados 0.3) · recuento automático 0.1% · 18 encuestas, 2 encuestadoras en la ventana

Cómo se llega: promedio de encuestas +22.4 · sesgo estatal de Pennsylvania -1.0 · mercados -2.5

**Encuesta más reciente:** ActiVote, terminó el 2026-10-21 (**2 días** antes del corte). Las fuentes se consultan en vivo, pero el promedio solo puede ser tan reciente como la última encuesta publicada.

**Boletas por correo devueltas** (civicAPI, diagnóstico, al 2026-10-23): 720,664 · registrados D 67.0% · R 24.1% · sin partido y otros 8.9%. PA no tiene voto anticipado en persona y el correo es muy demócrata por hábito: no indica el resultado y no entra al pronóstico.

![Pronóstico](produccion/salidas/ultimo/pronostico.png)

![Evolución](produccion/salidas/evolucion.png)

Detalle: [`resumen.txt`](produccion/salidas/ultimo/resumen.txt) · [encuestas usadas](produccion/salidas/ultimo/encuestas_gobernador.csv) · [escenarios](produccion/salidas/ultimo/escenarios_gobernador.csv) · [voto anticipado por condado](produccion/salidas/ultimo/voto_anticipado_condados.csv) · [historial](produccion/salidas/historial_pronosticos.csv)
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
