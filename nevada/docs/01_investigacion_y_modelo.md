# Nevada 2026 · Gobernador (general) · Investigación, backtest y modelo

Corte: 22-oct-2026, 12 días antes de la elección del 3-nov.

Carpetas:
- [`../produccion/`](../produccion/): paquete `nv_pronostico` con fuentes en vivo y 16 pruebas sin red. El notebook ejecutado y tu Excel están en la carpeta local `Pronosticos/Nevada/MODELO_NEVADA_GENERAL`.
- [`../backtest/`](../backtest/): backtest, datos y resultados.

## 1. Pronóstico
| Candidato | % de voto (IC80) | Probabilidad de ganar |
|---|---|---|
| Aaron Ford (D) | 45.3 % (41.2–49.5) | 42 % |
| **Joe Lombardo (R, gobernador)** | **46.6 %** (42.4–50.7) | **58 %** |
| Terceros: Danielle Ford (I), otros y «None of these candidates» | 8.1 % (5.8–10.4) | — |

- **Margen Ford − Lombardo:** −1.2 pp (σ 6.4; IC95 −13.9 a +11.5). Es una contienda abierta.
- **P(|margen| ≤ 0.5 pp):** 6.5 %. Nevada no tiene recuento automático, pero cualquier candidato puede pedirlo.
- **Cómo se llega:**
  - Promedio de encuestas: −2.25.
  - Sesgo estatal de NV: −0.58 (pequeño).
  - Resultado solo con encuestas: −2.85, con P(Ford) 31.8 %.
  - Los mercados (Kalshi y Polymarket, ambos en 66.5 %) mueven el margen +1.6 y suben P(Ford) a 41.9 %.

**Cruce sesgo × mercados**
| Sesgo estatal | Mercados | Margen | P(Ford) |
|---|---|---|---|
| Sí | No | −2.9 | 31.8 % |
| No | No | −2.2 | 35.5 % |
| **Sí** | **Sí (final)** | **−1.2** | **41.9 %** |
| No | Sí | −0.8 | 44.7 % |

**Otros escenarios** (sin mercados → con mercados)
| Escenario | P(Ford) |
|---|---|
| Sin efectos de casa | 37.6 % → 46.3 % |
| Ajuste por patrocinador (la encuesta de GSG es interna de Ford) | 27.1 % → 38.1 % |
| Ventana de 60 días (agrega a Emerson, Ford +2) | 33.2 % → 43.0 % |
| Polymarket por rangos de margen | 53.0 % (margen implícito Ford +0.9) |

**El dato clave: encuestas y mercados no coinciden.**
- **Encuestas (31.8 %):** solo hay dos encuestadoras en la ventana ampliada.
  - Noble Predictive Insights, 22–26 sep: Lombardo +2.
  - Global Strategy Group, 8–13 oct, interna de la campaña de Ford: Lombardo +1. Con su efecto de casa (+1.4 pro-D) queda en −2.4.
- **Mercados (66.5 %):** subieron de 51.5 % a 66.5 % entre el 13 y el 21-oct, en coincidencia con los reportes de voto anticipado con ventaja demócrata (Ralston, 21-oct). El modelo no usa el voto anticipado directamente, pero los mercados sí lo incorporan, y entran con peso 0.30.

## 2. Fuentes
| Fuente | Qué aporta | Uso |
|---|---|---|
| Wikipedia (API) | 14 encuestas; 7 posteriores a la primaria, con n, población y terceros | Pronóstico |
| 270toWin | 5 encuestas, fechadas por publicación | Pronóstico (se deduplica) |
| Tu Excel (`NEVADA_GOBERNADOR-v2.xlsx`) | 12 encuestas generales; **Wedgewood Polls (D)** solo está aquí | Pronóstico (se deduplica) |
| **Kalshi** `GOVPARTYNV-26` | Ford 66.5 % | Mezcla con peso 0.30 (promediado con Polymarket) |
| **Polymarket** `nevada-governor-winner-2026` | Ford 66.5 % | Mezcla con peso 0.30 |
| Polymarket por rangos de margen | Margen implícito Ford +0.9 (σ 7.9) | Escenario |
| **civicAPI (NV)** | Votos emitidos por partido y condado (correo y en persona) | Diagnóstico |
| On Point Politics `/api/polls/nv-gov-2026` | Las mismas encuestas que Wikipedia | Contraste |
| The Nevada Independent (Ralston, voto anticipado) | Comparación del voto anticipado con 2022 y 2024 al mismo día | Contexto (sin API) |

**Particularidades de Nevada que se resolvieron en el código**
- **Hay dos candidatos Ford.** La columna del demócrata se busca como «Aaron Ford». **Danielle Ford** (independiente, consejera estatal de educación) cuenta como tercero: 7 % en NPI.
- **«None of these candidates»** aparece en la boleta. Entra en «terceros», que se calibra con el resultado real (100 − D − R).
- **Fechas del Excel** en inglés y sin año («Sep 22–26»). Se excluyen el promedio, las preguntas de primaria, los careos hipotéticos («Ford vs. Hansen») y la versión RV repetida de NPI.
- **civicAPI no separa a los no partidistas en NV:** van en «Otros».
- **La página de estadísticas del Secretario de Estado** responde 403 a consultas automáticas. El registro se tomó de la prensa (FOX5, 5-oct), que cita al Secretario de Estado.

**Se recomienda agregar** (hoy no entran por falta de serie histórica para validarlas):
- la serie diaria de voto anticipado por partido del Secretario de Estado y de Clark y Washoe, para construir una serie del mismo día para 2028;
- los reportes de Ralston como contraste.

## 3. Electorado y comportamiento de los indecisos
**Registro activo** (Secretario de Estado, cierre de septiembre de 2026)
| Grupo | Votantes | % |
|---|---|---|
| No partidistas | 809,764 | 38.9 % |
| Demócratas | 575,465 | 27.6 % |
| Republicanos | 571,078 | 27.4 % |
| Independent American Party | 83,392 | 4.0 % |
| Libertarios y otros | 44,678 | 2.1 % |
| **Total** | **2,084,377** | |

- **Los no partidistas son el grupo más grande y crecen por un cambio administrativo.** Desde 2025, quien se registra en el DMV y no devuelve el formulario de partido queda como no partidista. En Clark, el 94 % de los nuevos registros de 2026 son no partidistas.
- Por eso el registro D/R ya no describe bien al electorado probable. La ventaja demócrata en registro hoy es casi nula (+4,387).

**Primarias del 9-jun:** 187,818 votos demócratas (Ford 63.3 %) contra 189,634 republicanos (Lombardo 90.8 %, sin rival real).

**Voto ya emitido** (civicAPI, 22-oct)
- **Total:** 230,976 (148,796 por correo y 82,180 en persona).
- **Por partido registrado:** D 39.7 %, R 35.5 %, otros 24.8 % → D+4.2.
- **Por modalidad:** correo D+9.1; en persona R+4.7.
- **Comparación (Ralston, 21-oct):** la ventaja demócrata urbana está unos 1.4 pp por encima de la de 2022 al mismo día. En 2022 Lombardo ganó por 1.5. En 2024 los republicanos iban adelante a estas alturas. Ralston advierte que falta cerca de tres cuartas partes del voto.
- **Solo diagnóstico:** es registro, no intención de voto (y el 25 % «otros» decide la elección). No hay serie del mismo día para calibrarlo.

**Indecisos y terceros**
- **NPI (LV, 22–26 sep):** Lombardo 42, Ford 40, Danielle Ford 7, indecisos 9. Entre no partidistas, 32–32. La aprobación de Trump en NV es de 38 % (61 % desaprueba).
- **Emerson (nov-2025):** los independientes daban Lombardo +8, pero el 40 % estaba indeciso. Ford ganaba a los hispanos por 16.
- **Backtest de reglas de indecisos:**
  - El reparto proporcional (H2) es el mejor en NV (CRPS 3.166 contra 3.321), pero el peor a nivel nacional (3.650 contra 3.375; P = 0.000). Adoptarlo sería sobreajustar con 23 contiendas.
  - La cuota R estimada (H3) es peor en NV (3.410).
- **Regla adoptada: indecisos 50/50.**
- **Terceros:**
  - Con NPI reportando 10 % de otros, la regla calibrada da 8.1 % (`0.81 + 0.73 × 10`).
  - En NV, la regla subestimó históricamente a los terceros en 0.7 pp.
  - El riesgo va en el otro sentido: una independiente sin dinero suele perder apoyo al final. Si Danielle Ford cae, los votos se reparten entre los dos candidatos.
  - El margen no depende de los terceros; solo cambian los %.

## 4. Backtest (LOYO, horizonte de 12 días, ventana de producción de 12 a 21 días)
- **Datos:** FiveThirtyEight 1998–2022 más 2024 (incluye NV Presidente y Senado). En total 848 contiendas, 23 de NV.
- **Métrica:** CRPS, más bootstrap por años.

| Variante | CRPS nacional | CRPS NV (23) | CRPS NV 2016+ (9) | P(mejor que G) en NV |
|---|---|---|---|---|
| **G · V11 + sesgo estatal contraído** | **3.375** | 3.321 | 2.198 | — |
| H8 · sin sesgo estatal (Arizona) | 3.468 | 3.265 | **2.028** | 0.62 |
| F1 · sesgo sin contraer | 3.502 | 3.438 | 2.399 | 0.10 |
| H2 · indecisos proporcionales | 3.650 | **3.166** | 2.178 | 0.65 (nacional 0.000) |
| H3 · cuota R de indecisos | 3.393 | 3.410 | 2.368 | 0.19 |
| P1 · casa + patrocinador si no hay historia | 3.377 | 3.352 | 2.271 | 0.002 |
| P2 · sin encuestas partidistas | 3.439 | 3.418 | 2.405 | 0.002 |
| P3 · partidistas pesan la mitad | 3.386 | 3.357 | 2.280 | 0.006 |

**Error de las encuestas en NV** (+ = sobreestimaron al demócrata)
- Pro-D en 8 de 23 contiendas.
- Subestimaron a los demócratas en 2008 (−11.6), 2010 Sen (−9.7) y 2018 (−5.3 y −6.0).
- Los sobreestimaron en 2020 (+5.1) y 2024 (+2.1 y +3.7).
- La autocorrelación del error relativo a la media nacional es −0.11: no persiste.

**Validación estrictamente cronológica** (todo con años anteriores, 2004–2024): con sesgo 3.441 contra sin sesgo 3.418 en NV (P = 0.55); a nivel nacional con sesgo 3.202 contra 3.395 (P = 0.002).

**Decisión: G** (la regla de Florida y la nacional).
- En NV, quitar el sesgo no es claramente mejor ni peor (P = 0.62 en LOYO y 0.55 cronológico, contra 0.85 en Arizona).
- El sesgo contraído de NV es pequeño (+0.58 pp pro-D).
- Sin evidencia estatal clara se usa la regla que gana a nivel nacional. «Sin sesgo» se reporta siempre (44.7 % con mercados).
- **Encuestas internas de campaña:** ninguna alternativa mejora (P1, P2 y P3 son peores en NV). Se mantiene el efecto de casa de la firma; el ajuste por patrocinador queda como escenario.
- **Terceros:** «no reportado» ≠ 0 % (T4) da 2.311 de MAE conjunto en NV, contra 2.302 de la regla anterior; es una diferencia nula. Se mantiene T4 por consistencia con Florida.

## 5. Mercados
- **Hoy:** Kalshi 66.5 % y Polymarket 66.5 %.
- **Serie desde junio:**
  - Correlación de niveles 0.75 y de cambios diarios −0.03; diferencia media 3.1 pp. No son el mismo precio, así que se promedian.
  - Subieron 15 pp en nueve días (13 al 22-oct), sobre todo el 21-oct (Kalshi de 57.5 % a 66.2 %).
- **Peso:** 0.30, estimado por máxima verosimilitud con 40 contiendas de 2024, entre ellas NV Presidente y Senado.

## 6. Limitaciones
- **Pocas encuestas, viejas y una interna.** En los 21 días previos a la elección solo hay una encuesta (interna de Ford). El promedio usa dos encuestadoras, la más reciente terminó el 13-oct, y la σ incluye 9 días de deriva.
- **Alta sensibilidad a la encuesta de GSG:** pesa el 70 % del promedio. Sin efectos de casa, P(Ford) sube a 46 %; con ajuste por patrocinador, baja a 38 %.
- **El registro ya no informa:** el 39 % de no partidistas, inflado por el registro automático, hace que el voto anticipado por partido sea menos informativo que en otros ciclos.
- **Terceros:** de Danielle Ford y «None of these candidates» depende cuánto suman Ford y Lombardo, pero no quién gana.

Fuentes:
- [Political Wire / NPI, 6-oct](https://politicalwire.com/2026/10/06/joe-lombardo-barely-leads-in-nevada-governors-race/)
- [Noble Predictive Insights, sep-2026](https://www.noblepredictiveinsights.com/post/lombardo-tries-to-escape-trump-s-orbit-up-2-over-ford)
- [The Nevadan News, Danielle Ford](https://thenevadannews.com/news/elections/danielle-ford-nevada-governor-race/)
- [FOX5, registro al cierre de septiembre](https://www.fox5vegas.com/2026/10/05/nevada-sees-surge-active-registered-voters-secretary-states-office-reports/)
- [The Nevada Independent, auge de no partidistas](https://thenevadaindependent.com/es/article/nonpartisans-are-surging-in-nevada-is-a-recent-policy-change-the-reason)
- [Ralston, blog de voto anticipado 2026](https://thenevadaindependent.com/article/the-early-voting-blog-2026-general)
- [Newsweek, encuestas y calificaciones](https://newsweek.com/democrats-chances-flipping-gop-governor-swing-state-nevada-11089696)
- [Just the News / Center Square, Emerson y NPI](https://justthenews.com/nation/states/center-square/lombardo-ford-statistical-tie-according-polling)
