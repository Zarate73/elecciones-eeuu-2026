# Revisión técnica — Georgia V9 (modelo integrado), corte 19-oct-2026

## Resultado V9 publicado
Margen B−J +0.34 (IC95 −5.67, +6.24), P(Bottoms > Jackson) = 0.548, P(nadie >50% → segunda vuelta) = 0.218. Las encuestas solas dan −1.75 (Jackson arriba). Lo que voltea el signo es el componente territorial (+1.47 pp) y, en menor medida, la asignación de indecisos (+0.63 pp).

## Hallazgos críticos
1. **Sesgo del voto anticipado.** El modelo compara la geografía del voto anticipado 2026 contra la geografía del voto FINAL 2022 y reparte el voto restante según los pesos finales de 2022. Como el voto anticipado siempre se concentra en condados metropolitanos con inclinación demócrata (p_D ponderado por anticipado = 0.484 vs 0.462 ponderado por el total 2022), el resultado se carga hacia D por construcción. Aporta unos +0.8 pp. Corrección: comparar contra el voto anticipado 2022 por condado en el día equivalente, y repartir lo que falta según el voto restante de 2022 (final − anticipado).
2. **Proyección de crecimiento 2018→2022.** La pendiente de log-crecimiento según tamaño (+0.0157) se extrapola a 2026 y suma +0.67 pp a D aunque no haya voto anticipado. Además, el JSON de respaldo trae una pendiente de −0.0095 que no coincide con la de esta ejecución.
3. **Doble conteo con encuestas LV.** Las encuestas de votantes probables ya incorporan su propio modelo de electorado. Sumarles un ajuste de composición respecto del mapa 2022 solo se justifica si se demuestra que las encuestas usan ese mapa.
4. **Indecisos.** La Beta(2.62, 3.38) se obtiene del error del promedio RCP en 2018/2022: es error direccional de encuestas, no comportamiento de los indecisos. Mete +0.63 pp a D y se cuenta dos veces junto con el piso de 2 pp.
5. **Incertidumbre subestimada.** Un piso de 2 pp de error común en el margen es bajo. El error histórico de los promedios de encuestas a gobernador ronda 4–5 pp de margen.
6. **Falta la segunda vuelta.** Georgia exige mayoría absoluta y V9 no reporta P(segunda vuelta) ni el ganador condicionado a ella.

## Sensibilidad (las mismas 150k simulaciones)
| Escenario | Margen medio | IC95 | P(B>J) | P(2ª vuelta) |
|---|---|---|---|---|
| V9 tal cual | +0.34 | [−5.67, +6.24] | 0.548 | 0.218 |
| Sin territorio | −1.04 | [−6.98, +4.81] | 0.369 | 0.213 |
| Sin territorio + indecisos 50/50 | −1.65 | [−7.61, +4.25] | 0.293 | 0.193 |
| Sin territorio + piso 4.5 pp | −1.05 | [−10.56, +8.44] | 0.415 | 0.136 |
| Sin territorio + 50/50 + piso 4.5 pp | −1.66 | [−11.15, +7.86] | 0.366 | 0.132 |

## Problemas menores / de producción
- La SD del margen usa la varianza de D−R sin dividir entre (D+R), mientras que el margen sí está normalizado (subestimación de ~5%).
- No hay efectos de casa ni ajuste por patrocinador partidista; 6 de 13 encuestas son (R). Se mezclan RV y LV sin ajuste.
- El backtest de vida media predice la siguiente encuesta, no la elección (n = 9 errores).
- La encuesta Quantus de octubre está escrita en el código en vez de estar en el CSV, y hay constantes (3939428, 3953408) repetidas.
- `pruebas_integracion.py` sobrescribe `salida_integrada/` con n=3000 y exige que haya efecto territorial (está probando un supuesto, no la corrección del código).
- Al CSV de 2018 le falta cuadrar un condado: dem+rep+otros difiere del total en 100 votos.
- El tercer partido tiene un rango estrecho (piso de SD logit 0.3) y la SD del residual de encuestas (0.8 pp) es demasiado ajustada.
