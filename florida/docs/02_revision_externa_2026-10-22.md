# Revisión externa del modelo de Florida (22-oct-2026)

Las cifras son reproducibles con [`backtest/revision_observaciones.py`](../backtest/revision_observaciones.py). Resultados en `backtest/salida/revision_*.csv`.

## Resumen
| Observación | Veredicto | Acción |
|---|---|---|
| 3. El backtest (`days >= H`) y producción (ventana de 21 días) no usan la misma ventana | **Incorrecta en la práctica** (la diferencia afecta 1 de 848 contiendas, fuera de FL) | Ventana explícita en el backtest y en la calibración; prueba de equivalencia; backtest recorrido (sin cambios) |
| Comparar el sesgo estatal con validación estrictamente cronológica | Pertinente | Hecha: el sesgo sigue ganando en FL |
| A. 19 de 23 → 18 de 23 | **Correcta** | Corregida en README, docs, módulo y notebook |
| B. Terceros: «no reportado» se convertía en 0 % | **Correcta** | v1.1.0: no reportado ≠ 0 en el analizador, la calibración y el modelo |
| B. La regla de terceros mejora % D pero empeora % R | Correcta, y ya se veía en la tabla | Documentada; la regla se mantiene porque mejora el error conjunto |
| C. El escenario «sin sesgo» cambia a la vez el sesgo y los mercados | **Correcta** | 2 × 2 sesgo × mercados; todos los escenarios traen su probabilidad con mercados |
| Sensibilidad a la contracción y a la deriva | Pertinente | Escenarios agregados y probados |
| Registro de lo publicado antes de modificar | Pertinente | `produccion/salidas/versiones/v1.0.0_2026-10-22/` y columna `version_modelo` en el historial |

## 3. Ventana
- **FiveThirtyEight raw-polls solo publica encuestas de los últimos 21 días antes de la elección** (máximo de días a la elección = 21 en las 11,475 filas). Con H = 12, `days >= 12` ya equivale a «12 a 21 días», que es exactamente la ventana de producción el 22-oct: encuestas que terminan desde el 13-oct, sin pasar el corte.
- **Verificación.** Cada una de las 848 contiendas se recalculó con las funciones de producción (`modelo.seleccionar_ventana` e `historico.promedio`) y se comparó con el promedio del backtest:
  - 847 contiendas son idénticas (diferencia < 0.01 pp, mismo k).
  - La única diferencia es GA Presidente 2024. Su archivo de Wikipedia traía 3 encuestas a 22 días: el backtest las usaba y producción no (0.63 pp).
  - La regla de ampliación (menos de 2 encuestadoras en la ventana) se activa en 248 contiendas, pero no agrega nada, porque no hay encuestas más viejas en los datos.
- **Corrección.** `motor_backtest.construir` y la calibración de producción filtran ahora `12 <= days <= 21` de forma explícita. Después de la corrección, las 848 contiendas son idénticas a producción (diferencia máxima 0.0000 pp). El backtest recorrido da las mismas cifras (CRPS FL: G 2.200, H8 2.643; P = 0.06) y τ, s y ν no cambian.

## Validación estrictamente cronológica del sesgo estatal
El LOYO estima el sesgo estatal solo con años anteriores, pero los efectos de casa y τ, s y ν también usaban años posteriores. Aquí todo se estima con años anteriores al evaluado. Evaluación 2004–2024 (674 contiendas):

| Ámbito | n | CRPS con sesgo | CRPS sin sesgo | P(sin sesgo mejor) |
|---|---|---|---|---|
| Nacional | 674 | **3.202** | 3.394 | 0.002 |
| Gobernadores del país | 199 | **3.165** | 3.244 | 0.225 |
| Florida | 18 | **2.136** | 2.660 | 0.085 |
| Florida, gobernador | 5 | **1.891** | 2.300 | 0.097 |
| Florida 2016+ | 9 | **2.311** | 3.591 | 0.002 |

La conclusión no cambia: en Florida el sesgo estatal mejora el error también bajo validación cronológica. Matiz: en el LOYO, los gobernadores del país prefieren levemente quitar el sesgo (3.478 contra 3.515, P = 0.59); en la validación cronológica, no.

## A. Signos
`errores_encuestas_FL.csv` tiene 18 errores pro-D de 23. La cifra de 19 era un error de conteo.

## B. Terceros
- **Problema.** El analizador de Wikipedia sumaba las columnas de terceros con `nan_to_num`: «—» (la encuesta no los reporta) se convertía en 0 %. En la ventana del 22-oct las cuatro encuestas tienen «—», así que el modelo leía «0 % de terceros» en lugar de «sin dato». En el histórico, el 63 % de las filas de 538 no reporta terceros (NaN), y también se rellenaban con 0.
- **Variante T4 (adoptada en v1.1.0).** El porcentaje de terceros se promedia solo entre las encuestas que lo reportan, y se calibra `real = a + c·reportado`. Si ninguna encuesta lo reporta, se usa la media histórica de las contiendas sin reporte (435 de 848).

  | Ámbito | Regla | MAE % D | MAE % R | MAE conjunto | MAE terceros |
  |---|---|---|---|---|---|
  | Nacional (848) | T0 sin terceros | 2.995 | 2.490 | 2.743 | 2.724 |
  | | T2 anterior (faltante = 0) | 2.475 | 2.441 | 2.458 | 1.475 |
  | | **T4 no reportado ≠ 0** | **2.468** | **2.430** | **2.449** | **1.427** |
  | Florida (23) | T0 sin terceros | 2.102 | **1.649** | 1.876 | 1.693 |
  | | T2 anterior | **1.493** | 1.834 | **1.664** | **1.214** |
  | | T4 | 1.509 | 1.856 | 1.683 | 1.237 |

- **Decisión.** Se adopta T4 por corrección metodológica y porque mejora a nivel nacional. En FL es 0.02 pp peor en 23 contiendas, una diferencia sin peso estadístico. Hoy el efecto es mínimo: terceros pasan de 2.0 a 2.1 %; margen y probabilidad no cambian.
- **Sobre % R.** Es cierto que la regla de terceros empeora el % R en FL. No es un defecto de la regla, sino del margen: en FL el resultado republicano supera al pronóstico, y cualquier asignación de terceros resta lo mismo a D y a R. La regla «media histórica del estado» (T3) da el mismo % R (1.84). El error conjunto sí mejora.

## C. Escenarios cruzados (22-oct, 200,000 simulaciones)
| Sesgo estatal | Mercados | Margen | P(Jolly) |
|---|---|---|---|
| Sí | No | −10.1 | 2.6 % |
| No | No | −5.2 | 14.3 % |
| Sí | Sí (final) | −8.3 | 5.0 % |
| No | Sí | −4.8 | 16.2 % |

Todos los demás escenarios simulados traen ahora también `P_D_con_mercados` y `margen_con_mercados`, con la misma mezcla que el final.

## Sensibilidad agregada (22-oct, sin mercados; cada fila trae también su valor con mercados en `escenarios_gobernador.csv`)
| Escenario | P(Jolly) |
|---|---|
| Sesgo estatal sin contraer (−5.42) | 2.1 % |
| Sesgo estatal a la mitad (−2.41) | 6.3 % |
| Efectos de casa k = 4 / k = 16 (base 8) | 2.6 % / 2.4 % |
| Deriva al doble (0.50 pp/día) | 2.6 % (hoy las encuestas tienen 2 días de antigüedad) |

## Versión
- **v1.0.0** (publicada el 22-oct, 03:51 ET): copia en `produccion/salidas/versiones/v1.0.0_2026-10-22/`.
- **v1.1.0:** terceros con no reportado ≠ 0, ventana explícita de 21 días en la calibración, escenarios cruzados y de sensibilidad. El historial registra `version_modelo` en cada corrida.
- El notebook de `modelo_general/` queda como v1.0.0: mismo margen y probabilidad, terceros 2.0 %.
