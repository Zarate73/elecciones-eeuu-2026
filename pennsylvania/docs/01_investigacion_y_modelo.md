# Pennsylvania 2026 · Gobernador (general) · Investigación, backtest y modelo

Corte: 23-oct-2026, 11 días antes de la elección del 3-nov.

- [`../produccion/`](../produccion/): paquete `pa_pronostico` con fuentes en vivo y 16 pruebas sin red. El notebook ejecutado y tu Excel están en la carpeta local `Pronosticos/Pennsylvania/MODELO_PENNSYLVANIA_GENERAL`.
- [`../backtest/`](../backtest/): backtest, datos y resultados.

## 1. Pronóstico
| Candidato | % de voto (IC80) | Probabilidad de ganar |
|---|---|---|
| **Josh Shapiro (D, gobernador)** | **58.3 %** (54.1–62.5) | **99.7 %** |
| Stacy Garrity (R, tesorera estatal) | 39.5 % (35.3–43.8) | 0.3 % |
| Terceros (Ken Krawchuk, L; otros) | 2.1 % (0.1–4.5) | — |

- **Margen Shapiro − Garrity:** +18.8 pp (σ 6.5; IC95 +5.9 a +31.7).
- **P(recuento automático):** 0.1 %. En PA el recuento es automático si el margen es ≤ 0.5 pp.
- **Cómo se llega:**
  - Promedio de encuestas: +22.3 (F&M LV 59–36, 7–18 oct, y ActiVote 62–39, 21-oct; k = 2).
  - Sesgo estatal de PA: −1.05 (las encuestas en PA sobreestimaron al demócrata en 1.43 pp; contracción 0.73).
  - Resultado solo con encuestas: +21.2, con P(Shapiro) 99.9 %.
  - Mercados (Kalshi 97.3 %, Polymarket 97.7 %) desplazan −2.4 pp. P(Shapiro) queda en 99.7 %.

**Cruce sesgo × mercados**
| Sesgo estatal | Mercados | Margen | P(Shapiro) |
|---|---|---|---|
| Sí | No | +21.2 | 99.9 % |
| No | No | +22.3 | 99.9 % |
| **Sí** | **Sí (final)** | **+18.8** | **99.7 %** |
| No | Sí | +19.6 | 99.8 % |

**Sensibilidad** (margen solo con encuestas; P con mercados)
| Escenario | Margen | P(Shapiro) |
|---|---|---|
| Sin F&M (pesa 51 %): la ventana se amplía a 5 firmas | +23.4 | 99.9 % |
| Sin ActiVote (pesa 49 %) | +22.7 | 99.9 % |
| Ventana de 45 o 60 días (7 encuestadoras) | +21.9 | 99.9 % |
| Ajuste por patrocinador (Z to A D, Susquehanna R, NPA R) | +21.9 | 99.7 % |
| Peso de mercados 0.15 / 0.50 | +20.1 / +17.2 | 99.8 % / 99.4 % |
| Polymarket por rangos de margen | +24.3 | ≈100 % |

**Lectura.** La pregunta de quién gana está resuelta por todas las fuentes: ningún escenario baja P(Shapiro) de 99 %. La incertidumbre real está en el **tamaño** del margen, que va de +17 a +24 según el escenario. Ahí el modelo y los mercados por rangos no coinciden (ver §5).

## 2. Fuentes
| Fuente | Qué aporta | Uso |
|---|---|---|
| Wikipedia (API) | Encuestas con n, población y terceros | Pronóstico |
| 270toWin | Encuestas, fechadas por publicación; **ActiVote 21-oct solo está aquí** | Pronóstico (se deduplica) |
| Tu Excel (`PENNSYLVANIA_GOBERNADOR-v1.xlsx`, hoja «Gobernador Pennsylvania») | 20 encuestas generales | Pronóstico (se deduplica) |
| **Kalshi** `GOVPARTYPA-26` | Shapiro 97.3 % | Mezcla con peso 0.30 (promediado con Polymarket) |
| **Polymarket** `pennsylvania-governor-winner-2026` | Shapiro 97.7 % | Mezcla con peso 0.30 |
| Polymarket `margin-of-victory` (rangos) | Margen implícito +24.3 (σ 8.0) | Escenario |
| **civicAPI (PA)** | Boletas por correo solicitadas y devueltas, por partido y condado | Diagnóstico |
| Departamento de Estado de PA (registro) | Registro por partido | Contexto (prensa; sin API estable) |

**Particularidades de Pennsylvania resueltas en el código**
- **Encuestadoras con varios nombres:** PennLive y Bravo Group son la misma serie (Bravo Group hace la encuesta de PennLive). NYT/Inquirer/Siena aparece de cuatro formas. Todas se normalizan a una clave para deduplicar y para los efectos de casa.
- **Versiones LV y RV de la misma encuesta:** se prefiere LV y la RV se descarta (columna `nota_version`). Antes el modelo podía contar dos veces la misma encuesta.
- **Polymarket por rangos:** el rango abierto «X % or more» tenía cota superior arbitraria. Ahora es max(30, X + 10). Con un margen de +20 la cota importa.
- **PA no tiene voto anticipado en persona**, solo por correo. `anticipado.py` trata la columna en persona como opcional.
- **Terceros:** la ventana no los reporta (F&M y ActiVote solo dan D/R). Con la regla T4 («no reportado ≠ 0»), entra la media histórica (2.1 %).

**Se recomienda agregar** (hoy no entran por falta de serie histórica para validarlas):
- Las encuestas de Muhlenberg y Emerson cuando se publiquen. La ventana tiene solo 2 firmas, y una (ActiVote) es un panel en línea de n = 400.
- La serie diaria de boletas devueltas del Departamento de Estado, para tener una serie del mismo día para 2028.

## 3. Electorado, contexto y comportamiento de los indecisos
**Registro**
- Total: D ≈ 3.84 M y R ≈ 3.64 M.
- Votantes activos (agosto de 2026, según el GOP de PA): la ventaja demócrata se redujo de 56,006 a 25,811. La tendencia republicana de registro sigue desde 2020.
- En 2024 Trump ganó PA por 1.7. En 2022 Shapiro ganó por 14.8 contra Mastriano.

**Primarias del 19-may:** Shapiro sin rival, 1,116,869 votos. Garrity sin rival, 641,172. La participación demócrata fue 1.7 veces la republicana.

**Contexto de la campaña**
- **Shapiro, gobernador popular:** aprobación del 63 % (Quinnipiac, 1–5 oct). Se le menciona como presidenciable en 2028.
- **Garrity es poco conocida:** 33 % no la conoce (NYT/Siena, sep), incluido el 26 % de los republicanos.
- **Dinero:** de junio a septiembre Shapiro gastó 23 veces lo de Garrity, y 43 veces en anuncios.
- **Clima nacional:** aprobación de Trump en PA 37 % (60 % desaprueba).
- **Temas:** economía y costo de vida; centros de datos y energía (tema local destacado). Hubo un solo debate, a principios de octubre.

**Encuestas recientes**
| Encuestadora | Fechas | Población | Shapiro | Garrity | Margen |
|---|---|---|---|---|---|
| ActiVote | 21-oct | LV, n 400 | 62 | 39 | +23 |
| Franklin & Marshall | 7–18 oct | LV, n 600 | 59 | 36 | +23 |
| PennLive / Bravo Group | 5–11 oct | RV | 58 | 28 | +30 |
| Quinnipiac | 1–5 oct | LV, n 1,159 | 59 | 34 | +25 |
| Z to A Research (D) | 28 sep–1 oct | LV | 53 | 34 | +19 |
| Susquehanna (R) | 22–30 sep | LV | 52 | 31 | +21 |
| NYT / Inquirer / Siena | 15–22 sep | LV | 58 | 38 | +20 |

**Indecisos**
- Las encuestas LV de octubre dejan 4–5 % de indecisos. Las RV y las de septiembre dejan 8–17 %.
- Quinnipiac: los independientes van 62–23 por Shapiro. No hay una base de indecisos favorable a Garrity a la que recurrir.
- **Backtest de reglas de indecisos (PA, 24 contiendas):**
  - el reparto proporcional (H2) es el peor (CRPS 3.912 contra 3.320);
  - la cuota R estimada (H3) también empeora (3.500).
- **Regla adoptada: indecisos 50/50.** Es la regla nacional y la mejor también en PA.

**Contiendas con ventaja grande (≥ 15 pp, n = 357 a nivel nacional)**
- El líder ganó en promedio por 0.28 pp más de lo pronosticado. No hay compresión sistemática.
- La variante E (escala del margen) estima b = 0.991 fuera de muestra y no mejora (P = 0.24 en ventajas grandes). **No se aplica ajuste por paliza.**

**Voto por correo** (civicAPI, 23-oct)
- 1,251,610 boletas solicitadas y 720,664 devueltas (D 67.0 %, R 24.1 %, sin partido 8.7 %; D+43).
- **Solo diagnóstico:** desde 2020 los demócratas votan por correo y los republicanos en persona el día de la elección. Es registro de partido, no intención de voto.

## 4. Backtest (LOYO, horizonte de 11 días, ventana de producción de 12 a 21 días)
- **Datos:** FiveThirtyEight 1998–2022 más 2024. En total 902 contiendas, 24 de PA (7 de gobernador).
- **Métrica:** CRPS, más bootstrap por años.

| Variante | CRPS nacional | CRPS PA (24) | CRPS PA 2016+ (9) | P(mejor que G) en PA |
|---|---|---|---|---|
| **G · V11 + sesgo estatal contraído** | **3.391** | 3.320 | 2.858 | — |
| H8 · sin sesgo estatal (Arizona) | 3.538 | **3.312** | **2.695** | 0.52 (nacional 0.06) |
| F1 · sesgo sin contraer | 3.488 | 3.966 | 3.063 | 0.02 |
| H2 · indecisos proporcionales | 3.679 | 3.912 | 2.915 | 0.02 |
| H3 · cuota R de indecisos | 3.419 | 3.500 | 2.849 | 0.05 |
| P1 · casa + patrocinador si no hay historia | 3.394 | 3.334 | 2.905 | 0.18 |
| P2 · sin encuestas partidistas | 3.441 | 3.356 | 3.024 | 0.24 |
| P3 · partidistas pesan la mitad | 3.401 | 3.332 | 2.928 | 0.30 |
| E · G + escala del margen | — | 3.505 | — | 0.14 |

**Error de las encuestas en PA** (+ = sobreestimaron al demócrata)
- Pro-D en 13 de 24 contiendas. El error cambia de signo entre ciclos: la autocorrelación del error relativo al nacional es −0.12.
- **Antes de 2016**, a menudo subestimaron al demócrata: 2000 Sen (−9.4), 2004 Sen (−7.0) y 2006 Sen (−6.4).
- **Desde 2016** lo sobreestimaron en todas las contiendas presidenciales y de Senado: 2016 (+6.8 y +5.3), 2020 (+4.3) y 2024 (+2.1 y +3.8). La excepción es 2022, donde subestimaron a Shapiro y Fetterman (−1.9 y −3.7).
- **1998 Gob:** una sola encuestadora, error −22.5. Es un caso atípico.

**Validación estrictamente cronológica** (todo con años anteriores, 2004–2024)
| Ámbito | n | Con sesgo | Sin sesgo | P(sin sesgo mejor) |
|---|---|---|---|---|
| Nacional | 723 | **3.205** | 3.460 | 0.002 |
| PA | 19 | 2.335 | **2.308** | 0.52 |
| PA 2016+ | 9 | 2.968 | **2.838** | 0.60 |
| PA gobernador | 5 | 2.114 | **1.899** | 0.86 |

**Decisión: G** (la regla nacional, igual que en Florida y Nevada).
- En PA, quitar el sesgo no es ni mejor ni peor (P = 0.52 en LOYO y en el cronológico). A nivel nacional, el sesgo gana con claridad (P = 0.002 cronológico).
- **Por qué no se adopta H8 aunque gane en PA gobernador:** son 5–7 contiendas, y la diferencia viene de 2022, cuando las encuestas subestimaron a Shapiro. Sin evidencia estatal significativa se usa la regla nacional. «Sin sesgo» se reporta siempre (+19.6 con mercados).
- **Escenario sin contiendas de una encuestadora:** −0.91 pp en lugar de −1.05 (efecto de 1998). La decisión es transversal a GA, FL y NV.
- **Encuestas internas de campaña:** P1, P2 y P3 son peores en PA. Se mantiene el efecto de casa de la firma.
- **Terceros:** T4 (MAE conjunto 2.349) contra T2 (2.360) y T0 (2.366). Se mantiene T4.

## 5. Mercados
- **Hoy:** Kalshi 97.3 % y Polymarket 97.7 %.
- **Serie desde junio:**
  - Correlación de niveles 0.45 y de cambios diarios 0.02; diferencia media 1.55 pp.
  - Cerca de 1 los precios casi no se mueven, así que las variaciones diarias son ruido de liquidez.
  - Se promedian en una sola señal: el peso 0.30 es del promedio, no de cada plataforma.
- **Peso en régimen extremo:** en las 18 contiendas de 2024 con mercado < 0.1 o > 0.9, el peso óptimo por máxima verosimilitud es 0.30 (IC95 0–0.80). Se mantiene 0.30.
- **Advertencia sobre el margen.** Una probabilidad de 97 % «implica» un margen de +13, muy por debajo de las encuestas (+21) y de Polymarket por rangos (+24).
  - Por eso la mezcla **baja** el margen en 2.4 pp aunque los mercados también den ganador a Shapiro.
  - La causa probable es el sesgo favorito–longshot: los contratos a 97 ¢ rinden poco y los apostadores compran a Garrity barato. No es información sobre el margen.
  - Efecto en la probabilidad: casi nulo (99.9 → 99.7 %). En el margen y en los % sí pesa: Shapiro pasa de 59.5 a 58.3 %.
  - No se cambia la regla (está validada nacionalmente y en régimen extremo), pero **para el margen, el escenario «sin mercados» (+21.2) o Polymarket por rangos (+24.3) son lecturas igualmente defendibles.**

## 6. Limitaciones
- **Solo dos encuestadoras en la ventana**, cada una pesa ~50 %. ActiVote es un panel en línea con n = 400, y su suma D + R da 101 (redondeo). Sin ella, la ventana se amplía y el margen sube a +22.7: la dependencia no cambia el ganador.
- **La σ (6.5) es nacional.** En contiendas con ventaja grande los errores históricos son mayores (CRPS 4.04 contra 3.39) y la cobertura del 80 % es 0.78, bien calibrada.
- **El sesgo estatal de PA cambió de signo en 2022**, justo en la contienda de Shapiro. El valor de hoy (−1.05) viene sobre todo de 2016–2024 (presidenciales y Senado).
- **El registro y el correo no informan el margen:** con el voto por correo muy demócrata por hábito, el D+43 no se puede comparar sin una serie del mismo día.
- **Terceros:** ninguna encuesta de la ventana los reporta. La media histórica (2.1 %) define los % publicados, pero no el margen.

Fuentes:
- [City & State PA, Quinnipiac 1–5 oct](https://www.cityandstatepa.com/politics/2026/10/quinnipiac-poll-shapiro-garrity-race-looks-rout/416473/)
- [Political Wire, Quinnipiac](https://politicalwire.com/2026/10/07/shapiro-opens-wide-leads-in-pennsylvania/)
- [FOX29, Shapiro +25](https://fox29.com/news/shapiro-holds-25-point-lead-over-garrity-governors-race-election-day-looms-poll)
- [PhillyVoice, la contienda en cifras](https://www.phillyvoice.com/by-the-numbers-pa-governor-race-2026/)
- [Spotlight PA, Garrity como outsider](https://www.spotlightpa.org/news/2026/08/stacy-garrity-pennsylvania-governor-race-underdog-josh-shapiro-elections/)
- [Spotlight PA, guía de la elección](https://www.spotlightpa.org/news/2026/09/josh-shapiro-stacy-garrity-pennsylvania-governor-election-guide-elections/)
- [Axios, el único debate](https://www.axios.com/local/pittsburgh/2026/10/08/politicsshapiro-garrity-governor-debate)
- [MyChesCo, brecha de votantes activos](https://www.mychesco.com/a/news/pennsylvania/pennsylvania-gop-narrows-active-voter-gap/)
- [LehighValleyNews, registro por partido](https://www.lehighvalleynews.com/elections/republicans-narrow-democrats-edge-in-voter-registration-across-pa-lehigh-valley)
- [Franklin & Marshall College Poll](https://www.fandm.edu/stories/franklin-marshall-college-poll-august-2026.html)
- civicAPI (boletas por correo de PA), Kalshi `GOVPARTYPA-26` y Polymarket `pennsylvania-governor-winner-2026`
