# Nueva York 2026 · Gobernador

Elección general del 3 de noviembre de 2026 entre **Kathy Hochul (D, gobernadora en funciones)** y **Bruce Blakeman (R, ejecutivo del condado de Nassau)**. No hay terceros en la boleta. Gana la mayoría simple.

<!-- PRONOSTICO:INICIO -->
Sin corrida automática todavía: el modelo está validado y empaquetado, pero el flujo de GitHub Actions no está activo. Pronóstico de referencia con las fuentes del 26-oct-2026 (pruebas sin red): **Hochul 56.3 % · Blakeman 43.5 % · P(Hochul) 97.3 %** (margen +12.8, σ 6.5).
<!-- PRONOSTICO:FIN -->

## Modelo general (elegido por backtest)
Base: el modelo de Illinois v1.1.0 (Texas / Maine / Pennsylvania / Nevada / Florida / Georgia V11). Se validó con un backtest *leave-one-year-out* de 945 contiendas (1998–2024, 20 de Nueva York) a 9 días de la elección, con la misma ventana que producción, más una validación estrictamente cronológica.

| Pieza | Cómo entra | Por qué |
|---|---|---|
| Promedio de encuestas | V11: efecto de casa contraído (k = 8), √n, vida media de 14 días, cada firma pesa ~1; ventana de 21 días (hoy: Quinnipiac y ActiVote) | Mejor CRPS nacional (3.304). Las encuestas del 1–6 oct quedan fuera; los escenarios de 45 días y de fecha media las incluyen (+11.8) |
| Identidad de las encuestas | Firma + periodo de campo; Siena SRI ≠ NYT/Siena; decimales del Excel verificado cuando Wikipedia redondea | Conservan su efecto de casa y sus cifras originales |
| Sesgo estatal | Contraído por Bayes empírico con todas las contiendas del estado: hoy **resta** ~1.9 pp (desde 2020 las encuestas en NY sobreestimaron al demócrata) | El estado donde más ayuda: LOYO 2.929 vs 3.419 sin sesgo; cronológico 2.487 vs 2.718; «k ≥ 2» y «por cargo» peores |
| Terceros | Solo dos candidatos en la boleta: votos por escrito fijos (0.15 %) | La Junta Electoral rechazó las demás peticiones; 2022: 0.16 % |
| Indecisos | 50/50 | El reparto proporcional y la cuota R son peores en NY y a nivel nacional |
| Ventajas grandes | Sin ajuste de escala | b = 1.00 fuera de muestra |
| σ | `√(τ² + s²/k)` calibrada a los días que faltan, t de Student, más una deriva de 0.25 pp/día | Cobertura del 80 % correcta en el backtest |
| Mercados | Promedio de **Kalshi y Polymarket**, mezcla logit con peso 0.30 | Peso estimado con 40 contiendas de 2024 ([detalle](../arizona/docs/03_peso_mercados.md)) |
| Recuento | P(\|margen\| ≤ 0.5 pp) | Recuento automático en NY |
| Voto anticipado | civicAPI no cubre NY: diagnóstico opcional, no degrada | — |

## Carpetas
| Carpeta | Contenido |
|---|---|
| [`produccion/`](produccion/) | Paquete `ny_pronostico`. Fuentes en vivo: Wikipedia, 270toWin, Kalshi, Polymarket, FiveThirtyEight (civicAPI opcional). Incluye CLI, pruebas sin red y tarea programada de Windows |
| [`backtest/`](backtest/) | Backtest de variantes (sesgo estatal, indecisos, encuestas partidistas, terceros), validación cronológica del sesgo y escala de ventajas grandes |
| [`docs/`](docs/) | Investigación del electorado (registro, regiones, independientes, indecisos), contexto, fuentes y decisiones del modelo |
