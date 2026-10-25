# Texas 2026 · Gobernador

Elección general del 3 de noviembre de 2026 entre **Greg Abbott (R, gobernador en funciones)** y **Gina Hinojosa (D, representante estatal por Austin)**, con Pat Dixon (libertario). Gana la mayoría simple.

<!-- PRONOSTICO:INICIO -->
Sin corrida automática todavía: el modelo está validado y empaquetado, pero el flujo de GitHub Actions no está activo. Pronóstico de referencia con las fuentes del 25-oct-2026 (pruebas sin red): **Abbott 51.2 % · Hinojosa 46.6 % · P(Hinojosa) 14.6 %** (margen −4.5, σ 4.4).
<!-- PRONOSTICO:FIN -->

## Modelo general (elegido por backtest)
Base: el modelo de Maine v1.1.0 (Pennsylvania / Nevada / Florida / Georgia V11). Se validó con un backtest *leave-one-year-out* de 945 contiendas (1998–2024, 20 de Texas) a 9 días de la elección, con la misma ventana que producción, más una validación estrictamente cronológica.

| Pieza | Cómo entra | Por qué |
|---|---|---|
| Promedio de encuestas | V11: efecto de casa contraído (k = 8), √n, vida media de 14 días, cada firma pesa ~1; ventana de 21 días, ampliada si hay menos de 2 encuestadoras | Mejor CRPS nacional (3.304) |
| Encuestadoras con varios nombres | Fox News = Beacon/Shaw, Texas A&M = ReconMR/Siena, UH Hobby = University of Houston, Cook = GS Strategy/New River, «YouGov» de 270toWin = CBS/YouGov | Conservan su efecto de casa; no se cuentan dos veces |
| Sesgo estatal | Contraído por Bayes empírico con todas las contiendas del estado: hoy se restan ~2.5 pp (las encuestas en TX sobreestimaron al demócrata en 14 de 20 contiendas, +7.2 en 2024) | Cronológico TX: empate con «sin sesgo» (2.306 vs 2.309), mejor que «k ≥ 2» (P = 0.07); nacional: gana con claridad (P = 0.002). «Sin sesgo» y «solo gobernador» se reportan siempre |
| Encuestas partidistas | Con su efecto de casa; «sin partidistas» es escenario | Excluirlas mejora en TX (P = 0.98) pero es lo peor a nivel nacional (P = 0.000) |
| Terceros (Dixon) | `real = a + c·(otros en las encuestas que los reportan)` | Mejor regla nacional; en TX el libertario se desinfla ~1 pp |
| Indecisos | 50/50 | El reparto proporcional es el peor en TX y a nivel nacional |
| σ | `√(τ² + s²/k)` calibrada a los días que faltan, t de Student, más una deriva de 0.25 pp/día si las encuestas son más viejas que ese horizonte | Cobertura del 80 % correcta en el backtest |
| Mercados | Promedio de **Kalshi y Polymarket**, mezcla logit con peso 0.30 | Peso estimado con 40 contiendas de 2024 ([detalle](../arizona/docs/03_peso_mercados.md)) |
| Resultado muy estrecho | P(\|margen\| ≤ 0.5 pp) | Texas no tiene recuento automático (lo pide un candidato) |
| Voto anticipado (civicAPI) | Diagnóstico, peso 0; solo volumen por condado | Texas no tiene registro partidario |

## Carpetas
| Carpeta | Contenido |
|---|---|
| [`produccion/`](produccion/) | Paquete `tx_pronostico`. Todas las fuentes en vivo: Wikipedia, 270toWin, Kalshi, Polymarket, civicAPI y FiveThirtyEight. Incluye CLI, pruebas sin red y tarea programada de Windows |
| [`backtest/`](backtest/) | Backtest de variantes (sesgo estatal, indecisos, encuestas partidistas, terceros) y validación cronológica del sesgo (todas, k ≥ 2, por cargo) |
| [`docs/`](docs/) | Investigación del electorado (voto anticipado, subgrupos, indecisos), contexto, fuentes y decisiones del modelo |
