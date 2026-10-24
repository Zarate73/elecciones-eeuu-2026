# Maine 2026 · Gobernador

Elección general del 3 de noviembre de 2026 entre **Hannah Pingree (D, ex presidenta de la Cámara estatal)** y **Bobby Charles (R)**, con **Rick Bennett (independiente)**. Elección abierta: Janet Mills no puede reelegirse. Gana la mayoría simple: la general de gobernador no usa voto preferencial.

<!-- PRONOSTICO:INICIO -->
Pendiente de la primera corrida automática.
<!-- PRONOSTICO:FIN -->

GitHub Actions actualiza el bloque anterior dos veces al día ([flujo](../.github/workflows/pronostico_maine.yml)).

## Modelo general (elegido por backtest)
Base: el modelo de Pennsylvania v1.1.0 (Nevada / Florida / Georgia V11). Se validó con un backtest *leave-one-year-out* de 923 contiendas (1998–2024, 13 de Maine) a 10 días de la elección, con la misma ventana que producción, más una validación estrictamente cronológica.

| Pieza | Cómo entra | Por qué |
|---|---|---|
| Promedio de encuestas | V11: efecto de casa contraído (k = 8), √n, vida media de 14 días, cada firma pesa ~1; ventana de 21 días, ampliada si hay menos de 2 encuestadoras | Mejor CRPS nacional (3.388) |
| Encuestadoras con varios nombres | Fox News = Beacon/Shaw, AARP = Fabrizio Ward/Impact, CNN = SSRS, NYT/PPH = Siena: se unifican con la clave del histórico de FiveThirtyEight. Las bipartidistas no se tratan como partidistas | Conservan su efecto de casa |
| Sesgo estatal | Contraído por Bayes empírico y **estimado sin contiendas de una sola encuestadora**: hoy se restan ~2.4 pp (las encuestas en Maine sobreestimaron al demócrata en 8 de 13 contiendas) | Con sesgo 3.32 vs sin sesgo 3.52 (cronológico P = 0.014). Sin contiendas k = 1 mejora en ME (P = 0.99) y a nivel nacional (P = 0.74); estimarlo por cargo empeora. «Con todas las contiendas» se reporta siempre |
| Independiente (Bennett) | `real = a + c·(otros en las encuestas que los reportan)`; un careo forzado sin Bennett cuenta como «no reportado» | En 139 contiendas con terceros ≥ 5 % el tercero se desinfla 1.1 pp y la regla ya lo corrige; ese voto no va claramente a ningún lado |
| Indecisos | 50/50 | El reparto proporcional es el peor en ME y a nivel nacional |
| σ | `√(τ² + s²/k)` calibrada a los días que faltan, t de Student, más una deriva de 0.25 pp/día si las encuestas son más viejas que ese horizonte | Cobertura del 80 % correcta en el backtest |
| Mercados | Promedio de **Kalshi y Polymarket**, mezcla logit con peso 0.30. Kalshi tiene un contrato de Bennett: se usa D / (D + R) | Peso estimado con 40 contiendas de 2024 ([detalle](../arizona/docs/03_peso_mercados.md)) |
| Resultado muy estrecho | P(\|margen\| ≤ 0.5 pp) | Maine no tiene recuento automático (lo pide un candidato) |
| Escenarios | Cruce 2 × 2 de sesgo × mercados, sesgo con todas las contiendas, influencia de cada encuesta, terceros con reducción, peso de mercados 0.15/0.50, Polymarket por rangos (con «gana un independiente») | Igual que Pennsylvania |
| Voto ausente (civicAPI) | Diagnóstico, peso 0 | Es registro de partido; un tercio del padrón no está inscrito |

## Carpetas
| Carpeta | Contenido |
|---|---|
| [`produccion/`](produccion/) | Paquete `me_pronostico`. Todas las fuentes en vivo: Wikipedia, 270toWin, Kalshi, Polymarket, civicAPI y FiveThirtyEight. Incluye CLI, pruebas sin red y tarea programada de Windows |
| [`backtest/`](backtest/) | Backtest de variantes (sesgo estatal, indecisos, encuestas internas, terceros e independiente fuerte) y prueba de dónde estimar el sesgo |
| [`docs/`](docs/) | Investigación del electorado (registro, voto ausente, independiente, indecisos), contexto, fuentes y decisiones del modelo |
