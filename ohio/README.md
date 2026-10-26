# Ohio 2026 · Gobernador

Elección general del 3 de noviembre de 2026 entre **Amy Acton (D, exdirectora de Salud del estado)** y **Vivek Ramaswamy (R)**, con Don Kissick (Libertario). El gobernador Mike DeWine (R) deja el cargo por límite de mandatos. Gana la mayoría simple.

<!-- PRONOSTICO:INICIO -->
Sin corrida automática todavía: el modelo está validado y empaquetado, pero el flujo de GitHub Actions no está activo. Pronóstico de referencia con las fuentes del 26-oct-2026 (pruebas sin red): **Acton 48.7 % · Ramaswamy 48.1 % · P(Acton) 55.0 %** (margen +0.6, σ 4.8; solo encuestas 40.8 %; Kalshi y Polymarket ~82 %).
<!-- PRONOSTICO:FIN -->

## Modelo general (elegido por backtest)
Base: el modelo de Nueva York v1.1.0 e Illinois v1.1.0 (Texas / Maine / Pennsylvania / Nevada / Florida / Georgia V11). Se validó con un backtest *leave-one-year-out* de 957 contiendas (1998–2024, 24 de Ohio) a 8 días de la elección, con la misma ventana que producción, más una validación estrictamente cronológica.

| Pieza | Cómo entra | Por qué |
|---|---|---|
| Promedio de encuestas | V11: efecto de casa contraído (k = 8), √n, vida media de 14 días, cada firma pesa ~1; ventana de 21 días (hoy, 6 encuestadoras) | Mejor CRPS nacional (3.249) |
| Identidad de las encuestas | Firma + periodo de campo; NYT/Siena, SSRS, Beacon/Shaw y BGSU con sus alias; cifras y n de la publicación original (Marist LV 50–43, ActiVote 48.6–51.4) | Conservan su efecto de casa y sus cifras |
| Sesgo estatal | Contraído por Bayes empírico con todas las contiendas del estado: hoy **resta** ~4.0 pp | Las encuestas sobreestimaron al demócrata en todas las contiendas de OH desde 2014; LOYO 2.066 vs 2.478 sin sesgo; cronológico 1.802 vs 2.464 (P = 0.002) |
| Terceros (Kissick) | `real = a + c·(otros en las encuestas que los reportan)` | Mejor regla en OH y a nivel nacional |
| Indecisos | 50/50 | El reparto proporcional y la cuota R son peores |
| Ventajas grandes | Sin ajuste de escala | b = 1.00 fuera de muestra |
| σ | `√(τ² + s²/k)` calibrada a los días que faltan, t de Student, más una deriva de 0.25 pp/día | Cobertura del 80 % correcta en el backtest |
| Mercados | Promedio de **Kalshi y Polymarket**, mezcla logit con peso 0.30 | Peso estimado con 40 contiendas de 2024 ([detalle](../arizona/docs/03_peso_mercados.md)). Hoy los mercados (~82 %) están muy por encima de las encuestas corregidas (41 %): el peso 0.15/0.50 da 48 %/64 % |
| Recuento | P(\|margen\| ≤ 0.25 pp) | Recuento automático en OH |
| Voto anticipado | civicAPI por condado (88), sin partido | Diagnóstico, peso 0 |

## Carpetas
| Carpeta | Contenido |
|---|---|
| [`produccion/`](produccion/) | Paquete `oh_pronostico`. Fuentes en vivo: Wikipedia, 270toWin, Kalshi, Polymarket, civicAPI y FiveThirtyEight. Incluye CLI, pruebas sin red y tarea programada de Windows |
| [`backtest/`](backtest/) | Backtest de variantes (sesgo estatal, indecisos, encuestas partidistas, terceros), validación cronológica del sesgo, sesgo por regla y escala de ventajas grandes |
| [`docs/`](docs/) | Investigación del electorado (independientes, lealtad, voto anticipado), indecisos, contexto, fuentes y decisiones del modelo |
