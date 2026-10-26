# Illinois 2026 · Gobernador

Elección general del 3 de noviembre de 2026 entre **JB Pritzker (D, gobernador en funciones)** y **Darren Bailey (R)**, revancha de 2022, con Collin Corbett (independiente). Gana la mayoría simple.

<!-- PRONOSTICO:INICIO -->
**Pronóstico al 2026-10-25** (9 días a la elección) · actualizado automáticamente 2026-10-25 21:37 CT · fuentes en vivo 8/8

| Gobernador | % de voto (IC80) | Probabilidad de ganar |
|---|---|---|
| JB **Pritzker** (D, gobernador) | **56.2%** (52.0–60.5) | **99%** |
| Darren **Bailey** (R) | **38.6%** (34.3–42.8) | **1%** |
| Terceros (Collin Corbett, I; otros) | 5.2% (3.0–7.3) | — |

Margen D−R +17.6 pp (σ 6.6) · solo encuestas: P(Pritzker) >99% · Kalshi 96% · Polymarket 97% (peso de mercados 0.3) · resultado muy estrecho (|margen| ≤ 0.5) 0.2% · 2 encuestas, 2 encuestadoras en la ventana

Cómo se llega: promedio de encuestas +18.7 · sesgo estatal de Illinois +1.2 · mercados -2.2

**Encuesta más reciente:** ActiVote, terminó el 2026-10-22 (**3 días** antes del corte). Las fuentes se consultan en vivo, pero el promedio solo puede ser tan reciente como la última encuesta publicada.

**Voto anticipado ya emitido** (civicAPI, diagnóstico, al 2026-10-25): 786,257 (342,424 en persona, 443,833 por correo) · 19 % del total de votos de 2022. Illinois no tiene registro partidario: es solo volumen, no indica el resultado y no entra al pronóstico.

![Pronóstico](produccion/salidas/ultimo/pronostico.png)

![Evolución](produccion/salidas/evolucion.png)

Detalle: [`resumen.txt`](produccion/salidas/ultimo/resumen.txt) · [encuestas usadas](produccion/salidas/ultimo/encuestas_gobernador.csv) · [escenarios](produccion/salidas/ultimo/escenarios_gobernador.csv) · [voto anticipado por condado](produccion/salidas/ultimo/voto_anticipado_condados.csv) · [historial](produccion/salidas/historial_pronosticos.csv)
<!-- PRONOSTICO:FIN -->

GitHub Actions actualiza el bloque anterior dos veces al día ([flujo](../.github/workflows/pronostico_illinois.yml)).

## Modelo general (elegido por backtest)
Base: el modelo de Texas v1.1.0 (Maine / Pennsylvania / Nevada / Florida / Georgia V11). Se validó con un backtest *leave-one-year-out* de 945 contiendas (1998–2024, 19 de Illinois) a 9 días de la elección, con la misma ventana que producción, más una validación estrictamente cronológica.

| Pieza | Cómo entra | Por qué |
|---|---|---|
| Promedio de encuestas | V11: efecto de casa contraído (k = 8), √n, vida media de 14 días, cada firma pesa ~1; ventana de 21 días, **ampliada hoy** (solo 2 encuestas: PPP y ActiVote) | Mejor CRPS nacional (3.304); ampliar es mejor que no ampliar (3.397 vs 3.670) |
| Identidad de las encuestas | Firma + periodo de campo; la fecha puntual de 270toWin es de publicación | Revisión de Texas del 25-oct |
| Sesgo estatal | Contraído por Bayes empírico con todas las contiendas del estado: hoy **suma** ~1.2 pp al demócrata | Cronológico IL: no significativo (sin sesgo P = 0.63); nacional: gana con claridad (P = 0.002); desde 2016 gana en IL |
| Terceros (Corbett) | `real = a + c·(otros en las encuestas que los reportan)` | Mejor regla en IL y a nivel nacional |
| Indecisos | 50/50 | El reparto proporcional es el peor en IL y a nivel nacional |
| Ventajas grandes | Sin ajuste de escala | b = 1.00 fuera de muestra; ajustar empeora (P = 0.13 en ventajas ≥ 15 pp) |
| σ | `√(τ² + s²/k)` calibrada a los días que faltan, t de Student, más una deriva de 0.25 pp/día | Cobertura del 80 % correcta en el backtest |
| Mercados | Promedio de **Kalshi y Polymarket**, mezcla logit con peso 0.30 | Peso estimado con 40 contiendas de 2024 ([detalle](../arizona/docs/03_peso_mercados.md)). Con probabilidades cercanas a 1 baja el margen (−2.2 pp): «sin mercados» y Polymarket por rangos son lecturas igual de defendibles |
| Voto anticipado (civicAPI) | Diagnóstico, peso 0; solo volumen por condado y ciudad | Illinois no tiene registro partidario |

## Carpetas
| Carpeta | Contenido |
|---|---|
| [`produccion/`](produccion/) | Paquete `il_pronostico`. Todas las fuentes en vivo: Wikipedia, 270toWin, Kalshi, Polymarket, civicAPI y FiveThirtyEight. Incluye CLI, pruebas sin red y tarea programada de Windows |
| [`backtest/`](backtest/) | Backtest de variantes (sesgo estatal, indecisos, encuestas partidistas, terceros), validación cronológica del sesgo, ventana ampliada y escala de ventajas grandes |
| [`docs/`](docs/) | Investigación del electorado (voto anticipado por región, indecisos), contexto, fuentes y decisiones del modelo |
