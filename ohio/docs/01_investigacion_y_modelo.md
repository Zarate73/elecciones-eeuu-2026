# Ohio 2026 · Gobernador: investigación y modelo (26-oct-2026)

Elección general del 3 de noviembre. El gobernador Mike DeWine (R) deja el cargo por límite de mandatos.
- **Amy Acton (D):** exdirectora de Salud del estado durante la pandemia; su compañero de fórmula es David Pepper.
- **Vivek Ramaswamy (R):** empresario de biotecnología de Cincinnati, con apoyo de Trump; su compañero de fórmula es Rob McColley.
- **Don Kissick (Libertario):** también en la boleta, con James Mills.

Gana la mayoría simple. Hay recuento automático si el margen es ≤ 0.25 % de los votos.

## Resumen del pronóstico (captura del 26-oct 21:20 UTC, corte 26-oct, 8 días a la elección)
| | Acton (D) | Ramaswamy (R) | Terceros |
|---|---|---|---|
| % de voto (IC80) | 48.7 (45.5–51.9) | 48.1 (44.9–51.3) | 3.1 (1.0–5.3) |
| P(ganar) | **55.0 %** | **45.0 %** | — |

- **Margen D−R:** +0.6 pp (σ 4.8; IC80 −5.5 a +6.6). P(recuento automático, |margen| ≤ 0.25) = 4.3 %.
- **Cómo se llega:** promedio de encuestas +3.0, sesgo estatal −4.0, mercados +1.7.
- **Solo encuestas:** P(Acton) **40.8 %** (margen −1.1).
- **Mercados:** Kalshi 81.7 % y Polymarket 82.9 % (normalizados D / (D + R)). La mezcla con peso 0.30 sube la probabilidad final a 55 %.

**La pieza central es el choque entre el sesgo histórico de Ohio y los mercados.**
- **Sin el sesgo estatal**, las encuestas dan Acton +3.0 y P = 74 %; con mercados, 77 %. Es lo mismo que dicen los mercados: el rango de márgenes de Polymarket centra en +3.9.
- **Con el sesgo**, el modelo resta 4.0 pp. En Ohio las encuestas sobreestimaron al demócrata **en todas las contiendas desde 2014**, por +2.9 a +8.1 pp. También pasó en 2018, un año de ola demócrata: gobernador +5.4 y Senado +6.1.
- **El backtest favorece aplicar el sesgo con claridad** (§4). Los mercados, en cambio, no parecen descontarlo, o incorporan el efecto del anuncio del 19-oct (§5), que casi ninguna encuesta alcanzó a medir.

## 1. Fuentes
| Fuente | Estado | Decisión |
|---|---|---|
| Wikipedia (`2026_Ohio_gubernatorial_election`) | En vivo; 39 filas, con versiones LV/RV y con o sin indecisos asignados | Fuente principal |
| 270toWin | En vivo; 10 encuestas, fechadas por publicación | Complementa (Marist 20-oct = campo 15–18 oct) |
| Excel `OHIO_GOBERNADOR-v1.xlsx` (hoja «Histórico encuestas») | 27 encuestas generales hasta el 6-oct | Base verificada; se publica como CSV (el Excel no se sube). Aporta Wedgewood (11–13 ago), que Wikipedia no trae |
| Kalshi `GOVPARTYOH-26` | En vivo (D 0.82/0.83; volumen 1.8 M) | Mezcla |
| Polymarket `ohio-governor-winner-2026` y `ohio-governor-margin-of-victory-2026` | En vivo; márgenes = 5 rangos de cada lado (partición completa, suma 1.12); «Person A» y «Other» están inactivos y se descartan | Mezcla y escenario |
| civicAPI `early-vote/OH` | En vivo; 88 condados, **sin partido** (Ohio no tiene registro partidario) | Diagnóstico: volumen |
| On Point Politics | JSON en vivo; promedio Acton +4.0 al 20-oct | Solo para verificar cifras. Su encuesta propia («On Point Polling», 17-oct, 47.9–43.1) no publica el periodo de campo: no se agrega |
| Secretaría de Estado de Ohio | 403 desde GitHub Actions | No accesible de forma automática |
| FiveThirtyEight raw-polls | En vivo | Calibración |

**Correcciones de captura:**
- **Alias:**
  - el «Siena College» de 270toWin es NYT/Siena (en Ohio no encuesta el Siena Research Institute);
  - «CNN / SSRS» = SSRS (32 encuestas en FiveThirtyEight);
  - «Fox News» = Beacon/Shaw;
  - «New River / GSG» = GS Strategy Group/New River (encargada por Cook);
  - BGSU/YouGov aparece con tres nombres;
  - «Hart Research (D)» = Hart Research Associates.
- **Marist 15–18 oct (LV):** el comunicado dice 50–43; Wikipedia publica 51–43. Se corrige y n LV = 883, el que implica su margen de error (±4.5 frente a ±3.9 de los 1,176 RV).
- **ActiVote 27 sep–19 oct:** 48.6–51.4 en activote.net; Wikipedia y 270toWin redondean a 49–51.

## 2. Electorado
- **Sin registro partidario.** La afiliación sale de la última primaria en que votó cada elector, así que el voto anticipado solo da volumen.
- **Tendencia:**

| Elección | Resultado |
|---|---|
| Presidente 2020 | Trump +8.0 |
| Presidente 2024 | Trump +11.2 (55.1–43.9) |
| Senado 2022 | Vance +6.1 (53.0–46.9) |
| Senado 2024 | Moreno +3.6 sobre Sherrod Brown (50.1–46.5) |
| Gobernador 2018 | DeWine +3.7 (50.4–46.7) |
| Gobernador 2022 | DeWine +25.0 (62.4–37.4) |
| Issue 1 (aborto, 2023) | Aprobado con 57 % |

  Ohio vota republicano en lo federal desde 2016, pero un demócrata fuerte puede acercarse (Brown 2024).
- **Participación:** 52.3 % en 2022 (4,134,877 votos para gobernador) y 71.7 % en 2024.
- **Independientes:**
  - Marist (15–18 oct, LV): Acton 53 – 34;
  - CNN/SSRS: Acton +27;
  - BGSU (sep): Acton 45 – 34.

  Trump ganó a los independientes de Ohio por 2 en 2024.
- **Lealtad partidista:**
  - BGSU (sep): 96 % de los demócratas con Acton y 87 % de los republicanos con Ramaswamy; Kissick se lleva 5 % de los republicanos y otro 3 % dice que votará por alguien más;
  - CNN: Acton gana 7 % de los republicanos y Ramaswamy 2 % de los demócratas.
- **Imagen:** BGSU (oct) da favorabilidad neta −1 a Acton y −10 a Ramaswamy. El 51 % dice que Ramaswamy hizo más campaña negativa. El entusiasmo demócrata dobla al republicano (BGSU, sep).
- **Voto ya emitido (civicAPI, 26-oct):**
  - 1,084,305 votos (452,169 por correo y 632,136 en persona), el 26 % del total de 2022;
  - Cuyahoga concentra el 16 % del correo y Franklin el 9.7 % del total;
  - de 725,791 boletas solicitadas se ha devuelto el 62 %.

  Es solo volumen.

## 3. Indecisos y terceros
- **Pocos indecisos:** en octubre, 1–8 % (co/efficient 8 %, SSRS 1 %, Beacon 1 %, Marist LV ~2 %, RedBox 3 %).
- **Kissick:** 3 % en co/efficient; los «otros» reportados promedian 3.2 % en la ventana.
- **Backtest:**
  - indecisos 50/50 es lo mejor (OH: G 2.066; reparto proporcional 2.217; cuota R 2.136);
  - para terceros, la regla T4 (a + c·otros, solo encuestas que los reportan) es la mejor en OH (MAE 1.41) y a nivel nacional (1.36).
- **Indecisos republicanos:** la base de Ramaswamy es menos leal (Kissick y «otros» le quitan 8 % de los republicanos en BGSU). Si esos votantes vuelven a casa, el 50/50 subestimaría a Ramaswamy. La regla H3 (cuota R estimada) no mejora en Ohio, así que no se aplica.

## 4. Backtest (957 contiendas, 1998–2024, 24 de Ohio; H = 8 días, ventana de 8 a 21 días)
| Variante | Nacional | Gobernadores | OH (24) | OH 2016+ (9) | OH gobernador (7) |
|---|---|---|---|---|---|
| **G · V11 + sesgo estatal contraído** | **3.249** | 3.433 | **2.066** | 2.134 | 2.586 |
| H8 · sin sesgo estatal | 3.381 | 3.375 | 2.478 (P = 0.05) | 3.562 | 2.830 |
| F1 · sesgo sin contraer | 3.328 | 3.639 | 2.101 | 2.013 | 2.594 |
| H2 · indecisos proporcionales | 3.464 | 3.712 | 2.217 | 2.280 | 2.638 |
| H3 · cuota R de indecisos | 3.277 | 3.438 | 2.136 | 2.064 | 2.740 |
| P2 · sin encuestas partidistas | 3.287 (P = 0.000) | 3.477 | 2.047 | 2.089 | 2.526 |
| P3 · partidistas pesan la mitad | 3.257 | 3.442 | 2.053 | 2.091 | 2.560 |

**Errores de las encuestas en OH** (V11 sin sesgo; + = sobreestiman al demócrata): **16 de 24 pro-D**.
- **1998–2000: pro-R** (−1.3 a −7.8).
- **2002–2012: mixtos y chicos.**
- **Desde 2014, todos pro-D:**

| Contienda | Error |
|---|---|
| Gobernador 2014 | +6.3 |
| Presidente 2016 | +6.0 |
| Senado 2016 | +7.1 |
| Gobernador 2018 | +5.4 |
| Senado 2018 | +6.1 |
| Presidente 2020 | +6.3 |
| Gobernador 2022 | +8.1 |
| Senado 2022 | +4.3 |
| Presidente 2024 | +4.3 |
| Senado 2024 | +2.9 |

- **Error de Ohio frente al nacional:** +5.6 en 2018 y +4.4 en 2022. Ohio es peor que el promedio nacional, no solo un reflejo del error de cada año.
- Con la vida media de 4 años, el sesgo bruto es **+4.56 pro-D**; contraído, **+4.04**.

**Sesgo estatal: validación estrictamente cronológica (2004–2024):**
| Ámbito | n | G «todas» | G «k ≥ 2» | G por cargo | Sin sesgo |
|---|---|---|---|---|---|
| Nacional | 765 | **3.077** | 3.094 | 3.202 (P = 0.004) | 3.317 (P = 0.001) |
| Ohio | 19 | 1.802 | **1.799** | 2.019 (P = 0.010) | 2.464 (P = 0.002) |
| Ohio gobernador | 5 | 2.247 | 2.261 | 2.507 | 3.089 (P = 0.08) |
| Ohio 2016+ | 9 | 2.172 | — | — | 3.632 (P = 0.000) |

**Decisión sobre el sesgo: se aplica, con la regla «todas».**
- Ohio es uno de los estados donde el sesgo más ayuda, en LOYO y en el cronológico.
- «k ≥ 2» empata (LOYO 2.048, cronológico 1.799) y da casi la misma corrección (−3.96).
- «Por cargo» es peor.
- **Sensibilidad leave-one-contest-out:** la corrección va de −3.60 (sin el gobernador 2022) a −4.29 (sin el Senado 2024). El signo no cambia.

**Otras decisiones:**
- **Encuestas partidistas:** se quedan con su peso (regla G). Excluirlas mejora apenas en OH (2.047 frente a 2.066), pero a nivel nacional empeora con P = 0.000. Queda como escenario.
- **Ventajas grandes:** la escala estimada es 1.004; no se ajusta.
- **Ventana:** hay 6 encuestadoras en los últimos 21 días, así que no se amplía.

## 5. Contexto de la campaña
- **Encuestas de octubre** (ventana desde el 13-oct, en negritas):

| Encuesta | Campo | Población | Resultado |
|---|---|---|---|
| **RedBox Research (D)** | **20–23 oct** | **2,998 LV** | **48 – 44** |
| **Verasight/VoteHub** | **1–20 oct** | **531 LV** | **46 – 45** |
| **Beacon (D)/Shaw (R) — Fox News** | **15–19 oct** | **1,592 LV** | **50 – 48** |
| **ActiVote** | **27 sep–19 oct** | **400 LV** | **48.6 – 51.4** |
| **Marist** | **15–18 oct** | **883 LV** | **50 – 43** |
| **GS Strategy/New River — Cook** | **9–13 oct** | **959 LV** | **49 – 44** |
| BGSU/YouGov | 29 sep–9 oct | 1,000 LV | 50 – 44 |
| co/efficient (R) | 5–6 oct | 925 LV | 43 – 45 |
| CNN/SSRS | 29 sep–5 oct | 760 LV | 50 – 42 |
| NYT/Siena | 22 sep–1 oct | 616 LV | 49 – 45 |

- **El anuncio de la madre (19–20 oct).** La campaña de Ramaswamy difundió un anuncio con Donna Arthur, la madre de Acton, de quien está distanciada desde 1978. El anuncio omite que Acton fue retirada de su custodia a los 12 años. Tenía detrás una compra de $4 millones.
  - DeWine lo calificó de «profundamente preocupante»; Husted se desmarcó.
  - Trump lo elogió y Vance pidió a los republicanos «dejar de quejarse».
  - Ramaswamy no lo retiró, pero el 24-oct pasó a una versión más corta.
  - Obama hizo campaña en Ohio el 24-oct; Cook movió la contienda hacia Acton el 23-oct.
  - Kalshi pasó de 69 % (19-oct) a 76 % (21-oct) y a 82–83 % (26-oct).
  - La única encuesta posterior al anuncio es RedBox (D), de 20 a 23 de octubre.
- **Dinero:** Ramaswamy y sus aliados gastaron o reservaron más de $97 M en TV y radio, más del triple que los demócratas (Axios, 20-oct). En la caja de junio, Ramaswamy tenía $30.7 M y Acton $8.1 M.
- **Debates:** Acton se negó a debatir; no hubo ninguno.
- **Trump:** respaldó a Ramaswamy y hizo mítines en Vandalia (3-oct) y Youngstown (12-oct).
- **Senado especial (correlacionado):** Sherrod Brown (D) frente a Jon Husted (R). Marist LV: Brown 48 – 44.
- **Calificaciones:** Cook, Sabato e Inside Elections la tenían como Tossup a inicios de octubre; Silver Bulletin, Lean D.

## 6. Mercados
- **Kalshi 81.7 % y Polymarket 82.9 %**, muy por encima de las encuestas corregidas (40.8 %) y algo por encima de las encuestas sin corregir (73.9 %).
- **Mercado de márgenes de Polymarket:** P(D) 77.5 %, margen centrado en +3.9 (σ 6.8). Es casi el promedio de encuestas sin corregir (+3.0). Su volumen es bajo (~$34 mil).
- **Lectura:**
  - o los mercados no descuentan el sesgo histórico de Ohio;
  - o incorporan información posterior a casi todas las encuestas (el anuncio);
  - o las dos cosas.

  El modelo no reoptimiza el peso con un solo año: usa 0.30, estimado con las 40 contiendas de 2024 (ver `../arizona/docs/03_peso_mercados.md`). Los escenarios de 0.15 y 0.50 muestran el rango.

## 7. Escenarios (P(Acton); sin mercados salvo que se indique)
| Escenario | Margen | P | P con mercados |
|---|---|---|---|
| **Final (encuestas + mercados)** | +0.6 | — | **55.0 %** |
| Con sesgo, sin mercados | −1.1 | 40.8 % | 55.0 % |
| Sin sesgo, sin mercados | +3.0 | 73.9 % | 76.7 % |
| Sesgo sin contraer (−4.56) | −1.6 | 36.6 % | 51.9 % |
| Sesgo a la mitad (−2.02) | +0.9 | 58.1 % | 66.6 % |
| Sesgo solo con contiendas de gobernador (−3.71) | −0.7 | 43.6 % | 56.9 % |
| Sin RedBox (D), que pesa 33 % | −1.6 | 37.2 % | 52.4 % |
| Sin encuestas de patrocinio partidista | −1.6 | 37.4 % | 52.5 % |
| Ajuste partidista por patrocinador | −1.8 | 35.0 % | 50.7 % |
| Fechas por el punto medio del campo | −0.4 | 47.4 % | 59.6 % |
| Ventana de 45 días (13 firmas) | −1.1 | 39.1 % | 53.8 % |
| Peso de mercados 0.15 / 0.50 | −0.3 / +1.7 | — | 47.9 % / 64.2 % |
| Polymarket por rangos | +3.9 | 77.5 % | — |

## Fuentes
- [Wikipedia: 2026 Ohio gubernatorial election](https://en.wikipedia.org/wiki/2026_Ohio_gubernatorial_election) · [270toWin](https://www.270towin.com/2026-governor-polls/ohio) · [Kalshi](https://kalshi.com) · [Polymarket](https://polymarket.com/event/ohio-governor-winner-2026) · [On Point Politics](https://onpointpolitics.us/polls/oh/governor)
- [Marist: Ohio, octubre 2026](https://maristpoll.marist.edu/polls/midterm-elections-in-ohio-october-2026/) · [ActiVote: Ohio](https://www.activote.net/polls/2026/oh-governor/) · [News From The States: BGSU de septiembre](https://www.newsfromthestates.com/article/still-anyones-ball-game-bowling-green-poll-finds-statistical-tie-ohios-race-governor)
- [Newsweek: récord negativo de Ramaswamy (19-oct)](https://www.newsweek.com/vivek-ramaswamy-breaks-unwanted-record-in-ohio-race-vs-amy-acton-12590201) · [Newsweek: encuestas de octubre](https://www.newsweek.com/vivek-ramaswamy-gets-boost-after-five-ohio-polling-blows-in-a-row-12544047) · [Newsweek: mítines de Trump](https://www.newsweek.com/trump-husted-ramaswamy-ohio-rally-polls-show-12559293)
- [Axios Cleveland (20-oct)](https://www.axios.com/local/cleveland/2026/10/20/amy-acton-vivek-ramaswamy-ohio-governor-election-preview) · [Al Jazeera: el anuncio (24-oct)](https://www.aljazeera.com/news/2026/10/24/has-vivek-ramaswamys-attack-ad-against-amy-acton-backfired) · [DeFi Rate: Kalshi 76 % (21-oct)](https://defirate.com/news/acton-kalshi-ohio-governor-ramaswamy-ad-sparks-backlash/)
- civicAPI (`early-vote/OH`), FiveThirtyEight raw-polls
