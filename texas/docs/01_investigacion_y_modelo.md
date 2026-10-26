# Texas 2026 · Gobernador: investigación y modelo (25-oct-2026)

Elección general del 3 de noviembre: **Greg Abbott (R, gobernador desde 2015)** busca un cuarto periodo contra **Gina Hinojosa (D, representante estatal por Austin)**. En la boleta también está Pat Dixon (libertario). Gana la mayoría simple; no hay segunda vuelta en la general.

## Resumen del pronóstico (fixtures del 25-oct, 9 días a la elección)

> **Actualización (revisión del 25-oct, v1.1.0):** se recuperó la segunda encuesta de ActiVote (17–21 oct). El promedio pasa de −3.11 a −3.23 y P(Hinojosa) de 14.6 % a 14.2 %. Detalle en [`02_revision_externa_2026-10-25.md`](02_revision_externa_2026-10-25.md).
| | Hinojosa (D) | Abbott (R) | Terceros |
|---|---|---|---|
| % de voto (IC80) | 46.6 (43.6–49.6) | 51.2 (48.2–54.1) | 2.2 (0.1–4.3) |
| P(ganar) | **14.6 %** | **85.4 %** | — |

- Margen D−R −4.5 pp (σ 4.4). Solo encuestas: 10.0 %. Kalshi 33.2 %, Polymarket 31.5 % (peso 0.30).
- Cómo se llega: promedio de encuestas −3.1 · sesgo estatal −2.5 · mercados +1.1.
- 9 encuestadoras en la ventana (13–20 oct); la más reciente es Verasight/VoteHub (20-oct).

**La pieza decisiva es el sesgo estatal.** Sin él, P(Hinojosa) sube a 23 % (26 % con mercados). El backtest de Texas no distingue entre las dos opciones; el nacional sí favorece aplicarlo (sección 4).

## 1. Fuentes
| Fuente | Estado | Decisión |
|---|---|---|
| Wikipedia (`2026_Texas_gubernatorial_election`) | En vivo, la más completa (incluye versiones LV y RV) | Fuente principal |
| 270toWin | En vivo | Complementa; rotula «YouGov» encuestas de patrocinadores (UT/Texas Politics Project, CBS): se deduplican |
| Excel `TEXAS_GOBERNADOR.xlsx` (hoja «Histórico encuestas») | 50 encuestas verificadas | Base verificada; se publica como CSV (el Excel no se sube) |
| Kalshi `GOVPARTYTX-26` | En vivo (D y R) | Mezcla |
| Polymarket `texas-governor-winner-2026` y `…-margin-of-victory-2026` | En vivo; el de márgenes es partición completa D/R (suma 1.005) | Mezcla y escenario |
| civicAPI `early-vote/TX` | En vivo, por condado, **sin partido** | Diagnóstico del volumen |
| FiveThirtyEight raw-polls | En vivo | Calibración |
| OnPoint Politics, Poliagg, Texas SOS | Revisadas | No se agregan: replican Wikipedia (OnPoint sirvió para confirmar que el «YouGov» de 270toWin, n 1,460, es CBS/YouGov) y la Secretaría de Estado no publica el voto anticipado en un formato estable |

**Correcciones de captura hechas en el paquete:**
- **Duplicados:** se elige la candidata más cercana en fecha. Antes, Beacon/Shaw (Fox) del 19-oct (47–52 LV, n 1,398) se pegaba a la del 28-sep (mismas cifras) y la encuesta más reciente de Fox desaparecía.
- **Alias:** Texas A&M/ReconMR/Siena → `reconmr`; UH Hobby School → `universityofho`; Cook Political Report → GS Strategy/New River (misma encuesta del 13-oct); «Texas Politics Project» por nombre (la clave de 14 letras chocaba con UT Tyler).
- **n faltante:** Marist 8–11 oct LV publica «TBA». Se imputa 600 y queda marcado; con el margen de error de ±4.9 y el efecto de diseño de su versión RV, el n real ronda 550–600.

## 2. Electorado
- **Sin registro partidario.** Texas no registra partido, así que el voto anticipado no se puede leer por partido: civicAPI solo da volumen.
- **Voto ya emitido:** 4.13 millones al 25-oct (3.93 M en persona y 0.20 M por correo), el **51 % del total de votos de 2022** (8.10 M). Harris aporta 13.2 %. El voto anticipado va del 19 al 30 de octubre, y Mark Jones (Rice) estima que entre 60 % y 75 % del voto se emitirá en ese periodo (CBS Austin).
- **Composición de la muestra (UH Hobby, 10–14 oct, 2,000 LV):** republicanos 42 %, demócratas 31 %, independientes 23 %.
- **Subgrupos (UMass Lowell/YouGov, 18–28 sep, Newsweek):**
  - hispanos: Hinojosa 51 – Abbott 43;
  - independientes: Hinojosa 39 – Abbott 26, con 21 % indecisos;
  - blancos: Abbott 56 – 35; mayores de 65: Abbott 59 – 37; hombres: Abbott +12.
- **YouGov (28 sep–5 oct):** brecha de edad muy fuerte (18–29: Hinojosa 64 – 30; 65+: Abbott 61 – 36) y por sexo (mujeres Hinojosa +10, hombres Abbott +10). Aprobación de Trump: 44 – 56.
- **Latinos:** en algunas encuestas del verano Hinojosa llegó a +38 entre latinos, más que O'Rourke en 2022 (Reuters).

## 3. Indecisos
- En las encuestas de octubre los indecisos son pocos: 1–6 % (UH 3 %, YouGov 5 %, UMass Lowell 6 %). Además, 13 % no conoce lo suficiente a Hinojosa para opinar (UH).
- Los indecisos se concentran en independientes (21 % en UMass Lowell), que hoy se inclinan por Hinojosa. Los republicanos, en cambio, tienen más espacio para «volver a casa».
- **Backtest:** el reparto 50/50 es el mejor en Texas y a nivel nacional.
  - Reparto proporcional (H2): el peor en TX (CRPS 4.182 contra 3.523) y a nivel nacional (P = 0.002).
  - Cuota R estimada (H3): peor en TX (3.594) y nacional (P = 0.14).
- **Decisión:** 50/50. Con 3–5 % de indecisos, una cuota 60/40 movería el margen 0.3–0.5 pp, muy por debajo de σ (4.4).

## 4. Backtest (945 contiendas, 1998–2024, 20 de Texas; H = 9 días, ventana de 9 a 21 días)
| Variante | Nacional | Gobernadores | TX (20) | TX 2016+ (8) |
|---|---|---|---|---|
| **G · V11 + sesgo estatal contraído** | **3.304** | 3.514 | 3.523 | 2.950 |
| H8 · sin sesgo estatal | 3.438 (P = 0.08) | 3.477 | 3.028 (P = 0.85) | 2.914 |
| F1 · sesgo sin contraer | 3.389 | 3.731 | 4.100 | 3.009 |
| H2 · indecisos proporcionales | 3.543 | 3.824 | 4.182 | 3.164 |
| P2 · sin encuestas partidistas | 3.350 (P = 0.000) | 3.558 | 3.339 (P = 0.98) | 2.901 |
| P2s · P2 sin sesgo | 3.475 | 3.521 | **2.874** | **2.836** |

CRPS del margen (menor es mejor); entre paréntesis, P(variante mejor que G) por bootstrap de años.

**Errores de las encuestas en Texas** (V11 sin sesgo; + = sobreestiman al demócrata): **14 de 20 pro-D.**

| Año | Contienda | Error |
|---|---|---|
| 2018 | Gobernador / Senado | −6.2 / −3.2 (subestimaron a O'Rourke y Valdez) |
| 2020 | Presidente / Senado | +4.9 / +4.0 |
| 2022 | Gobernador | +2.1 |
| 2024 | Presidente / Senado | **+7.2 / +6.1** |

El error relativo de TX (TX − nacional) tiene autocorrelación de 0.52: es persistente pero cambia de signo (2018 contra 2024).

**Sesgo estatal: validación estrictamente cronológica (2004–2024; solo años anteriores, como en producción):**
| Ámbito | n | G «todas» | G «k ≥ 2» | G por cargo | Sin sesgo |
|---|---|---|---|---|---|
| Nacional | 757 | **3.132** | 3.137 (P = 0.41) | 3.259 (P = 0.004) | 3.369 (P = 0.002) |
| Gobernadores | 218 | **3.147** | 3.154 | 3.213 | 3.270 |
| Texas | 16 | 2.306 | 2.562 (P = 0.07) | **2.230** (P = 0.82) | 2.309 (P = 0.49) |
| Texas gobernador | 4 | 2.328 | 2.369 | 2.297 | 2.196 |

**Decisión sobre el sesgo:**
- **Se aplica, con la regla «todas».** En el cronológico de Texas aplicarlo o no empata (2.306 contra 2.309). A nivel nacional aplicarlo es claramente mejor (P = 0.002). Es la misma situación de Pennsylvania y se resuelve igual: con 16 contiendas el estado no tiene información para apartarse de la regla nacional.
- **El LOYO de Texas favorece no aplicarlo (P = 0.85), pero no es la prueba relevante.** Usa años futuros: el sesgo pro-D de 2020–2024 empeora la evaluación de 2018, que fue pro-R. El cronológico solo usa el pasado, como producción.
- **«k ≥ 2» es peor en Texas** (P = 0.07). Excluye 1998–2014 con una sola encuestadora, cuyo error es pequeño y estabiliza la media.
- **El sesgo por cargo gana en Texas (P = 0.82) pero pierde con claridad a nivel nacional (P = 0.004):** sobreajuste. Queda como escenario: con solo contiendas de gobernador el sesgo es +0.08 pp y P(Hinojosa) sube a 24 %.

**Encuestas partidistas.** Texas tiene muchas: Stratus (R), Quantus (R), Cygnal (R), GBAO (D) y otras. Excluirlas (P2) mejora en TX (P = 0.98) pero es la peor opción a nivel nacional (P = 0.000). Se mantienen con su efecto de casa; «sin encuestas partidistas» es escenario y hoy no cambia el margen: en la ventana actual pesan poco.

**Terceros.** El libertario se desinfla: en TX la regla T4 sobreestima a los terceros por +1.0 pp, y T2 (faltante = 0) es mejor en TX. A nivel nacional T4 es la mejor (MAE de terceros 1.368 contra 1.440). Se mantiene T4; hoy da 2.2 % a terceros con Dixon en 1–4 %.

**Ventana ampliada:** no aplica hoy (9 firmas en 21 días). La emulación confirma que ampliar es mejor que no ampliar (3.397 contra 3.670).

## 5. Contexto de la campaña
- **Encuestas:** Abbott por 2 a 5 puntos en las públicas recientes (Mark Jones, Rice). La tendencia pública se cerró de +8 (enero) a +1 (julio–agosto) y volvió a abrirse a +3–5 en octubre.
  - Marist 8–11 oct LV: Abbott 49 – 45.
  - UH Hobby 10–14 oct: Abbott 49 – 46, Dixon 2.
  - TxPOR 15–18 oct LV: Abbott 51 – 48.
  - Fox/Beacon-Shaw 15–19 oct LV: 52 – 47.
  - Emerson 17–19 oct: 49 – 45.
- **Dinero:** Abbott empezó 2026 con más de $105 millones y gastó 6 a 1 entre julio y septiembre; terminó el periodo con $18.2 M contra $4 M de Hinojosa (Newsweek).
- **Senado:** en la misma boleta, James Talarico (D) lleva una ventaja estrecha sobre Ken Paxton (R) (CBS Austin). Es la principal fuente de un posible arrastre demócrata, y la razón por la que los mercados dan más a Hinojosa que las encuestas corregidas.
- **Temas:**
  - Hinojosa: tarifas eléctricas, cierre de escuelas y centros de datos;
  - Abbott: impuesto a la propiedad, y la acusa de apoyar un impuesto estatal sobre la renta. Abbott no ha aceptado debatir.

## 6. Mercados
- Kalshi D 33.2 % y Polymarket D 31.5 % contra 10 % de las encuestas corregidas (23 % sin sesgo).
- Los mercados se parecen más al escenario sin sesgo, y su mercado de márgenes centra el resultado en −3.0. No parecen descontar el error pro-D histórico de Texas.
- Con el peso de 0.30 estimado en 40 contiendas de 2024 (ver Arizona), el final queda en 14.6 %.

## 7. Escenarios (P(Hinojosa); sin mercados salvo que se indique)
| Escenario | Margen | P |
|---|---|---|
| **Final (encuestas + mercados)** | −4.5 | **14.6 %** |
| Con sesgo, sin mercados | −5.6 | 10.0 % |
| Sin sesgo, sin mercados | −3.1 | 23.4 % |
| Sin sesgo, con mercados | −2.8 | 25.9 % |
| Sesgo solo con contiendas de gobernador (+0.08) | −3.0 | 24.1 % |
| Sesgo sin contiendas k = 1 (−2.88) | −6.0 | 8.5 % |
| Ventana de 45 días (20 firmas) | −4.7 | 11.8 % |
| Polymarket por rangos | −3.0 | 29.0 % |

## Fuentes
- [Fox 7 Austin: encuesta UH Hobby School, 10–14 oct](https://www.fox7austin.com/news/texas-governors-race-abbott-holds-narrow-lead-over-hinojosa-latest-poll)
- [Fox 7 Austin: encuesta YouGov, 28 sep–5 oct](https://www.fox7austin.com/election/hinojosa-abbott-split-texas-voters-latest-governors-poll)
- [Newsweek: encuestas de septiembre y octubre, subgrupos de UMass Lowell y finanzas de campaña](https://www.newsweek.com/greg-abbott-gets-good-sign-after-double-texas-polling-blow-12542755)
- [Reuters vía Lufkin Daily News: tendencia de las encuestas y voto latino](https://lufkindailynews.com/news_reuters/state/gov-greg-abbott-gina-hinojosa-in-virtual-tie-in-governor-race/article_370a2b51-2399-55d2-b04c-fb794c6b0b76.html)
- [CBS Austin: voto anticipado y carrera al Senado](https://cbsaustin.com/news/local/early-voting-could-decide-close-texas-governor-and-us-senate-races)
- [Wikipedia: 2026 Texas gubernatorial election](https://en.wikipedia.org/wiki/2026_Texas_gubernatorial_election) · [270toWin](https://www.270towin.com/2026-governor-polls/texas) · [Kalshi](https://kalshi.com) · [Polymarket](https://polymarket.com/event/texas-governor-winner-2026) · [civicAPI](https://civicapi.org)
