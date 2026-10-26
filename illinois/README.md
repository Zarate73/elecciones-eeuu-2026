# Illinois 2026 · Gobernador

Elección general del 3 de noviembre de 2026 entre **JB Pritzker (D, gobernador en funciones)** y **Darren Bailey (R)**, revancha de 2022, con Collin Corbett (independiente). Gana la mayoría simple.

<!-- PRONOSTICO:INICIO -->
Sin corrida automática todavía: el modelo está validado y empaquetado, pero el flujo de GitHub Actions no está activo. Pronóstico de referencia con las fuentes del 25-oct-2026 (pruebas sin red): **Pritzker 56.2 % · Bailey 38.6 % · P(Pritzker) 99.5 %** (margen +17.6, σ 6.6).
<!-- PRONOSTICO:FIN -->

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
