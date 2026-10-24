# Georgia 2026 · Gobernador (y Senado)

<!-- PRONOSTICO:INICIO -->
**Pronóstico al 2026-10-24** (10 días a la elección) · actualizado automáticamente 2026-10-24 00:15 ET · fuentes en vivo 7/7

| Gobernador | % de voto (IC80) | Probabilidad de ganar |
|---|---|---|
| Keisha Lance **Bottoms** (D) | **49.5%** (46.1–52.8) | **41%** |
| Rick **Jackson** (R) | **50.5%** (47.2–53.9) | **59%** |

Margen D−R -1.1 pp (σ 5.3) · solo encuestas: P(Bottoms) 34% · con Kalshi (peso 0.3) · segunda vuelta 0.2% · 15 encuestas, 4 encuestadoras en la ventana

**Encuesta más reciente:** ActiVote, terminó el 2026-10-20 (**4 días** antes del corte). Las fuentes se consultan en vivo, pero el promedio solo puede ser tan reciente como la última encuesta publicada.

**Senado:** Ossoff 53.6% · Collins 46.4% · P(Ossoff) 90% · Jackson+Ossoff 50% · Bottoms+Ossoff 40%

![Pronóstico](produccion/salidas/ultimo/pronostico.png)

![Evolución](produccion/salidas/evolucion.png)

Detalle: [`resumen.txt`](produccion/salidas/ultimo/resumen.txt) · [encuestas usadas](produccion/salidas/ultimo/encuestas_gobernador.csv) · [escenarios](produccion/salidas/ultimo/escenarios_gobernador.csv) · [historial](produccion/salidas/historial_pronosticos.csv)
<!-- PRONOSTICO:FIN -->

El bloque anterior lo actualiza GitHub Actions dos veces al día ([flujo](../.github/workflows/pronostico_georgia.yml)).

| Carpeta | Contenido |
|---|---|
| [`produccion/`](produccion/) | Paquete `ga_pronostico`: Wikipedia, 270toWin, Kalshi, Civic Forge y FiveThirtyEight en vivo. `scripts\instalar.bat` y luego `scripts\correr_pronostico.bat`. Ver su README. |
| [`modelo_v11/`](modelo_v11/) | Notebook final V11 ejecutado (`GEORGIA_2026_MODELO_FINAL_V11.ipynb`), módulo, 17 pruebas y LEEME |
| [`backtest/`](backtest/) | Backtest LOYO de modelos y componentes (V5–V11), análisis de indecisos, Kalshi y observaciones externas |
| Encuesta propia G-Ratings | Solo resultados (24–29 sep 2026, 1,000 RV) en `produccion/data/ajustes_encuestas.csv` y en los CSV de encuestas; el Excel no se publica |
| [`docs/`](docs/) | 01 revisión de V9 · 02 backtest y selección · 03 modelo final V11 y revisión externa |

## Modelo V11 en una línea
Promedio de encuestas corregido por efecto de casa − sesgo histórico de Georgia; σ empírica según el número de encuestadoras; colas Student-t; mezcla 70/30 con Kalshi; indecisos 50/50; solo write-ins como "otros".
