# Nevada 2026 · Gobernador

Elección general del 3 de noviembre de 2026 entre **Aaron Ford (D, fiscal general)** y **Joe Lombardo (R, gobernador en funciones)**. En la boleta también aparecen Danielle Ford (independiente) y la opción «None of these candidates».

<!-- PRONOSTICO:INICIO -->
**Pronóstico al 2026-10-31** (3 días a la elección) · actualizado automáticamente 2026-10-31 10:24 PT · fuentes en vivo 8/8

| Gobernador | % de voto (IC80) | Probabilidad de ganar |
|---|---|---|
| Aaron **Ford** (D) | **48.6%** (45.1–52.0) | **65%** |
| Joe **Lombardo** (R, gobernador) | **46.6%** (43.2–50.0) | **35%** |
| Terceros | 4.8% (2.8–6.9) | — |

Margen D−R +2.0 pp (σ 5.2) · solo encuestas: P(Ford) 60% · Kalshi 76% · Polymarket 78% (peso de mercados 0.3) · resultado muy estrecho (|margen| ≤ 0.5) 7.2% · 12 encuestas, 4 encuestadoras en la ventana

Cómo se llega: promedio de encuestas +1.8 · sesgo estatal de Nevada -0.6 · mercados +0.7

**Encuesta más reciente:** Noble Predictive Insights, terminó el 2026-10-28 (**3 días** antes del corte). Las fuentes se consultan en vivo, pero el promedio solo puede ser tan reciente como la última encuesta publicada.

**Voto ya emitido** (civicAPI, diagnóstico, al 2026-10-30): 688,777 (380,971 por correo, 307,806 en persona) · registrados D 39.5% · R 34.2% · otros e independientes 26.3% (correo D+11.8, en persona R+2.8). Es registro de partido, no intención de voto: no entra al pronóstico.

![Pronóstico](produccion/salidas/ultimo/pronostico.png)

![Evolución](produccion/salidas/evolucion.png)

Detalle: [`resumen.txt`](produccion/salidas/ultimo/resumen.txt) · [encuestas usadas](produccion/salidas/ultimo/encuestas_gobernador.csv) · [escenarios](produccion/salidas/ultimo/escenarios_gobernador.csv) · [voto anticipado por condado](produccion/salidas/ultimo/voto_anticipado_condados.csv) · [historial](produccion/salidas/historial_pronosticos.csv)
<!-- PRONOSTICO:FIN -->

GitHub Actions actualiza el bloque anterior dos veces al día ([flujo](../.github/workflows/pronostico_nevada.yml)).

## Modelo general (elegido por backtest)
Base: el modelo de Florida v1.1.0 (Georgia V11). El componente de encuestas se validó con un backtest *leave-one-year-out* de 848 contiendas (1998–2024, 23 de Nevada) a 12 días de la elección, con la misma ventana que producción, más una validación estrictamente cronológica.

| Pieza | Cómo entra | Por qué |
|---|---|---|
| Promedio de encuestas | V11: efecto de casa contraído (k = 8), √n, vida media de 14 días, cada firma pesa ~1; ventana de 21 días, ampliada si hay menos de 2 encuestadoras | Mejor CRPS nacional (3.375) |
| Sesgo estatal | Contraído por Bayes empírico: hoy +0.58 pp pro-D (pequeño) | En NV el error cambia de signo entre ciclos (8 de 23 contiendas pro-D, autocorrelación −0.11). Con todas las contiendas, quitarlo parece mejor (3.265 vs 3.321, P = 0.62), pero solo por 2014 (una encuestadora, error +22.8): sin 2014 el sesgo gana (2.521 vs 2.585; cronológico 2.443 vs 2.572, P = 0.23). «Sin sesgo» se reporta siempre |
| Encuestas internas de campaña | Con su efecto de casa; el ajuste por patrocinador queda como escenario | Descartarlas, pesarlas a la mitad o ajustarlas por patrocinador empeora el CRPS en NV (P ≤ 0.006) |
| Terceros | `real = a + c·(otros en las encuestas que los reportan)`; si ninguna los reporta, media histórica. Incluye a Danielle Ford y «None of these candidates» | Calibrado con el resultado real (100 − D − R) |
| Indecisos | 50/50 | El reparto proporcional gana en NV (3.166) pero es el peor a nivel nacional (3.650, P = 0.000): sería sobreajuste |
| σ | `√(τ² + s²/k)` calibrada a los días que faltan, t de Student, más una deriva de 0.25 pp/día si las encuestas son más viejas que ese horizonte | Cobertura del 80 % correcta en el backtest |
| Mercados | Promedio de **Kalshi y Polymarket**, mezcla logit con peso 0.30; la distribución del margen se desplaza para que P(margen > 0) sea la probabilidad publicada | En NV no son el mismo precio (cambios diarios con correlación −0.03). Peso estimado con 40 contiendas de 2024 ([detalle](../arizona/docs/03_peso_mercados.md)) |
| Resultado muy estrecho | P(\|margen\| ≤ 0.5 pp) | NV no tiene recuento automático (lo puede pedir un candidato) |
| Escenarios | Cruce 2 × 2 de sesgo × mercados. Influencia de cada encuesta (se quita y se reconstruye la ventana; sin GSG, P(Ford) sube de 42 % a 50 %). Sesgo sin contiendas de una sola encuestadora. Terceros con reducción moderada y pronunciada. Peso de mercados 0.15 y 0.50 | Revisión externa del 22-oct ([detalle](docs/02_revision_externa_2026-10-22.md)) |
| Voto ya emitido (civicAPI) | Diagnóstico, peso 0 | Es registro de partido, no intención de voto; el 39 % del padrón es no partidista |

## Qué valida y qué no valida el backtest

*Auditoría transversal del 26-oct-2026 (T4, T7). Detalle en [`docs/auditoria_2026-10-26.md`](../docs/auditoria_2026-10-26.md).*

- **Qué valida.** El backtest *leave-one-year-out* sobre el histórico de FiveThirtyEight + 2024 valida el **componente de encuestas** (promedio, efectos de casa, sesgo estatal) y su distribución de error (τ, s, ν). El número de contiendas depende del horizonte: con el corte de la corrida del 25/26-oct (9 días) la calibración de producción usa **945 contiendas**.
- **Qué no valida.** No es un backtest del pronóstico final que mezcla Kalshi/Polymarket con peso `w = 0.30`. Ese peso se estudió aparte con **40 contiendas de 2024** (un solo ciclo, con errores correlacionados): `w` de máxima verosimilitud 0.65 sin sesgo común y 0.25 con sesgo común libre (IC95 0–0.65). `w = 0.30` es compatible con ambos, no una validación entre ciclos. Ver [`arizona/docs/03_peso_mercados.md`](../arizona/docs/03_peso_mercados.md).
- **Margen y ganador son cosas distintas.** CRPS y MAE miden el margen; Brier y log score, el ganador. Una variante puede mejorar uno y no el otro.
- **Significancia.** Los valores P de esta página y de `docs/` comparan variantes **contienda por contienda**, como si las contiendas de un mismo año fueran independientes. Con bootstrap **por año** (26 años, 4,000 réplicas, 945 contiendas), la corrección por sesgo estatal mejora el CRPS nacional en −0.134, pero con IC95 [−0.320, +0.051], que incluye el cero (fracción de réplicas con empeoramiento: 0.077), y el Brier no cambia (+0.0009, IC95 [−0.004, +0.006]). La mejora observada es real en la muestra; la evidencia no alcanza para afirmar una ventaja robusta al 95 % entre ciclos. Se mantiene la regla vigente: se fijó antes de la elección y no se cambia con estos datos.
- **Fechas del histórico (T1).** FiveThirtyEight fecha cada encuesta en la mediana de su campo; producción usa el cierre. Recalibrar suponiendo que cada encuesta histórica estuvo disponible 2–4 días después de su mediana **no ensancha σ** (baja 0.1–0.3 pp; ν baja de 19.5 a ~13): no hay evidencia para aumentar la incertidumbre.

## Carpetas
| Carpeta | Contenido |
|---|---|
| [`produccion/`](produccion/) | Paquete `nv_pronostico`. Todas las fuentes en vivo: Wikipedia, 270toWin, Kalshi, Polymarket, civicAPI y FiveThirtyEight. Incluye CLI, pruebas sin red y tarea programada de Windows |
| [`backtest/`](backtest/) | Backtest de variantes (sesgo estatal, indecisos, encuestas internas, terceros) y errores históricos de las encuestas en NV |
| [`docs/`](docs/) | Investigación del electorado (registro, no partidistas, voto anticipado, indecisos), fuentes y decisiones del modelo |
