# Florida 2026 · Gobernador

Elección general del 3 de noviembre de 2026 entre **David Jolly (D)** y **Byron Donalds (R)**, con candidatos de terceros en la boleta. El gobernador Ron DeSantis no puede reelegirse.

<!-- PRONOSTICO:INICIO -->
**Pronóstico al 2026-10-22** (12 días a la elección) · actualizado automáticamente 2026-10-22 03:51 ET · fuentes en vivo 8/8

| Gobernador | % de voto (IC80) | Probabilidad de ganar |
|---|---|---|
| David **Jolly** (D) | **44.8%** (41.5–48.2) | **5%** |
| Byron **Donalds** (R) | **53.1%** (49.8–56.5) | **95%** |
| Terceros | 2.0% (0.1–4.3) | — |

Margen D−R -8.3 pp (σ 5.1) · solo encuestas: P(Jolly) 3% · Kalshi 22% · Polymarket 20% (peso de mercados 0.3) · recuento por máquina 1.9% · 16 encuestas, 4 encuestadoras en la ventana

Cómo se llega: promedio de encuestas -5.3 · sesgo estatal de Florida -4.8 (las encuestas de FL han sobreestimado al demócrata) · mercados +1.8

**Encuesta más reciente:** co/efficient (R), terminó el 2026-10-20 (**2 días** antes del corte). Las fuentes se consultan en vivo, pero el promedio solo puede ser tan reciente como la última encuesta publicada.

**Voto ya emitido** (civicAPI, diagnóstico, al 2026-10-22): 1,676,291 (1,124,045 por correo, 552,246 en persona) · registrados D 41.3% · R 38.2% · NPA 18.1% (correo D+6.7, en persona R+4.4). Es registro de partido, no intención de voto: no entra al pronóstico.

![Pronóstico](produccion/salidas/ultimo/pronostico.png)

![Evolución](produccion/salidas/evolucion.png)

Detalle: [`resumen.txt`](produccion/salidas/ultimo/resumen.txt) · [encuestas usadas](produccion/salidas/ultimo/encuestas_gobernador.csv) · [escenarios](produccion/salidas/ultimo/escenarios_gobernador.csv) · [voto anticipado por condado](produccion/salidas/ultimo/voto_anticipado_condados.csv) · [historial](produccion/salidas/historial_pronosticos.csv)
<!-- PRONOSTICO:FIN -->

GitHub Actions actualiza el bloque anterior dos veces al día ([flujo](../.github/workflows/pronostico_florida.yml)).

## Modelo general (elegido por backtest)
Base: el modelo V11 de Georgia. Se validó con un backtest *leave-one-year-out* de 848 contiendas (1998–2024, 23 de Florida) a 12 días de la elección, donde ganó el menor CRPS. Del modelo de la primaria de Florida no se adoptó nada: todas sus piezas empeoraron el error en la general.

| Pieza | Cómo entra | Por qué |
|---|---|---|
| Promedio de encuestas | V11: efecto de casa contraído (k = 8), √n, vida media de 14 días, cada firma pesa ~1 | Mejor CRPS nacional (3.374) |
| Sesgo estatal | **Sí**, contraído por Bayes empírico (vida media de 4 años): hoy −4.8 pp hacia Donalds | Las encuestas de FL sobreestimaron al demócrata en 19 de 23 contiendas (2022 Gob +8.2, 2024 Pres +6.6, Sen +8.4). Quitarlo sube el CRPS de FL de 2.200 a 2.643 (P = 0.06 de que quitarlo mejore). Sin contraer da 2.168 en FL pero empeora a nivel nacional (P = 0.03). Ambos quedan como escenario |
| Terceros | `real = 1.85 + 0.64 · (otros en encuestas)`, calibrado | El MAE del % de Jolly bajó de 2.10 a 1.49 en FL |
| Indecisos | 50/50 | La cuota R estimada (0.55) no mejora (2.209); el reparto de la primaria FIX v8 empeora (2.351) |
| σ | `√(τ² + s²/k)` calibrada a los días que faltan, t de Student, más una deriva de 0.25 pp/día si las encuestas son más viejas que ese horizonte | Cobertura del 80 % correcta en el backtest |
| Mercados | Promedio de **Kalshi y Polymarket**, mezcla logit con peso 0.30. La distribución del margen se desplaza para que P(margen > 0) sea igual a la probabilidad publicada | En FL los niveles se mueven juntos (0.86) pero los cambios diarios no (0.20). Peso estimado con 40 contiendas de 2024 ([detalle](../arizona/docs/03_peso_mercados.md)) |
| Recuento | P(\|margen\| ≤ 0.5 pp) | Recuento por máquina según la ley de FL |
| Voto ya emitido (civicAPI) | Diagnóstico, peso 0 | Es registro de partido, no intención de voto, y no hay histórico al mismo día para calibrarlo |

## Carpetas
| Carpeta | Contenido |
|---|---|
| [`produccion/`](produccion/) | Paquete `fl_pronostico`. Todas las fuentes en vivo: Wikipedia, 270toWin, Kalshi, Polymarket, civicAPI y FiveThirtyEight. Incluye CLI, pruebas sin red y tarea programada de Windows. Ver su README. |
| [`modelo_general/`](modelo_general/) | Notebook final ejecutado (corte 22-oct-2026), el módulo del modelo, datos y salidas |
| [`backtest/`](backtest/) | Backtest de variantes (Georgia V11, regla de Arizona, primaria de FL, H1–H8) y errores históricos de las encuestas en FL |
| [`docs/`](docs/) | Investigación del electorado (registro, primarias, voto ya emitido, indecisos), fuentes y decisiones del modelo |
