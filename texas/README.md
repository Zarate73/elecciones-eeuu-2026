# Texas 2026 · Gobernador

Elección general del 3 de noviembre de 2026 entre **Greg Abbott (R, gobernador en funciones)** y **Gina Hinojosa (D, representante estatal por Austin)**, con Pat Dixon (libertario). Gana la mayoría simple.

<!-- PRONOSTICO:INICIO -->
**Pronóstico al 2026-10-27** (7 días a la elección) · actualizado automáticamente 2026-10-27 11:36 CT · fuentes en vivo 8/8

| Gobernador | % de voto (IC80) | Probabilidad de ganar |
|---|---|---|
| Gina **Hinojosa** (D) | **46.8%** (43.9–49.6) | **15%** |
| Greg **Abbott** (R, gobernador) | **51.1%** (48.3–53.9) | **85%** |
| Terceros (Pat Dixon, L; otros) | 2.1% (0.1–4.1) | — |

Margen D−R -4.3 pp (σ 4.2) · solo encuestas: P(Hinojosa) 10% · Kalshi 33% · Polymarket 34% (peso de mercados 0.3) · resultado muy estrecho (|margen| ≤ 0.5) 5.4% · 53 encuestas, 11 encuestadoras en la ventana

Cómo se llega: promedio de encuestas -2.9 · sesgo estatal de Texas -2.5 · mercados +1.1

**Encuesta más reciente:** N+ Univision, terminó el 2026-10-27 (**0 días** antes del corte). Las fuentes se consultan en vivo, pero el promedio solo puede ser tan reciente como la última encuesta publicada.

**Voto anticipado ya emitido** (civicAPI, diagnóstico, al 2026-10-27): 4,949,614 (4,734,516 en persona, 215,098 por correo) · 61 % del total de votos de 2022. Texas no tiene registro partidario: es solo volumen, no indica el resultado y no entra al pronóstico.

![Pronóstico](produccion/salidas/ultimo/pronostico.png)

![Evolución](produccion/salidas/evolucion.png)

Detalle: [`resumen.txt`](produccion/salidas/ultimo/resumen.txt) · [encuestas usadas](produccion/salidas/ultimo/encuestas_gobernador.csv) · [escenarios](produccion/salidas/ultimo/escenarios_gobernador.csv) · [voto anticipado por condado](produccion/salidas/ultimo/voto_anticipado_condados.csv) · [historial](produccion/salidas/historial_pronosticos.csv)
<!-- PRONOSTICO:FIN -->

GitHub Actions actualiza el bloque anterior dos veces al día ([flujo](../.github/workflows/pronostico_texas.yml)).

## Modelo general (elegido por backtest)
Base: el modelo de Maine v1.1.0 (Pennsylvania / Nevada / Florida / Georgia V11). El componente de encuestas se validó con un backtest *leave-one-year-out* de 945 contiendas (1998–2024, 20 de Texas) a 9 días de la elección, con la misma ventana que producción, más una validación estrictamente cronológica.

| Pieza | Cómo entra | Por qué |
|---|---|---|
| Promedio de encuestas | V11: efecto de casa contraído (k = 8), √n, vida media de 14 días, cada firma pesa ~1; ventana de 21 días, ampliada si hay menos de 2 encuestadoras | Mejor CRPS nacional (3.304) |
| Identidad de las encuestas | Firma + periodo de campo; la fecha puntual de 270toWin es de publicación | Revisión del 25-oct ([detalle](docs/02_revision_externa_2026-10-25.md)) |
| Encuestadoras con varios nombres | Fox News = Beacon/Shaw, Texas A&M = ReconMR/Siena, UH Hobby = University of Houston, Cook = GS Strategy/New River, «YouGov» de 270toWin = CBS/YouGov | Conservan su efecto de casa; no se cuentan dos veces |
| Sesgo estatal | Contraído por Bayes empírico con todas las contiendas del estado: hoy se restan ~2.5 pp (las encuestas en TX sobreestimaron al demócrata en 14 de 20 contiendas, +7.2 en 2024) | Cronológico TX: empate con «sin sesgo» (2.306 vs 2.309), mejor que «k ≥ 2» (P = 0.07); nacional: mejor en la prueba por contienda (P = 0.002), no concluyente con bootstrap por año (ver «Qué valida»). «Sin sesgo» y «solo gobernador» se reportan siempre |
| Encuestas partidistas | Con su efecto de casa; «sin partidistas» es escenario | Excluirlas mejora en TX (P = 0.98) pero es lo peor a nivel nacional (P = 0.000) |
| Terceros (Dixon) | `real = a + c·(otros en las encuestas que los reportan)` | Mejor regla nacional; en TX el libertario se desinfla ~1 pp |
| Indecisos | 50/50 | El reparto proporcional es el peor en TX y a nivel nacional |
| σ | `√(τ² + s²/k)` calibrada a los días que faltan, t de Student, más una deriva de 0.25 pp/día si las encuestas son más viejas que ese horizonte | Cobertura del 80 % correcta en el backtest |
| Mercados | Promedio de **Kalshi y Polymarket**, mezcla logit con peso 0.30 | Peso estimado con 40 contiendas de 2024 ([detalle](../arizona/docs/03_peso_mercados.md)) |
| Resultado muy estrecho | P(\|margen\| ≤ 0.5 pp) | Texas no tiene recuento automático (lo pide un candidato) |
| Voto anticipado (civicAPI) | Diagnóstico, peso 0; solo volumen por condado | Texas no tiene registro partidario |

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
| [`produccion/`](produccion/) | Paquete `tx_pronostico`. Todas las fuentes en vivo: Wikipedia, 270toWin, Kalshi, Polymarket, civicAPI y FiveThirtyEight. Incluye CLI, pruebas sin red y tarea programada de Windows |
| [`backtest/`](backtest/) | Backtest de variantes (sesgo estatal, indecisos, encuestas partidistas, terceros) y validación cronológica del sesgo (todas, k ≥ 2, por cargo) |
| [`docs/`](docs/) | Investigación del electorado (voto anticipado, subgrupos, indecisos), contexto, fuentes y decisiones del modelo |
