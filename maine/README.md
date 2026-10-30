# Maine 2026 · Gobernador

Elección general del 3 de noviembre de 2026 entre **Hannah Pingree (D, ex presidenta de la Cámara estatal)** y **Bobby Charles (R)**, con **Rick Bennett (independiente)**. Elección abierta: Janet Mills no puede reelegirse. Gana la mayoría simple: la general de gobernador no usa voto preferencial.

<!-- PRONOSTICO:INICIO -->
**Pronóstico al 2026-10-30** (4 días a la elección) · actualizado automáticamente 2026-10-30 12:45 ET · fuentes en vivo 8/8

| Gobernador | % de voto (IC80) | Probabilidad de ganar |
|---|---|---|
| Hannah **Pingree** (D) | **50.0%** (46.6–53.5) | **91%** |
| Bobby **Charles** (R) | **43.2%** (39.8–46.6) | **9%** |
| Terceros (Rick Bennett, I) | 6.8% (4.7–8.8) | — |

Margen D−R +6.9 pp (σ 5.2) · solo encuestas: P(Pingree) 88% · Kalshi 95% · Polymarket 96% (peso de mercados 0.3) · resultado muy estrecho (|margen| ≤ 0.5) 3.0% · 19 encuestas, 4 encuestadoras en la ventana

Cómo se llega: promedio de encuestas +7.5 · sesgo estatal de Maine -1.5 · mercados +0.9

**Con independiente** (mayoría simple): P(Pingree gana) 91% · P(Bennett u otro tercero gana) en el modelo 0% (cota: los terceros se simulan como un total) · en los mercados Kalshi 1% y Polymarket 2%. La probabilidad de los mercados que entra a la mezcla es D / (D + R), condicional a que gane un partido principal.

**Encuesta más reciente:** SSRS, terminó el 2026-10-26 (**4 días** antes del corte). Las fuentes se consultan en vivo, pero el promedio solo puede ser tan reciente como la última encuesta publicada.

**Voto ausente ya emitido** (civicAPI, diagnóstico, al 2026-10-29): 275,559 (123,261 por correo, 152,298 en persona) · registrados D 47.5% · R 22.6% · no inscritos y otros 29.9%. Es registro de partido, no intención de voto, y el voto ausente es más demócrata que el electorado: no entra al pronóstico.

![Pronóstico](produccion/salidas/ultimo/pronostico.png)

![Evolución](produccion/salidas/evolucion.png)

Detalle: [`resumen.txt`](produccion/salidas/ultimo/resumen.txt) · [encuestas usadas](produccion/salidas/ultimo/encuestas_gobernador.csv) · [escenarios](produccion/salidas/ultimo/escenarios_gobernador.csv) · [voto ausente por municipio](produccion/salidas/ultimo/voto_anticipado_condados.csv) · [historial](produccion/salidas/historial_pronosticos.csv)
<!-- PRONOSTICO:FIN -->

GitHub Actions actualiza el bloque anterior dos veces al día ([flujo](../.github/workflows/pronostico_maine.yml)).

## Modelo general (elegido por backtest)
Base: el modelo de Pennsylvania v1.1.0 (Nevada / Florida / Georgia V11). El componente de encuestas se validó con un backtest *leave-one-year-out* de 923 contiendas (1998–2024, 13 de Maine) a 10 días de la elección, con la misma ventana que producción, más una validación estrictamente cronológica.

| Pieza | Cómo entra | Por qué |
|---|---|---|
| Promedio de encuestas | V11: efecto de casa contraído (k = 8), √n, vida media de 14 días, cada firma pesa ~1; ventana de 21 días, ampliada si hay menos de 2 encuestadoras | Mejor CRPS nacional (3.388) |
| Encuestadoras con varios nombres | Fox News = Beacon/Shaw, AARP = Fabrizio Ward/Impact, CNN = SSRS, NYT/PPH = Siena: se unifican con la clave del histórico de FiveThirtyEight. Las bipartidistas no se tratan como partidistas | Conservan su efecto de casa |
| Sesgo estatal | Contraído por Bayes empírico y **estimado sin contiendas de una sola encuestadora**: hoy se restan ~2.4 pp (las encuestas en Maine sobreestimaron al demócrata en 8 de 13 contiendas) | Con sesgo 3.32 vs sin sesgo 3.52 (cronológico, prueba por contienda P = 0.014). Sin contiendas k = 1 mejora en ME (P = 0.99) y a nivel nacional (P = 0.74); estimarlo por cargo empeora. «Con todas las contiendas» se reporta siempre |
| Independiente (Bennett) | `real = a + c·(otros en las encuestas que los reportan)`; un careo forzado sin Bennett cuenta como «no reportado» | En 139 contiendas con terceros ≥ 5 % el tercero se desinfla 1.1 pp y la regla ya lo corrige; ese voto no va claramente a ningún lado |
| Indecisos | 50/50 | El reparto proporcional es el peor en ME y a nivel nacional |
| σ | `√(τ² + s²/k)` calibrada a los días que faltan, t de Student, más una deriva de 0.25 pp/día si las encuestas son más viejas que ese horizonte | Cobertura del 80 % correcta en el backtest |
| Mercados | Promedio de **Kalshi y Polymarket**, mezcla logit con peso 0.30. Kalshi tiene un contrato de Bennett: se usa D / (D + R) | Peso estimado con 40 contiendas de 2024 ([detalle](../arizona/docs/03_peso_mercados.md)) |
| Resultado muy estrecho | P(\|margen\| ≤ 0.5 pp) | Maine no tiene recuento automático (lo pide un candidato) |
| Escenarios | Cruce 2 × 2 de sesgo × mercados, sesgo con todas las contiendas, influencia de cada encuesta, terceros con reducción, peso de mercados 0.15/0.50, **k efectivo y deriva por antigüedad ponderada** (ventana ampliada), Polymarket por rangos (condicional a que gane un partido principal) | Revisión del 24-oct ([detalle](docs/02_revision_externa_2026-10-24.md)) |
| Probabilidad con independiente | P(gana) exige superar a R y a los terceros; se reporta una cota de P(gana un tercero) y las probabilidades de Bennett de Kalshi y Polymarket | Mayoría simple sin voto preferencial |
| Voto ausente (civicAPI) | Diagnóstico, peso 0 | Es registro de partido; un tercio del padrón no está inscrito |

## Qué valida y qué no valida el backtest

*Auditoría transversal del 26-oct-2026 (T4, T7). Detalle en [`docs/auditoria_2026-10-26.md`](../docs/auditoria_2026-10-26.md).*

- **Qué valida.** El backtest *leave-one-year-out* sobre el histórico de FiveThirtyEight + 2024 valida el **componente de encuestas** (promedio, efectos de casa, sesgo estatal) y su distribución de error (τ, s, ν). El número de contiendas depende del horizonte: con el corte de la corrida del 25/26-oct (9 días) la calibración de producción usa **945 contiendas**.
- **Qué no valida.** No es un backtest del pronóstico final que mezcla Kalshi/Polymarket con peso `w = 0.30`. Ese peso se estudió aparte con **40 contiendas de 2024** (un solo ciclo, con errores correlacionados): `w` de máxima verosimilitud 0.65 sin sesgo común y 0.25 con sesgo común libre (IC95 0–0.65). `w = 0.30` es compatible con ambos, no una validación entre ciclos. Ver [`arizona/docs/03_peso_mercados.md`](../arizona/docs/03_peso_mercados.md).
- **Margen y ganador son cosas distintas.** CRPS y MAE miden el margen; Brier y log score, el ganador. Una variante puede mejorar uno y no el otro.
- **Significancia.** Los valores P de esta página y de `docs/` comparan variantes **contienda por contienda**, como si las contiendas de un mismo año fueran independientes. Con bootstrap **por año** (26 años, 4,000 réplicas, 945 contiendas), la corrección por sesgo estatal mejora el CRPS nacional en −0.134, pero con IC95 [−0.320, +0.051], que incluye el cero (fracción de réplicas con empeoramiento: 0.077), y el Brier no cambia (+0.0009, IC95 [−0.004, +0.006]). La mejora observada es real en la muestra; la evidencia no alcanza para afirmar una ventaja robusta al 95 % entre ciclos. Se mantiene la regla vigente: se fijó antes de la elección y no se cambia con estos datos.
- **Fechas del histórico (T1).** FiveThirtyEight fecha cada encuesta en la mediana de su campo; producción usa el cierre. Recalibrar suponiendo que cada encuesta histórica estuvo disponible 2–4 días después de su mediana **no ensancha σ** (baja 0.1–0.3 pp; ν baja de 19.5 a ~13): no hay evidencia para aumentar la incertidumbre.

### Sensibilidad de Maine a la fecha de disponibilidad (T1)

Maine es el estado donde más se mueve el sesgo estatal. Corte del 25-oct, mismas cachés de encuestas y mercados, misma semilla; solo cambia `L`, el supuesto de días entre la mediana del campo y la disponibilidad de cada encuesta histórica (FiveThirtyEight no da fecha de publicación: `L` es una aproximación, no una fecha reconstruida). **El pronóstico oficial es `L = 0`; `L = 3` y `L = 4` son sensibilidades.**

| L (días) | Contiendas | τ / s / ν | Corrección estatal al margen D−R (pp) | σ (pp) | Margen final D−R | P(D) |
|---:|---:|---|---:|---:|---:|---:|
| 0 | 945 | 3.60 / 7.70 / 19.5 | −3.67 | 4.81 | +7.17 | 93.4 % |
| 3 | 849 | 3.40 / 7.60 / 13.5 | −2.57 | 4.63 | +7.83 | 95.5 % |
| 4 | 821 | 3.20 / 7.80 / 12.9 | −2.53 | 4.54 | +7.80 | 95.8 % |

La corrección es negativa porque las encuestas de Maine sobreestimaron al demócrata (sesgo estimado positivo, que se resta del margen). Con `L = 3–4` la corrección baja ~1.1 pp y P(D) sube unos 2 puntos. Reproducible con `scripts/auditoria/maine_sensibilidad_temporal.py`.

## Carpetas
| Carpeta | Contenido |
|---|---|
| [`produccion/`](produccion/) | Paquete `me_pronostico`. Todas las fuentes en vivo: Wikipedia, 270toWin, Kalshi, Polymarket, civicAPI y FiveThirtyEight. Incluye CLI, pruebas sin red y tarea programada de Windows |
| [`backtest/`](backtest/) | Backtest de variantes (sesgo estatal, indecisos, encuestas internas, terceros e independiente fuerte) y prueba de dónde estimar el sesgo |
| [`docs/`](docs/) | Investigación del electorado (registro, voto ausente, independiente, indecisos), contexto, fuentes y decisiones del modelo |
