# Backtest California · M1–M4 + Kalshi

Ejecutar desde esta carpeta: `python backtest_california.py`
(requiere pandas, numpy, scipy, matplotlib, openpyxl; lee el Excel de ../CALIFORNIA_2026_NOTEBOOK_COMPLETO).

## data/
| archivo | contenido | fuente |
|---|---|---|
| generales_encuestas.csv | encuestas D vs R de 6 contiendas estatales 2018–2025 | Wikipedia, 270toWin, ARG, ABC7/DDHQ |
| generales_resultados.csv | resultados certificados | SOS / Wikipedia |
| primarias_encuestas_previas.csv | encuestas finales primarias 2018 (gob) y 2024 (senado) | Wikipedia |
| primarias_resultados.csv | resultados top-two 2018, 2024, 2026 | SOS Statement of Vote |
| conteo_primaria_2026.csv | cortes del conteo 3-jun, 10-jun, certificado | San Jose Inside, SOS |
| retornos_tempranos_referencias.csv | composición de boletas devueltas (puntos sueltos) | PDI, Civiq, The Ballot Book |
| kalshi_primaria_avanza.csv | velas diarias KXGOVCAPRIMARY-26 (Becerra, Hilton, Steyer) | API pública Kalshi /historical |
| kalshi_general_ganador.csv | velas diarias KXGOVCA-26 (Becerra, Hilton) abr–oct 2026 | API pública Kalshi |

`fecha_aprox=1` = fechas de campo aproximadas (revocatoria 2021 y algunas de 2024/2025): úsese con cautela en cortes T−7/T−0.
Las encuestas de la primaria 2026 se leen directamente del Excel (hoja Gobernador California, bloque Primarias).

## Limitaciones
- 6 elecciones generales y 3 primarias: los parámetros calibrados son órdenes de magnitud, no estimaciones finas.
- M4 (sentimiento) no es evaluable: la serie de sentimiento empieza el 3-jun-2026.
- M2 histórico requiere la tabla diaria de Civiq/PDI (2022G, 2024G, 2024P, 2025E, 2026P); el notebook la lee pero no la guarda.
