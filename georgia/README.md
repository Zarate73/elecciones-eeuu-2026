# Georgia 2026 · Gobernador (y Senado)

<!-- PRONOSTICO:INICIO -->
**Pronóstico al 20-oct-2026:** Bottoms 49.3% · Jackson 50.7% · P(Bottoms) = 0.39 · P(segunda vuelta) ≈ 0.2%.
**Senado:** Ossoff 54.1% · Collins 45.9% · P(Ossoff) = 0.91.
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
