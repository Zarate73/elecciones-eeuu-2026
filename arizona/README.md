# Arizona 2026 · Gobernador

Elección general del 3 de noviembre de 2026 entre **Katie Hobbs (D, gobernadora en funciones)** y **Andy Biggs (R)**, con candidatos de terceros en la boleta.

<!-- PRONOSTICO:INICIO -->
**Pronóstico al 2026-10-21** (13 días a la elección) · modelo del notebook; GitHub Actions reemplaza este bloque en la primera corrida

| Gobernador | % de voto (IC80) | Probabilidad de ganar |
|---|---|---|
| Katie **Hobbs** (D) | **51.9%** (48.5–55.3) | **94%** |
| Andy **Biggs** (R) | **44.0%** (40.6–47.4) | **6%** |
| Terceros | 4.1% (1.6–6.5) | — |
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
| Mercados | Promedio de **Kalshi y Polymarket**, mezcla logit con peso 0.30 | No son el mismo precio: la correlación de los cambios diarios es 0.16 y la diferencia media es de 3.3 pp |
| Recuento | P(\|margen\| ≤ 0.5 pp) | Recuento automático según la ley de AZ |
| Voto anticipado (civicAPI) | Diagnóstico, peso 0 | Sin histórico al mismo día para validarlo |
| Ajuste partidista | Solo escenario | No mejora el CRPS (3.579 frente a 3.545) |

## Carpetas
| Carpeta | Contenido |
|---|---|
| [`produccion/`](produccion/) | Paquete `az_pronostico`. Todas las fuentes en vivo: Wikipedia, 270toWin, Kalshi, Polymarket, civicAPI y FiveThirtyEight. Incluye CLI, pruebas sin red y tarea programada de Windows. Ver su README. |
| [`modelo_general/`](modelo_general/) | Notebook final ejecutado (corte 21-oct-2026), el módulo del modelo, datos y salidas |
| [`backtest/`](backtest/) | Backtest de variantes (Georgia V11, primaria AZ, H1–H8), comparación Kalshi frente a Polymarket e ideas de On Point Politics (OP1–OP5) |
| [`docs/`](docs/) | Investigación del electorado, decisiones del modelo y revisión de On Point Politics |
