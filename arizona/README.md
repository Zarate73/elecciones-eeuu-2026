# Arizona 2026 · Gobernador

Elección general del 3 de noviembre de 2026 entre **Katie Hobbs (D, gobernadora en funciones)** y **Andy Biggs (R)**, con candidatos de terceros en la boleta.

<!-- PRONOSTICO:INICIO -->
**Pronóstico al 2026-10-21** (13 días a la elección) · actualizado automáticamente 2026-10-21 17:28 MST · fuentes en vivo 8/8

| Gobernador | % de voto (IC80) | Probabilidad de ganar |
|---|---|---|
| Katie **Hobbs** (D) | **51.7%** (48.3–55.1) | **93%** |
| Andy **Biggs** (R) | **44.2%** (40.8–47.6) | **7%** |
| Terceros | 4.1% (1.6–6.5) | — |

Margen D−R +7.5 pp (σ 5.1) · solo encuestas: P(Hobbs) 94% · Kalshi 90% · Polymarket 92% (peso de mercados 0.3) · recuento automático 2.3% · 15 encuestas, 4 encuestadoras en la ventana

**Encuesta más reciente:** GrayHouse (R), terminó el 2026-10-08 (**13 días** antes del corte). Las fuentes se consultan en vivo, pero el promedio solo puede ser tan reciente como la última encuesta publicada.

**Voto anticipado** (civicAPI, diagnóstico, al 2026-10-21): 649,159 boletas devueltas · D 39.1% · R 38.3% · otros 22.6% · Maricopa 59% del total

![Pronóstico](produccion/salidas/ultimo/pronostico.png)

![Evolución](produccion/salidas/evolucion.png)

Detalle: [`resumen.txt`](produccion/salidas/ultimo/resumen.txt) · [encuestas usadas](produccion/salidas/ultimo/encuestas_gobernador.csv) · [escenarios](produccion/salidas/ultimo/escenarios_gobernador.csv) · [voto anticipado por condado](produccion/salidas/ultimo/voto_anticipado_condados.csv) · [historial](produccion/salidas/historial_pronosticos.csv)
<!-- PRONOSTICO:FIN -->

GitHub Actions actualiza el bloque anterior dos veces al día ([flujo](../.github/workflows/pronostico_arizona.yml)).

## Modelo general (elegido por backtest)
Base: el modelo V11 de Georgia, más lo que el backtest respaldó del modelo de la primaria de Arizona. Se validó con un backtest *leave-one-year-out* de 782 contiendas (22 de Arizona), donde ganó el menor CRPS.

| Pieza | Cómo entra | Por qué |
|---|---|---|
| Promedio de encuestas | V11: efecto de casa contraído (k = 8), √n, vida media de 14 días, cada firma pesa ~1 | Mejor CRPS nacional (3.495) |
| Sesgo estatal | **No se usa** | En AZ el error no persiste entre ciclos (autocorrelación −0.11 frente a +0.22 nacional); quitarlo bajó el CRPS de AZ de 2.630 a 2.471 |
| Terceros | `real = 1.87 + 0.69 · (otros en encuestas)`, calibrado | El MAE del % demócrata bajó de 2.53 a 1.94 en AZ |
| Indecisos | 50/50 | Los escenarios por facción, el reparto proporcional y la cuota R estimada empeoran el CRPS |
| σ | `√(τ² + s²/k)` calibrada a los días que faltan, t de Student, más una deriva de 0.25 pp/día si las encuestas son más viejas que ese horizonte | Cobertura del 80 % correcta en el backtest |
| Mercados | Promedio de **Kalshi y Polymarket**, mezcla logit con peso 0.30. La distribución del margen se desplaza para que P(margen > 0) sea igual a la probabilidad publicada | No son el mismo precio (correlación de cambios diarios 0.16). Peso por máxima verosimilitud con 40 contiendas de 2024: 0.65 (IC95 0.25–1.00), pero 0.25 (IC95 0–0.65) al descontar el error común de 2024; 0.30 es compatible con ambos ([detalle](docs/03_peso_mercados.md)) |
| Recuento | P(\|margen\| ≤ 0.5 pp) | Recuento automático según la ley de AZ |
| Voto anticipado (civicAPI) | Diagnóstico, peso 0 | Sin histórico al mismo día para validarlo |
| Ajuste partidista | Solo escenario | No mejora el CRPS (3.579 frente a 3.545) |

## Carpetas
| Carpeta | Contenido |
|---|---|
| [`produccion/`](produccion/) | Paquete `az_pronostico`. Todas las fuentes en vivo: Wikipedia, 270toWin, Kalshi, Polymarket, civicAPI y FiveThirtyEight. Incluye CLI, pruebas sin red y tarea programada de Windows. Ver su README. |
| [`modelo_general/`](modelo_general/) | Notebook final ejecutado (corte 21-oct-2026), el módulo del modelo, datos y salidas |
| [`backtest/`](backtest/) | Backtest de variantes (Georgia V11, primaria AZ, H1–H8), comparación Kalshi frente a Polymarket e ideas de On Point Politics (OP1–OP5) |
| [`docs/`](docs/) | Investigación del electorado, decisiones del modelo, revisión de On Point Politics y estimación del peso de los mercados |
