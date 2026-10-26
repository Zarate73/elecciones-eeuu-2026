# Illinois 2026 · Gobernador: investigación y modelo (25-oct-2026)

Elección general del 3 de noviembre: **JB Pritzker (D, gobernador desde 2019)** busca un tercer periodo contra **Darren Bailey (R, exsenador estatal)**, la revancha de 2022, que Pritzker ganó por 12.5 puntos. En la boleta también está **Collin Corbett (independiente, exconsultor republicano)**. Gana la mayoría simple.

## Resumen del pronóstico (fixtures del 25-oct, 9 días a la elección)
| | Pritzker (D) | Bailey (R) | Terceros |
|---|---|---|---|
| % de voto (IC80) | 56.2 (52.0–60.5) | 38.6 (34.3–42.8) | 5.2 (3.0–7.3) |
| P(ganar) | **99.5 %** | **0.5 %** | — |

- Margen D−R +17.6 pp (σ 6.6). Solo encuestas: 99.8 %. Kalshi 96.5 %, Polymarket 97.3 % (peso 0.30).
- Cómo se llega: promedio de encuestas +18.7 · sesgo estatal +1.2 · mercados −2.2.
- **Solo dos encuestas** en la ventana ampliada: PPP (30 sep–1 oct, +20) y ActiVote (2–22 oct, +18). La ventana se amplía porque solo ActiVote termina en los últimos 21 días.

**La duda no es quién gana, sino por cuánto.** Las piezas que mueven el margen son la mezcla con mercados (−2.2 pp) y el sesgo estatal (+1.2 pp). Ninguna cambia al ganador.

## 1. Fuentes
| Fuente | Estado | Decisión |
|---|---|---|
| Wikipedia (`2026_Illinois_gubernatorial_election`) | En vivo; 3 encuestas generales (una anterior a la primaria) | Fuente principal |
| 270toWin | En vivo; 2 encuestas, con la fecha de publicación | Complementa |
| Excel `ILLINOIS_GOBERNADOR-v1.xlsx` (hoja «Histórico encuestas») | 2 encuestas generales (Victory Research, PPP) | Base verificada; se publica como CSV (el Excel no se sube) |
| Kalshi `GOVPARTYIL-26` | En vivo (D y R; 163 mil contratos negociados en D) | Mezcla |
| Polymarket `illinois-governor-winner-2026` y `…-margin-of-victory-2026` | En vivo; márgenes = «Republican Wins» + 7 rangos del demócrata (partición completa, suma 1.0125) | Mezcla y escenario |
| civicAPI `early-vote/IL` | En vivo, por condado y ciudad, **sin partido** | Diagnóstico del volumen |
| FiveThirtyEight raw-polls | En vivo | Calibración |
| OnPoint Politics, PoliAgg, civicAPI forecast | Revisadas | No se agregan: solo publican promedios (OnPoint +19.6, PoliAgg ~+24) hechos con las mismas encuestas |
| FiftyPlusOne, RealClearPolitics, Junta Estatal de Elecciones | 404 / 403 / páginas sin datos | No accesibles de forma automática |

**No hay fuentes que agregar.** El cuello de botella es que casi no hay encuestas públicas: la carrera no se considera competitiva y los medios encargan pocas.

**Datos de captura que se corrigen:**
- **PPP:** Wikipedia trae Corbett 6 % e indecisos 6 %; el Excel junta «indecisos / otros» 12 %. Se usa la de Wikipedia, que reporta terceros.
- **Victory Research** (20–24 nov 2025, 54.3–34) es anterior a la primaria del 17-mar y no entra en el promedio.
- **ActiVote** reparte a los indecisos (59–41, D + R = 100).

## 2. Electorado
- **Sin registro partidario.** Como Texas, Illinois no registra partido: civicAPI solo da volumen.
- **Voto ya emitido:** 786,257 al 25-oct (443,833 por correo y 342,424 en persona), el **19 % del total de votos de 2022** (4.10 M).

| Región | % del voto ya emitido |
|---|---|
| Ciudad de Chicago | 11.4 |
| Cook suburbano | 17.5 |
| Condados conurbados (DuPage 9.3, Lake 8.4, Kane 5.6, Will 5.4, McHenry 3.4) | 32.1 |
| Resto del estado (downstate) | ~39 |

- **El volumen por región es diagnóstico, no intención de voto.** Chicago abrió centros de votación en sus 50 distritos el 19-oct, así que su peso todavía puede subir.
- **Composición de la muestra PPP** (569 votantes): D 42 %, R 27 %, independientes 30 %. Aprobación de Trump en Illinois: 33 – 61.
- **Antecedente de 2022:** el promedio de FiveThirtyEight daba Pritzker +14.3 y ganó por +12.5. El PPP de octubre de 2022 tenía Pritzker 49, Bailey 34, Schluter (L) 8.

## 3. Indecisos
- En las encuestas de 2026 los indecisos son 6 % (PPP) más Corbett 6 %. ActiVote no reporta indecisos.
- Con +18 a +20 en las encuestas, ni un reparto 100/0 de los indecisos hacia Bailey cambia al ganador.
- **Backtest:** 50/50 sigue siendo lo mejor a nivel nacional.
  - El reparto proporcional (H2) es el peor en IL (4.207) y a nivel nacional (P = 0.002).
  - La cuota R estimada (H3) es peor en IL (3.803).
- **Terceros:** T4 (solo encuestas que reportan) es la mejor regla en IL (MAE de terceros 1.04) y a nivel nacional. Hoy da 5.2 % a terceros, con Corbett en 6 %.

## 4. Backtest (945 contiendas, 1998–2024, 19 de Illinois; H = 9 días, ventana de 9 a 21 días)
| Variante | Nacional | Gobernadores | IL (19) | IL 2016+ (5) |
|---|---|---|---|---|
| **G · V11 + sesgo estatal contraído** | **3.304** | 3.514 | 3.660 | 1.929 |
| H8 · sin sesgo estatal | 3.438 (P = 0.08) | 3.477 | 3.233 (P = 0.75) | 2.003 |
| F1 · sesgo sin contraer | 3.389 | 3.731 | 3.979 | 1.921 |
| H2 · indecisos proporcionales | 3.543 | 3.824 | 4.207 | 2.069 |
| H3 · cuota R de indecisos | 3.336 | 3.524 | 3.803 | 1.888 |
| P2 · sin encuestas partidistas | 3.350 (P = 0.000) | 3.558 | 3.649 | 1.907 |

CRPS del margen (menor es mejor); entre paréntesis, P(variante mejor que G) por bootstrap de años.

**Errores de las encuestas en Illinois** (V11 sin sesgo; + = sobreestiman al demócrata): **8 de 19 pro-D.**
- El error cambia de signo; la autocorrelación año a año es 0.05.
- Los errores grandes son pro-R:
  - Senado 2008 (Durbin): −16.1;
  - 1998: −10.2 y −10.0;
  - Presidente 2020: −5.9.
- En 2022 los errores fueron +0.5 (gobernador) y −2.5 (Senado).

**Sesgo estatal: validación estrictamente cronológica (2004–2024):**
| Ámbito | n | G «todas» | G «k ≥ 2» | G por cargo | Sin sesgo |
|---|---|---|---|---|---|
| Nacional | 757 | **3.132** | 3.137 (P = 0.41) | 3.259 (P = 0.004) | 3.369 (P = 0.002) |
| Illinois | 14 | 2.827 | 2.824 (P = 0.53) | **2.692** (P = 0.81) | 2.742 (P = 0.63) |
| Illinois gobernador | 4 | 2.450 | 2.561 | 2.427 | 2.358 |
| Illinois 2016+ | 5 | **1.920** | — | — | 2.008 (P = 0.00) |

**Decisión sobre el sesgo:**
- **Se aplica, con la regla «todas»**, como en Texas, Pennsylvania y Nevada. La evidencia del estado no es significativa: «sin sesgo» es mejor con P = 0.63 y «por cargo» con P = 0.81, ambos con 14 contiendas. La nacional sí lo es: con sesgo P = 0.002; «por cargo» pierde con P = 0.004.
- Desde 2016, aplicar el sesgo es mejor en las 5 contiendas de IL.
- **Hoy el sesgo suma +1.2 pp a Pritzker** (bruto −1.60, contracción 0.75). Con «k ≥ 2» sumaría +0.56; con «solo gobernador» restaría 0.29.

**¿Las encuestas comprimen las ventajas grandes?** No.
- Escala estimada fuera de muestra b = 1.00.
- En 389 contiendas con ventaja ≥ 15 pp el líder ganó por 0.5 pp más de lo pronosticado.
- La variante con escala es peor a nivel nacional (P = 0.25), en IL (P = 0.18) y en ventajas grandes (P = 0.13). No se ajusta.

**Ventana ampliada:** hoy aplica. La emulación del backtest confirma que ampliar es mejor que no ampliar: 3.397 contra 3.670 en las 113 contiendas ampliadas. En ese régimen la cobertura del 80 % es 0.76, un poco corta. El escenario de k efectivo da 1.7 en lugar de 2 firmas.

## 5. Contexto de la campaña
- **Encuestas:**
  - PPP para Chicago News Weekly (30 sep–1 oct, 569): Pritzker 54, Bailey 34, Corbett 6, indecisos 6. En la misma encuesta, Senado: Stratton (D) 49 – Tracy (R) 36.
  - ActiVote (2–22 oct, 400 LV): 59 – 41.
  - Victory Research (nov-2025): 54.3 – 34. Aprobación de Pritzker: 52 – 41.
- **Dinero:**
  - Pritzker gastó $23.8 M entre julio y septiembre contra $0.94 M de Bailey (25 a 1). Entró a octubre con $44.4 M; Bailey, con $0.48 M.
  - Pritzker ha puesto más de $430 M en sus tres campañas. Richard Uihlein, que financió $12 M de Bailey en 2022, le ha dado $6,900.
- **Temas:**
  - Bailey: costo de vida, impuesto a la propiedad (tope de 1 %), derogar la SAFE-T Act y el estadio de los Bears.
  - Pritzker: lo ataca por su postura contra el aborto y por los libros de texto de la escuela cristiana de Bailey.
  - Compañero de fórmula de Bailey: Aaron Del Mar, presidente del Partido Republicano del condado de Cook.
- **Senado:** asiento abierto (se retira Durbin): Juliana Stratton (D) contra Don Tracy (R).

## 6. Mercados
- **Kalshi y Polymarket coinciden** en un 96.5–97.3 % para Pritzker, algo debajo del 99.8 % de las encuestas.
- **El mercado de márgenes de Polymarket** centra el margen en +20.2 (σ 9.4). Es más que el promedio de encuestas, con un 2.7 % para «gana el republicano».
- **Por eso la mezcla baja el margen** del pronóstico (de +19.8 a +17.6): con probabilidades cercanas a 1, mover la probabilidad un punto mueve mucho el margen.
- **«Sin mercados» (+19.8) y Polymarket por rangos (+20.2) son lecturas igual de defendibles del margen,** igual que en Pennsylvania. El peso de 0.30 se validó para la probabilidad, incluso en mercados extremos (Arizona 2024), no para el margen.

## 7. Escenarios (P(Pritzker); sin mercados salvo que se indique)
| Escenario | Margen | P |
|---|---|---|
| **Final (encuestas + mercados)** | +17.6 | **99.5 %** |
| Con sesgo, sin mercados | +19.8 | 99.8 % |
| Sin sesgo, sin mercados | +18.6 | 99.7 % |
| Sin sesgo, con mercados | +16.9 | 99.3 % |
| Sin ActiVote (solo PPP) | +20.4 | 99.0 % |
| Sin PPP (solo ActiVote) | +19.6 | 98.7 % |
| Peso de mercados 0.50 | +16.1 | 99.1 % |
| Polymarket por rangos | +20.2 | 97.3 % |

## Fuentes
- [Ballotwire: encuesta PPP / Chicago News Weekly, 30 sep–1 oct](https://www.ballotwire.com/news/pritzker-up-20-over-bailey-as-democrats-lead-across-illinois)
- [Capitol News Illinois: campaña de Bailey y ataques de Pritzker (7-oct)](https://capitolnewsillinois.com/news/bailey-trying-to-stay-on-message-as-attacks-from-pritzker-mount/)
- [Chicago Sun-Times: gasto 25 a 1 (16-oct)](https://chicago.suntimes.com/elections/2026/10/16/jb-pritzker-darren-bailey-illinois-governor-race-campaign-cash-spending)
- [Loyola Phoenix: Pritzker, Bailey y Corbett (21-oct)](https://loyolaphoenix.com/2026/10/pritzker-bailey-and-corbett-face-off-in-illinois-governors-race/)
- [Fox 32: Victory Research, nov-2025](https://www.fox32chicago.com/news/illinois-jb-pritzker-poll-nov-25)
- [Fox 32: fechas del voto anticipado](https://www.fox32chicago.com/news/election-2026-general-early-voting-illinois)
- [Capitol News Illinois: voto anticipado y promedio de 2022](https://capitolnewsillinois.com/news/early-voting-expands-as-campaign-season-enters-final-two-weeks/) · [WBEZ: PPP de octubre de 2022](https://www.wbez.org/stories/pritzker-leading-big-over-bailey-poll-finds/46dad98e-e317-4cd5-aaaf-b1f17af725f6)
- [Wikipedia: 2026 Illinois gubernatorial election](https://en.wikipedia.org/wiki/2026_Illinois_gubernatorial_election) · [270toWin](https://www.270towin.com/2026-governor-polls/illinois) · [Kalshi](https://kalshi.com) · [Polymarket](https://polymarket.com/event/illinois-governor-winner-2026) · [civicAPI](https://civicapi.org)
