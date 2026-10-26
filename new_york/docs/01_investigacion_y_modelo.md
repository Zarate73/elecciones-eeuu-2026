# Nueva York 2026 · Gobernador: investigación y modelo (26-oct-2026)

Elección general del 3 de noviembre: **Kathy Hochul (D, gobernadora desde 2021)** busca su segundo periodo completo contra **Bruce Blakeman (R, ejecutivo del condado de Nassau)**. Hochul va también en la línea del Working Families Party y Blakeman en la Conservadora. **No hay terceros en la boleta:** la Junta Electoral rechazó en mayo todas las peticiones de partidos no calificados. Gana la mayoría simple.

## Resumen del pronóstico (captura del 26-oct 05:30 UTC, corte 25-oct, 9 días a la elección)
| | Hochul (D) | Blakeman (R) | Votos por escrito |
|---|---|---|---|
| % de voto (IC80) | 56.3 (52.2–60.4) | 43.5 (39.4–47.7) | 0.15 |
| P(ganar) | **97.3 %** | **2.7 %** | — |

- Margen D−R +12.8 pp (σ 6.5). Solo encuestas: 98.0 %. Kalshi 94.0 %, Polymarket 96.0 % (peso 0.30).
- Cómo se llega: promedio de encuestas +15.5 · sesgo estatal −1.9 · mercados −0.8.
- **En la ventana de 21 días solo hay dos encuestas:** Quinnipiac (15–19 oct, 55–41, pesa 58 %) y ActiVote (1–23 oct, 59–41).

**La pieza más frágil es la ventana.** Las cuatro encuestas del 1–6 de octubre quedan fuera por pocos días: Marist +11, Emerson +12.7, OnMessage (R) +4 y Beacon (D) +22. Con ellas el promedio baja a ≈ +11.8 sin mercados («ventana 45 días» y «fechas por el punto medio»). P(Hochul) sigue en 98–99 % en todos los casos, pero el margen se mueve ~1.8 pp.

## 1. Fuentes
| Fuente | Estado | Decisión |
|---|---|---|
| Wikipedia (`2026_New_York_gubernatorial_election`) | En vivo; 30 encuestas | Fuente principal |
| 270toWin | En vivo; 10 encuestas, fechadas por publicación | Complementa |
| Excel `NUEVA_YORK_GOBERNADOR-v1.xlsx` (hoja «Histórico encuestas») | 26 encuestas generales, algunas con decimales | Base verificada; se publica como CSV (el Excel no se sube). Sus decimales reemplazan a los redondeos de Wikipedia cuando son compatibles |
| Kalshi `GOVPARTYNY-26` | En vivo (D y R; 3.9 M contratos en R) | Mezcla |
| Polymarket `new-york-governor-winner-2026` y `…-margin-of-victory-2026` | En vivo; márgenes = «Republican Wins» + 8 rangos del demócrata (partición completa, suma 1.09) | Mezcla y escenario |
| civicAPI | **No publica Nueva York** (404) | Se consulta en vivo por si empieza a hacerlo; diagnóstico opcional, no degrada |
| Junta Electoral de NY, Siena SRI | 403 / 404 desde GitHub Actions | No accesibles de forma automática |
| OnPoint Politics, PoliAgg | Solo promedios | No se agregan |
| FiveThirtyEight raw-polls | En vivo | Calibración |

**Correcciones de captura:**
- **Siena College Research Institute ≠ NYT/Siena.** En los demás estados «Siena» se unificaba con NYT/Siena; en NY la SRI tiene su propio historial en FiveThirtyEight (62 encuestas, casi todas de NY), y ahora conserva su efecto de casa.
- **Decimales del Excel:** Emerson 52.4–39.7 y McLaughlin 49.6–45.7, en lugar del 52–40 y 50–46 de Wikipedia.
- **Fecha de publicación de 270toWin:** Quinnipiac aparece el 21-oct; su campo fue del 15 al 19.

## 2. Electorado
- **Registro de partido** (NYPIRG con datos de la Junta Electoral, 2025):

| Región | Demócratas | Republicanos | Sin partido |
|---|---|---|---|
| Estado | 48.2 % | 22.4 % | 25.2 % |
| Ciudad de Nueva York | 65.9 % | 10.7 % | 21.0 % |
| Nassau, Suffolk y Westchester | 38.6 % | 28.2 % | 28.9 % |
| Resto del estado | 35.2 % | 31.2 % | 27.6 % |

- **Geografía del voto (Siena, ago-2026):** NYC Hochul 64 – 19; suburbios Blakeman 49 – 41; norte del estado prácticamente empatado.
- **Independientes:** Siena (sep) Blakeman 44 – 39 con 17 % indeciso; Quinnipiac (sep) Hochul 51 – 45.
- **Lealtad partidista:** Siena tiene a Hochul con 81 % de los demócratas y a Blakeman con 88 % de los republicanos.
- **Voto anticipado:** del 24-oct al 1-nov; la inscripción cerró el 24-oct. No hay datos automáticos (civicAPI no cubre NY).
- **2022:** Hochul ganó por 6.4 contra Zeldin (53.2 – 46.7, terceros 0.16 %). A estas alturas Siena la tenía +17; una Quinnipiac de finales de octubre con +4, entonces vista como atípica, fue la que acertó.

## 3. Indecisos
- En octubre son pocos: 2–8 % (Quinnipiac 2 %, Marist 5 %, Emerson 7.9 %). En septiembre Siena tenía 9 % y co/efficient 11 %.
- Blakeman sigue siendo poco conocido (40 % no lo conoce lo suficiente, Siena ago). Quinnipiac lo ve como su margen de crecimiento.
- 76 % de los votantes de Hochul y 83 % de los de Blakeman no cambiarían su voto (Quinnipiac sep).
- **Backtest:** 50/50 es lo mejor a nivel nacional. En NY la cuota R estimada (H3) es peor (3.097 contra 2.929) y el reparto proporcional (H2) también (3.252).
- Sin terceros en la boleta, el «otro» de las encuestas (1–2 %) se reparte como los indecisos.

## 4. Backtest (945 contiendas, 1998–2024, 20 de Nueva York; H = 9 días, ventana de 9 a 21 días)
| Variante | Nacional | Gobernadores | NY (20) | NY 2016+ (7) |
|---|---|---|---|---|
| **G · V11 + sesgo estatal contraído** | **3.304** | 3.514 | **2.929** | 2.397 |
| H8 · sin sesgo estatal | 3.438 | 3.477 | 3.419 (P = 0.06) | 2.528 |
| F1 · sesgo sin contraer | 3.389 | 3.731 | 3.093 | 2.363 |
| H2 · indecisos proporcionales | 3.543 | 3.824 | 3.252 | 2.382 |
| H3 · cuota R de indecisos | 3.336 | 3.524 | 3.097 | 2.427 |
| P3 · partidistas pesan la mitad | 3.313 | 3.520 | 2.933 (P = 0.45) | 2.399 |

**Errores de las encuestas en NY** (V11 sin sesgo; + = sobreestiman al demócrata): **6 de 20 pro-D**, pero el patrón cambió.
- **1998–2012: pro-R grandes:** −10.6 (gobernador 1998), −9.9, −8.5 (Senado 2006).
- **Desde 2014, sobre todo pro-D:** gobernador 2014 +9.2, presidente 2020 +9.5, gobernador 2022 +0.8, Senado 2022 +2.8, presidente 2024 +4.3, Senado 2024 +4.2.
- Con la vida media de 4 años pesan los errores recientes, así que hoy el sesgo es **+2.58 bruto pro-D**, contraído a **+1.95**.

**Sesgo estatal: validación estrictamente cronológica (2004–2024):**
| Ámbito | n | G «todas» | G «k ≥ 2» | G por cargo | Sin sesgo |
|---|---|---|---|---|---|
| Nacional | 757 | **3.132** | 3.137 | 3.259 (P = 0.004) | 3.369 (P = 0.002) |
| Nueva York | 16 | **2.487** | 2.646 (P = 0.02) | 2.841 (P = 0.10) | 2.718 (P = 0.21) |
| Nueva York gobernador | 4 | 3.631 | 3.808 | 2.745 | 2.644 |

**Decisión sobre el sesgo: se aplica, con la regla «todas».**
- Nueva York es el estado donde el sesgo más ayuda: LOYO 2.929 contra 3.419 (P = 0.06) y cronológico 2.487 contra 2.718.
- «k ≥ 2» y «por cargo» son peores en NY.
- Las 4 contiendas de gobernador prefieren no aplicarlo, pero son muy pocas para apartarse de la regla.
- **Sensibilidad leave-one-contest-out:** quitando una contienda, la corrección va de −1.43 (sin el presidente 2020) a −2.07 (sin el presidente 2016). El signo no cambia.

**Ventajas grandes:** la escala estimada es 1.00 y la variante con escala no mejora en NY (P = 0.44). No se ajusta.

**Terceros:** el backtest no conoce la boleta. En 2022 solo había dos candidatos y los terceros fueron 0.00 % en la base (0.16 % por escrito). Por eso se fijan en 0.15 % (sd 0.05), en lugar de la regla T4, que daría ~1.5 % con el «otro» de las encuestas. Solo afecta los porcentajes, no el margen ni la probabilidad.

## 5. Contexto de la campaña
- **Encuestas de octubre:**

| Encuesta | Campo | Población | Resultado |
|---|---|---|---|
| Quinnipiac | 15–19 oct | 1,167 LV | 55 – 41 |
| ActiVote | 1–23 oct | 400 LV | 59 – 41 |
| Marist | 1–4 oct | 1,361 RV | 53 – 42 |
| Emerson | 3–5 oct | 900 LV | 52.4 – 39.7 |
| OnMessage (R) | 1–6 oct | 1,000 LV | 50 – 46 |
| Beacon (D) | 1–6 oct | 820 RV | 53 – 31 |

  En septiembre, Siena 50 – 41 (11–17 sep) y Quinnipiac 58 – 39 (17–20 sep).
- **Dinero:** Hochul y el Partido Demócrata estatal tenían $33.5 M en caja a fin de septiembre. Blakeman reportó $4.3 M en julio y entró al sistema de fondos públicos de contrapartida; los demócratas piden que no reciba el resto.
- **Debate:** el único debate fue el 13 de octubre.
- **Apoyos:** el alcalde de NYC Zohran Mamdani hace campaña con Hochul. Trump apoyó a Blakeman el 20 de diciembre de 2025, tras la retirada de Stefanik.
- **Temas:** asequibilidad y vivienda (Hochul 51 – 31 en vivienda), seguridad y migración (casi empatados), energía.
- **Fórmulas:** Adrienne Adams acompaña a Hochul como vicegobernadora y Todd Hood a Blakeman.

## 6. Mercados
- **Kalshi 94.0 % y Polymarket 96.0 %**, algo debajo de las encuestas corregidas (98.0 %). La mezcla baja el margen 0.8 pp.
- **El mercado de márgenes de Polymarket** centra el margen en +16.4 (σ 9.9), con 6.4 % para «gana el republicano». Es más que el final (+12.8) y casi igual al promedio sin sesgo (+15.5).
- Su volumen es bajo (~$11.5 mil), así que pesa como escenario, no en la mezcla.

## 7. Escenarios (P(Hochul); sin mercados salvo que se indique)
| Escenario | Margen | P |
|---|---|---|
| **Final (encuestas + mercados)** | +12.8 | **97.3 %** |
| Con sesgo, sin mercados | +13.6 | 98.0 % |
| Sin sesgo, sin mercados | +15.5 | 98.9 % |
| Sin sesgo, con mercados | +14.1 | 98.3 % |
| Sesgo solo con contiendas de gobernador (−0.45) | +15.1 | 98.8 % |
| Ventana de 45 días (7 firmas) | +11.8 | 99.3 % |
| Fechas por el punto medio del campo (6 firmas) | +11.8 | 99.1 % |
| Sin Quinnipiac | +12.4 | 99.2 % |
| Sin ActiVote | +11.0 | 98.4 % |
| Polymarket por rangos | +16.4 | 93.6 % |

Las ventanas más anchas bajan el margen pero suben la probabilidad: con más firmas, la σ cae (k = 7 contra 2).

## Fuentes
- [Fox 5 NY: Marist 1–4 oct](https://www.fox5ny.com/news/hochul-leads-blakeman-11-points-governors-contest-ny) · [Fox 5 NY: debate del 13-oct](https://www.fox5ny.com/election/ny-politics-midterm-elections-bruce-blakeman-kathy-hochul)
- [City & State: Quinnipiac 17–20 sep](https://www.cityandstateny.com/politics/2026/09/quinnipiac-poll-puts-hochul-19-points-over-blakeman/416168/) · [City & State: dinero en caja](https://www.cityandstateny.com/politics/2026/09/one-month-out-election-day-hochul-has-more-33-million-bank/416290/)
- [Siena SRI: encuesta de agosto](https://sri.siena.edu/?p=13843) · [CNY Central: Siena de agosto](https://cnycentral.com/news/local/govenror-kathy-hochul-lead-on-bruce-blakeman-slims-in-latest-siena-poll-vote-election-new-york-democrat-republican-politics) · [Spectrum News: Siena y Quinnipiac de septiembre, 2022](https://spectrumlocalnews.com/nys/central-ny/politics/2026/09/23/interpreting-polls-race-for-governor-)
- [NYPIRG: registro de votantes 2025](https://www.nypirg.org/pubs/202511/VOTER_ENROLLMENT_2025.pdf)
- [Wikipedia: 2026 New York gubernatorial election](https://en.wikipedia.org/wiki/2026_New_York_gubernatorial_election) · [270toWin](https://www.270towin.com/2026-governor-polls/new-york) · [Kalshi](https://kalshi.com) · [Polymarket](https://polymarket.com/event/new-york-governor-winner-2026)
