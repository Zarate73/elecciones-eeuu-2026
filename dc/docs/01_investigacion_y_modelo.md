# Washington D.C. 2026 · Alcaldía · investigación y modelo general

Corte: 28-oct-2026, a 6 días de la elección del 3 de noviembre. Este es el estado 14 de 14 del proyecto y el único sin encuestas ni mercados de la general. Tampoco hay Excel de insumo: todos los datos se leen en vivo.

## 1. Contexto
- **Boleta oficial** (DCBOE, «General Election Candidates in Ballot Order», 15-jul):
  - **Janeese Lewis George** (D): concejal del Ward 4, socialista democrática.
  - **Rhonda Hamilton** (independiente): campaña de voluntarios (≈ 24 personas, sin personal pagado). Se registró como independiente en 2012, fue candidata por escrito en 2022 y nunca ha tenido un cargo electo.
  - **Robert L. Gross** (Statehood Green): no respondió los cuestionarios de GLAA ni del DC Line.
  - Además hay 10 candidatos declarados por escrito, ninguno concejal ni exalcalde. No hay republicano (la primaria republicana solo tuvo votos por escrito).
- **RCV:** es la primera general de alcaldía con voto preferencial (Iniciativa 83, 2024). Si nadie pasa del 50 % de las boletas activas, se elimina al último y sus votos se transfieren.
- **Primaria demócrata (16-jun):**
  - Lewis George 54.1 % y McDuffie 35.1 % en la primera ronda; no hizo falta segunda ronda.
  - McDuffie aceptó la derrota y se comprometió a apoyarla (desayuno de unidad del 18-jul).
  - La alcaldesa Bowser, que se retira, no la ha respaldado.
- **Campaña:** Trump llamó a Lewis George «communist adherent» y amenazó con limitar el autogobierno (*home rule*) si gana. Los medios locales la dan como «fuerte favorita» (Washington Blade, Washington Sun).
- **Encuestas:** ninguna de la general. Las dos encuestas publicadas son de la primaria y no se usan:
  - WaPo/GMU/Braun, 27 may–1 jun, 836 LV: 36–25 con 25 % de indecisos.
  - City Cast/True Dot, 12–17 may, 487 RV.
- **Mercados:** no hay mercado de esta elección.
  - Kalshi: 0 de los ~15,300 eventos abiertos (búsqueda completa del 28-oct). Las series KXMAYORDC, KXDCMAYOR y similares no existen.
  - Polymarket: solo tuvo la primaria demócrata, ya resuelta.

## 2. Electorado
- **Registro al 30-sep-2026** (DCBOE, informe mensual): 453,471 votantes.
  - Demócratas 76.3 %, sin partido 17.3 %, republicanos 5.0 %, Statehood Green 0.9 %.
  - La proporción de demócratas es estable: 76.6 % en sep-2022.
  - El total cayó desde 503,740 por depuración del padrón.
- **Voto anticipado:** D.C. no publica voto anticipado por partido; civicAPI devuelve ceros para DC. El voto anticipado en persona corre del 26-oct al 1-nov.
- **El voto de protesta se concentra en la alcaldía.** Contiendas de toda la ciudad certificadas por la DCBOE ([`backtest/datos/contiendas_citywide_certificadas_2014_2022.csv`](../backtest/datos/contiendas_citywide_certificadas_2014_2022.csv)):

| Año | Alcaldía (D) | Delegado (D) | Presidente del Consejo (D) |
|---|---|---|---|
| 2014 | 55.2 (opositor fuerte: Catania) | 83.7 | 82.4 |
| 2018 | 76.4 | 87.0 | 89.1 |
| 2022 | 74.6 | 86.5 | 82.0 |

  Con opositores débiles, el demócrata saca 7–13 pp menos en la alcaldía que en los otros cargos. Por eso el modelo se calibra solo con generales de alcaldía.

- **Indecisos e intención:** no hay encuestas de la general para estudiarlos. La lección viene de la primaria (sección 4): repartir a los indecisos en proporción reproduce mejor el resultado que dejarlos sin repartir. Si aparece una encuesta de la general, sus indecisos se reparten en proporción.

## 3. Datos del modelo (en vivo)
| Fuente | Vía | Uso |
|---|---|---|
| Wikipedia, 13 páginas «AAAA Washington, D.C., mayoral election» (1974–2022) | API MediaWiki | Resultado de cada general (votos válidos) y % del nominado en la primaria |
| Wikipedia, página 2026 | API MediaWiki | Valida la boleta (avisa si aparece otro candidato); encuestas de la general si se publican; % de la primaria |
| `data/contexto_alcaldias.csv` | Archivo versionado | Criterio del opositor (fuerte/débil) y titularidad, con el cargo de cada opositor |
| DCBOE | Página de estadísticas, luego PDF del último informe mensual | Registro por partido (contexto) |
| Kalshi y Polymarket | APIs públicas (búsqueda en cada corrida) | Mezcla logit con peso 0.30 si aparece un mercado |

- **Contraste con los resultados certificados:** las cifras de Wikipedia coinciden con las de la DCBOE con una diferencia de 0.1 pp o menos (2014, 2018, 2022).
- **Respaldo:** si Wikipedia falla, cada año usa su caché o el respaldo versionado.

## 4. El modelo de la primaria (base en GitHub) y qué se reutiliza
El repo [`dc2026-rcv-forecast`](https://github.com/Zarate73/dc2026-rcv-forecast) pronosticó la primaria con un Monte Carlo RCV que combinaba encuestas, endorsements, financiamiento y patrones por ward. Acertó a la ganadora (P = 85.3 %), pero su primera ronda falló por mucho:

| | Modelo | Real | Error |
|---|---|---|---|
| Lewis George | 42.2 | 54.1 | −11.9 |
| McDuffie | 31.6 | 35.1 | −3.5 |
| Los 6 menores + otros | 26.2 | 10.8 | +15.4 |

- **Causas del error:**
  - Los indecisos se repartían 55 % a candidatos, 30 % agotados y 15 % abstención. Solo con repartirlos en proporción, la WaPo/GMU ya da 48–33.
  - Los candidatos menores salían con 1.2 a 4.4 veces su resultado real (24 veces la categoría «otros»).
- **Error de la comparación en su README:** contrasta la cuota final simulada (51.85 %) con la primera ronda real (52.79 %). No son la misma cantidad.

Más detalle en [`backtest/revision_modelo_primaria.py`](../backtest/revision_modelo_primaria.py).

**Qué se reutiliza:**
- El conteo RCV de `run_rcv`: eliminar al último, transferir con fracción agotada y, con dos candidatos activos, gana el primero. Se reprodujo en `rcv.py` en versión vectorizada y las pruebas comparan las dos versiones en 2,000 casos.
- El concepto de agotamiento.

**Qué no se reutiliza:**
- La capa de encuestas, endorsements y financiamiento: para la general no hay encuestas, y los endorsements y el dinero de una contienda tan dispareja no se pueden calibrar.

**Lecciones aplicadas:**
- Los indecisos se reparten en proporción.
- La cuota de los candidatos menores sale de resultados reales, no de encuestas.

## 5. Backtest y selección (LOYO, 13 generales 1974–2022)
- **Variable principal:** opositor principal **fuerte** = concejal o alcalde, actual o anterior. El criterio se fijó antes de mirar los resultados y es objetivo: lo cumplen 1986–2002 (Schwartz), 2010 (Fenty, por escrito) y 2014 (Catania). No lo cumplen Fletcher (exfuncionario federal), Turner (exjefe de policía, designado), Wilcox (exjunta de educación) ni Grant.
- **Variable respuesta:** logit del % del demócrata. Predictiva t con la incertidumbre de los coeficientes.
- **Métrica:** CRPS en pp, con bootstrap por elección contra M1.

| Variante | CRPS | MAE | Cobertura IC80 | ΔCRPS vs M1 | P(mejor que M1) |
|---|---|---|---|---|---|
| M0 media | 6.91 | 10.01 | 77 % | +2.43 | 0.02 |
| **M1 opositor fuerte** | **4.49** | **6.17** | 77 % | — | — |
| M2 + titular | 4.83 | 6.68 | 85 % | +0.34 | 0.21 |
| M3 + % en la primaria | 5.00 | 7.02 | 77 % | +0.51 | 0.00 |
| M4 + tendencia | 4.90 | 6.82 | 77 % | +0.42 | 0.00 |
| M5 σ por grupo | 4.64 | 6.22 | 77 % | +0.15 | 0.11 |
| M6 vida media 12/20/32 años | 4.75 / 4.69 / 4.62 | — | 77 % | +0.26 / +0.21 / +0.13 | ≤ 0.03 |

- **Conclusión:** gana **M1**, `logit(%D) = 1.424 − 0.911·fuerte` con σ = 0.395. Con opositor débil, el centro es 80.6 %; con opositor fuerte, 62 %.
- **Lo que no predice:** el % de la primaria (Barry 1978 con 35 % sacó 70; Dixon 1990 con 34 % sacó 86; Bowser 2022 con 49 % sacó 75), la titularidad y la tendencia.
- **Reparto del voto no demócrata:**
  - Statehood Green cuando no es el opositor principal: media geométrica 1.28 % (sd del log 0.76; 8 elecciones).
  - Votos por escrito sin campaña organizada: 0.9 / 4.0 / 3.3 % en 2014/2018/2022. Se usa una lognormal de mediana 3 %.
  - El opositor principal se lleva al menos el 37 % del voto no demócrata (mediana 60 %). Se usa un mínimo de 30 %.

**Qué valida y qué no valida el backtest:**
- Valida el centro y la dispersión del % del demócrata en la primera ronda: cobertura del IC80 de 77 %, con 13 observaciones.
- **No valida la cola de derrota.** El demócrata ganó las 13 elecciones; P(pierde) ≈ 0.2 % sale de la forma t, no de casos observados.
- No valida el reparto entre Hamilton, Gross y los votos por escrito (calibrado, no evaluado fuera de muestra), ni las transferencias RCV. Para estas no hay datos, pero solo importan si Lewis George queda por debajo de 50 %.
- La mezcla con mercados no aplica: no hay mercados.

## 6. Pronóstico al 28-oct (corrida sin red con las respuestas reales)
| Primera ronda | % (IC80) |
|---|---|
| Janeese Lewis George (D) | **79.6** (70.0–88.1) |
| Rhonda Hamilton (I) | 15.4 (6.3–25.3) |
| Robert L. Gross (Verde) | 1.7 (0.5–3.3) |
| Votos por escrito | 3.3 (1.6–5.6) |

- **Probabilidades:** P(Lewis George gana) **99.8 %**; P(gana en la primera ronda) 99.7 %; P(≥ 70 %) 90 %; P(≥ 80 %) 54 %.
- **Escenarios** (no cambian el pronóstico):

| Escenario | % Lewis George | P(gana) |
|---|---|---|
| Solo las 7 elecciones con opositor débil (σ propia) | 79.1 | 99.1 % |
| Nivel reciente 2018–2022 (75.5 %) | 74.6 | 99.3 % |
| Protesta moderada, centrada en 70.2 % (1978) | 69.3 | 97.9 % |
| Si surgiera un opositor fuerte | 62.1 | 91.6 % |
| Transferencias RCV desfavorables | 79.7 | 99.8 % |

## 7. Riesgos y límites
- **El nivel de los últimos dos ciclos (75–76 %) está por debajo del centro de M1 (80.6 %).** La tendencia no mejora el backtest, pero el escenario «nivel reciente» es plausible. Lewis George, además, no tiene el respaldo de Bowser y es blanco de ataques nacionales. La diferencia entre los dos (≈ 5 pp) cabe dentro del IC80 (70–88).
- **Antecedente de Buffalo 2021:** una candidata socialista democrática perdió ante el alcalde en funciones, que hizo campaña por escrito. Aquí no hay una candidatura así. La lista oficial de candidatos por escrito cerró en julio y ninguno es concejal ni alcalde. Si apareciera, el escenario «opositor fuerte» da 92 %.
- **Encuestas o mercados nuevos:** si aparecen, entran solos.
  - Encuestas: combinación por precisión en escala logit, con una sd de 7 pp por encuesta. No está validada con historia (no hay encuestas de generales de alcaldía de D.C.).
  - Mercados: mezcla logit con peso 0.30.
