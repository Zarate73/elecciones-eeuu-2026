# Revisión externa del modelo de Nevada (22-oct-2026)

Las cifras se reproducen con [`backtest/revision_nevada.py`](../backtest/revision_nevada.py); los resultados están en `backtest/salida/revision_*.csv`. Los escenarios nuevos vienen en `nv_pronostico` v1.1.0.

## Resumen
| Observación | Veredicto | Acción |
|---|---|---|
| A. Dependencia de una encuesta interna (GSG ~70 %) | **Pertinente** | Escenarios de influencia: se quita cada encuesta y se reconstruye la ventana. Backtest en contiendas parecidas a la de hoy |
| B. Sesgo estatal: 2014 (una encuestadora, +22.8) y muestras chicas | **Pertinente, y cambia la lectura** | Comparaciones sin 2014 y por número de encuestadoras. Escenario con el sesgo estimado sin contiendas de una sola encuestadora |
| C. Terceros dependen de una sola medición de septiembre | **Pertinente** | Escenarios de reducción moderada y pronunciada |
| Mercados: coincidencia temporal ≠ causa; dos plataformas ≠ dos señales independientes | **Correcta** | Redacción corregida. Ya se promediaban en una sola señal con peso 0.30 |
| Peso 0.30 no validado en régimen de escasez de encuestas | **Correcta** | Máxima verosimilitud en 2024 con k ≤ 2 y escenarios con pesos 0.15 y 0.50 |

**El pronóstico publicado no cambia** (P(Ford) 41.9 %, margen −1.2): todo lo nuevo entra como escenario. La revisión sí cambia la interpretación del sesgo estatal (ver B).

## A. Dependencia de la encuesta interna de Global Strategy Group
**Influencia** (22-oct; probabilidad sin mercados → con la misma mezcla de mercados)
| Escenario | Ventana resultante | Margen (solo encuestas) | P(Ford) |
|---|---|---|---|
| Base | NPI (22–26 sep) + GSG (D, 8–13 oct) | −2.9 | 31.8 % → 41.9 % |
| **Sin GSG** | NPI + Emerson (5–8 sep, Ford +2) | −1.1 | 42.9 % → 50.1 % |
| Sin NPI | Solo GSG | −3.0 | 35.4 % → 44.6 % |
| Sin encuestas partidistas | NPI + Emerson | −1.1 | 43.0 % → 50.2 % |

- **Resultado clave:** la encuesta interna de Ford no infla a Ford.
  - Tras su efecto de casa (+1.4 pro-D), GSG da Lombardo +2.4, igual o más favorable a Lombardo que NPI.
  - Al quitarla, la regla de ampliación trae a Emerson (Ford +2), y P(Ford) sube de 41.9 % a 50.1 %.
- **La dependencia de una sola observación es grande:** unos 8 pp de probabilidad. No se adopta como escenario principal; se reporta siempre.

**Backtest en el régimen de hoy:** 44 contiendas históricas con k ≤ 2 y más del 50 % del peso en encuestas partidistas.

| Variante | CRPS | MAE | Cobertura 80 % |
|---|---|---|---|
| **G (producción)** | **2.948** | **3.942** | 0.93 |
| P1 · patrocinador si la firma no tiene historia | 3.035 | 4.096 | 0.93 |
| P3 · partidistas pesan la mitad | 3.018 | 4.072 | 0.91 |
| P2 · sin encuestas partidistas | 3.479 | 4.774 | 0.91 |
| H8 · sin sesgo estatal | 3.165 | 4.437 | 0.91 |

En contiendas parecidas a la de hoy, el tratamiento actual (incluir la encuesta interna con su efecto de casa) es el mejor. Descartar las partidistas es lo peor. La cobertura del 80 % es 0.93, así que con pocas firmas la σ no se queda corta.

## B. Sesgo estatal
**LOYO** (P = probabilidad por bootstrap de años de que quitar el sesgo mejore)
| Ámbito | n | Con sesgo | Sin sesgo | P |
|---|---|---|---|---|
| NV, todas | 23 | 3.321 | 3.265 | 0.64 |
| **NV sin 2014** | 22 | **2.521** | 2.585 | **0.34** |
| **NV con k ≥ 2** | 18 | **2.390** | 2.507 | **0.23** |
| NV con k = 1 | 5 | 6.673 | 5.996 | 0.94 |
| NV gobernador sin 2014 | 5 | 2.224 | 2.204 | 0.59 |
| NV gobernador con k ≥ 2 | 4 | 1.798 | 1.945 | 0.31 |

**Validación cronológica** (2004–2024)
| Ámbito | n | Con sesgo | Sin sesgo | P |
|---|---|---|---|---|
| NV | 19 | 3.441 | 3.418 | 0.56 |
| **NV sin 2014** | 18 | **2.443** | 2.572 | **0.23** |
| NV gobernador sin 2014 | 4 | 1.809 | 2.002 | 0.33 |

- **La ventaja aparente de «sin sesgo» en NV venía de 2014 y de las contiendas con una sola encuestadora.** Sin ellas, el sesgo mejora el error en NV, en LOYO y en la validación cronológica. Así se refuerza la decisión de mantenerlo, que antes se había tomado solo por la regla nacional.
- **Pero el valor actual del sesgo sí depende de esas contiendas:**

| Cómo se estima | Bruto | Contracción | Se resta al margen |
|---|---|---|---|
| Producción (todas las contiendas) | +0.80 | 0.73 | **−0.58** |
| Sin NV 2014 | +0.13 | 0.85 | −0.11 |
| Solo contiendas con k ≥ 2 (todos los estados) | +0.13 | 0.81 | −0.11 |

- **¿Excluir las contiendas de una sola encuestadora al estimar el sesgo, en todos los estados?** En LOYO mejora un poco en todos los ámbitos, pero sin significancia:
  - nacional 3.365 contra 3.375 (P = 0.56);
  - gobernadores 3.496 contra 3.515;
  - NV 3.310 contra 3.321.
- Como es una regla de todos los estados y la evidencia es débil, **no se adopta solo en Nevada**. Queda como escenario: −0.11 pp, P(Ford) 34.8 % sin mercados y 44.2 % con mercados. La decisión es transversal a GA, FL y NV.

## C. Terceros
NPI (22–26 sep) es la única encuesta de la ventana que reporta terceros (10 %, con Danielle Ford en 7 %). La regla da 8.1 %.

| Escenario (solo encuestas) | Terceros | Ford | Lombardo | Margen |
|---|---|---|---|---|
| Sin cambio | 8.1 % | 44.5 % | 47.4 % | −2.9 |
| Reducción moderada (apoyo × 0.6) | 5.2 % | 46.0 % | 48.8 % | −2.8 |
| Reducción pronunciada (apoyo × 0.3) | 3.0 % | 47.1 % | 49.9 % | −2.8 |

Los escenarios miden la sensibilidad, no suponen que alguno vaya a ocurrir. Los porcentajes publicados se mueven hasta 2.6 pp por candidato, mientras el margen y la probabilidad casi no cambian. La simulación incluye la incertidumbre residual histórica de los terceros (σ 1.8). No modela por separado el error muestral de NPI ni la correlación entre terceros y margen; si Danielle Ford pierde sobre todo votos de un solo lado, el margen también cambiaría.

## D. Mercados
- **Redacción corregida.** Que la subida de Kalshi y Polymarket coincida con los reportes de voto anticipado es descriptivo, no causal.
- **No son dos señales independientes.** Las dos plataformas no cotizan igual (correlación de cambios diarios −0.03), pero eso no las hace independientes: probablemente reaccionan a la misma información. Por eso entran como **un promedio** con peso 0.30; no hay doble conteo.
- **Peso en régimen de escasez** (máxima verosimilitud con el margen real, 2024, h = 13):

| Contiendas | n | w óptimo | IC95 | Pérdida con w = 0.30 (ΔLL) |
|---|---|---|---|---|
| Todas | 40 | 0.65 | 0.25–1.00 | −1.27 |
| k ≤ 3 | 22 | 0.60 | 0.15–1.00 | −0.71 |
| k ≤ 2 | 11 | 0.80 | 0.05–1.00 | −0.80 |
| k ≥ 4 | 18 | 0.70 | 0.00–1.00 | −0.60 |

Con pocas encuestas, los datos no piden menos peso para los mercados, si acaso más. 0.30 queda dentro de todos los intervalos y del lado conservador, pero con 11 contiendas de un solo año no está validado para este régimen. **Sensibilidad:** con peso 0.15, P(Ford) = 36.7 %; con 0.50, 49.0 % (base 0.30: 41.9 %).
