# Maine 2026 · Gobernador (general) · Investigación, backtest y modelo

Corte: 24-oct-2026, 10 días antes de la elección del 3-nov. Captura en vivo de las fuentes: 24-oct, 04:06 UTC.

- [`../produccion/`](../produccion/): paquete `me_pronostico` con fuentes en vivo y pruebas sin red. El notebook ejecutado y tu Excel están en la carpeta local `Pronosticos/Maine/MODELO_MAINE_GENERAL`.
- [`../backtest/`](../backtest/): backtest, datos y resultados (incluye `revision_sesgo_maine.py`).

## 1. Pronóstico
| Candidato | % de voto (IC80) | Probabilidad de ganar |
|---|---|---|
| **Hannah Pingree (D)** | **50.6 %** (47.4–53.8) | **95.3 %** |
| Bobby Charles (R) | 42.6 % (39.4–45.8) | 4.7 % |
| Rick Bennett (I) y otros | 6.8 % (4.6–9.0) | — |

- **Margen Pingree − Charles:** +8.0 pp (σ 4.8; IC95 −1.4 a +17.5).
- **P(|margen| ≤ 0.5 pp):** 1.9 %. Maine no tiene recuento automático; lo pide un candidato.
- **Mayoría simple.** La general de gobernador no usa voto preferencial: la Corte Suprema de Maine lo prohibió en 2017 y lo ratificó en abril de 2026 (LD 1666). Gana quien saque más votos, aunque no llegue al 50 %.
- **Cómo se llega:**
  - Promedio de encuestas: +10.3 (seis encuestadoras desde el 29-sep).
  - Sesgo estatal de Maine: −2.4 (las encuestas sobreestimaron al demócrata; ver §4).
  - Resultado solo con encuestas: +7.9, con P(Pingree) 95.0 %.
  - Mercados: Kalshi 95.7 % y Polymarket 96.4 %, prácticamente lo mismo. Desplazan +0.2 pp.

**Cruce sesgo × mercados**
| Sesgo estatal | Mercados | Margen | P(Pingree) |
|---|---|---|---|
| Sí | No | +7.9 | 95.0 % |
| No | No | +10.3 | 98.3 % |
| **Sí** | **Sí (final)** | **+8.0** | **95.3 %** |
| No | Sí | +9.7 | 97.8 % |

**Sensibilidad** (P con mercados)
| Escenario | Margen | P(Pingree) |
|---|---|---|
| Sesgo con todas las contiendas, incluido el Senado 2020 de una sola encuestadora (−4.0) | +6.3 | 92.8 % |
| Sesgo sin contraer (−3.9) | +6.4 | 93.0 % |
| Sin Beacon/Shaw (pesa 35 %) | +8.4 | 96.4 % |
| Ventana de 60 días (12 encuestadoras) | +7.9 | 96.7 % |
| Regla literal V11 (última encuesta de cada firma, k = 2) | +6.9 | 90.1 % |
| Bennett se desinfla (apoyo × 0.3) | +7.9 | 95.4 % (Pingree 52.6 %) |
| Polymarket por rangos (normal ajustada) | +12.3 | 90.9 % |

**Lectura.** Pingree es clara favorita. Todas las variantes razonables quedan entre 90 y 97 %. El riesgo para Pingree está en el sesgo de Maine: si se toma completo, el margen baja a +6. El independiente casi no mueve el margen; solo cambia cuánto suman los dos candidatos.

## 2. Fuentes
| Fuente | Qué aporta | Uso |
|---|---|---|
| Wikipedia (API) | 20 filas: n, población y Bennett. Siena publica la boleta completa y un careo sin Bennett | Pronóstico |
| 270toWin | 15 encuestas, fechadas por publicación | Pronóstico (se deduplica) |
| Tu Excel (`MAINE_GOBERNADOR-v1.xlsx`) | Hoja «Histórico encuestas», bloque 1: 14 encuestas con fechas, población, Bennett e indecisos por separado | Pronóstico (se deduplica) |
| **Kalshi** `GOVPARTYME-26` | D 95.4 %, R 4.3 %, Bennett (`-RBEN`) ~1 % | Mezcla con D / (D + R), peso 0.30 |
| **Polymarket** `maine-governor-winner-2026` | D 95.5 %, R 3.6 % (volumen ~$46 mil) | Mezcla con peso 0.30 |
| Polymarket `maine-governor-margin-of-victory-2026` | 8 rangos D/R + «gana un independiente» (2.9 %); precios que suman 1.22 | Escenario (diagnóstico) |
| **civicAPI (ME)** | Voto ausente por correo y en persona, por partido y **municipio** | Diagnóstico |

**Particularidades de Maine resueltas en el código**
- **Las encuestadoras aparecen con el medio o con la firma:**
  - Fox News = Beacon (D)/Shaw (R);
  - AARP = Fabrizio Ward (R)/Impact (D);
  - CNN = SSRS;
  - NYT/Portland Press Herald = Siena;
  - Washington Post = Schar School;
  - Marist University = Marist College.

  Se unifican con la clave del histórico de FiveThirtyEight, para que conserven su efecto de casa.
- **Las encuestas bipartidistas** (un socio D y otro R) ya no se marcan como partidistas.
- **Siena:** de sus dos versiones se usa la boleta completa (47–34–8), no el careo sin Bennett.
- **CBS/YouGov es un careo forzado** (56–44, sin Bennett). Entra con su margen y con terceros «no reportado», no 0.
- **Mercado de márgenes:** el contrato «gana un independiente» no tiene margen D−R, pero cuenta en el denominador de P(D).
- **civicAPI reporta municipios, no condados** (571 regiones; la principal es Portland).
- **Error corregido en el histórico 2024:** Axis Research (17–20 oct 2024, Trump 50–41) es una encuesta del **distrito 2 de Maine** y estaba como estatal.
  - En el backtest era la única encuesta de la ventana de Maine 2024 (error −15.9) y volteaba el signo del sesgo estatal.
  - La misma fila está en las copias de Florida, Nevada y Pennsylvania. Ahí solo afecta marginalmente la calibración nacional; no se corrigió.

**Se recomienda agregar:**
- La encuesta de Pan Atlantic Research, si publica la general: ha hecho las primarias.
- La serie diaria de voto ausente del Secretario de Estado, para comparar con 2022 al mismo día.

## 3. Electorado, contexto e indecisos
**Registro** (L2 vía Independent Voter Project, 23-oct)
| Grupo | Votantes | % |
|---|---|---|
| Demócratas | 326,582 | 33.7 % |
| No inscritos (unenrolled) | 313,081 | 32.3 % |
| Republicanos | 288,533 | 29.8 % |
| Otros partidos | 41,824 | 4.3 % |

**Primarias del 9-jun** (voto preferencial, primera primaria abierta a no inscritos):
- Pingree ganó en la 4ª ronda (56.2 % contra Nirav Shah; en la 1ª ronda iba 2ª, con 23 %).
- Charles ganó en la 7ª (60.3 % contra Ben Midgley; 38 % en la 1ª).

**Contexto**
- **Elección abierta:** Mills no puede reelegirse. Los demócratas tienen la gubernatura desde 2019; LePage (R) gobernó 2011–2019, primero con 37.6 % en una elección a tres.
- **Candidatos:**
  - Pingree, ex presidenta de la Cámara estatal e hija de la congresista Chellie Pingree.
  - Charles, exfuncionario de antinarcóticos del Departamento de Estado con George W. Bush, hoy cabildero.
  - Bennett, expresidente del Partido Republicano de Maine, salió del partido en 2025 («My jersey says Maine»).
- **Dinero:** Pingree ha recaudado $4.2 M, Charles $1.8 M y Bennett $0.92 M.
  - Un grupo ligado a la Asociación de Gobernadores Demócratas reservó más de $8 M en anuncios.
  - El apoyo de los gobernadores republicanos que esperaba Charles no llegó.
  - Un PAC de donantes republicanos gastó $70 mil promoviendo a Bennett, lo que divide el voto anti-Pingree.
- **Clima:** aprobación de Trump en Maine 40 % (Marist).
  - En la boleta también está el Senado (Troy Jackson D contra Collins, 51–47 en Marist), con voto preferencial.
- **Temas:** impuesto predial, vivienda, energía y costo de vida.
- **Calificaciones:** «Very Likely D» en promedio (Cook, Sabato y Pluribus).
- **Debates:** hubo cuatro; la prensa local los juzgó repetitivos y sin efecto.

**Encuestas en la ventana** (21 días previos a la más reciente)
| Encuestadora | Fin | Población | Pingree | Charles | Bennett | Margen | Peso |
|---|---|---|---|---|---|---|---|
| Beacon (D)/Shaw (R) — Fox News | 20-oct | LV 1,514 | 49 | 39 | 9 | +10 | 35 % |
| Suffolk | 11-oct | LV 500 | 49 | 38 | 8 | +11 | 13 % |
| Washington Post/Schar | 5-oct | LV 800 | 49 | 36 | 11 | +13 | 12 % |
| Marist | 4-oct | RV 1,505 | 52 | 40 | 6 | +12 | 16 % |
| CBS/YouGov (careo forzado) | 1-oct | LV 1,133 | 56 | 44 | — | +12 | 12 % |
| co/efficient (R) | 30-sep | LV 1,240 | 47 | 38 | 6 | +9 | 12 % |

- La carrera es muy estable: desde junio todas las encuestas dan entre +8 y +14.
- La encuesta más reciente (Beacon/Shaw, 16–20 oct) da +10.

**Indecisos y el independiente**
- **Bennett tiene entre 5 y 11 %** y es poco conocido: 36 % no lo conoce (AARP).
- **Hacia dónde va su voto:** Siena publicó cada encuesta con Bennett y sin él.
  - Septiembre: de 47–34–8 a 53–39, con 11 → 7 % de indecisos.
  - Junio: de 50–36–8 a 55–40.
  - Al quitar a Bennett, Pingree gana 5–6 puntos y Charles 4–5: su voto e indecisos se reparten casi parejo, apenas a favor de Pingree.
  - Entre los votantes mayores «indecisos» de AARP: Pingree 41 %, Bennett 32 % y Charles 13 %. Bennett no le quita votos solo a Charles.
- **Backtest nacional** (139 contiendas con terceros ≥ 5 % en las encuestas):
  - El tercero saca en promedio 1.1 pp menos de lo que daban las encuestas (mediana −1.2).
  - La regla T4 ya lo corrige: sesgo −0.07, MAE 1.8.
  - Ese voto no va claramente a ningún lado: pendiente del error del margen contra el desinfle +0.28 (ee 0.22; IC90 −0.17 a +0.72).
  - Calibrar aparte a los terceros fuertes (T5) no mejora (MAE 1.83 contra 1.81).
- **Maine 2014 (Cutler, el caso parecido):** las encuestas le daban 12.8 % y sacó 8.4 %. T4 pronosticaba 10.4, y el margen salió −2.8 respecto del pronóstico.
- **Indecisos:** el reparto proporcional es el peor en Maine (4.155) y a nivel nacional; la cuota R estimada también empeora.
- **Reglas adoptadas:** indecisos 50/50 y terceros T4.

**Voto ausente** (civicAPI, 23-oct)
- 179,532 emitidos: 87,036 por correo y 92,496 en persona, de 238,571 solicitados.
- Por partido registrado: D 50.3 %, R 21.2 %, no inscritos 26.1 % → D+29.
- **Solo diagnóstico:** el voto ausente es más demócrata que el electorado, y un tercio del padrón no está inscrito.

## 4. Backtest (LOYO, horizonte de 10 días, ventana de producción de 10 a 21 días)
- **Datos:** FiveThirtyEight 1998–2022 más 2024, con Axis Research quitada. En total 923 contiendas, 13 de Maine.
- **Fuera del backtest:** las contiendas en que el segundo lugar fue un independiente (King en 1998, 2012 y 2018; Cutler en 2010) no son D contra R y quedan fuera.

| Variante | CRPS nacional | CRPS ME (13) | CRPS ME 2016+ (3) | P(mejor que G) en ME |
|---|---|---|---|---|
| **G · V11 + sesgo estatal contraído** | **3.388** | 3.322 | 3.261 | — |
| H8 · sin sesgo estatal | 3.506 | 3.518 | 4.405 | 0.20 |
| F1 · sesgo sin contraer | 3.473 | **3.175** | **2.620** | 0.87 (nacional 0.12; gobernadores 0.002) |
| H2 · indecisos proporcionales | 3.633 | 4.155 | 4.328 | 0.03 |
| H3 · cuota R de indecisos | 3.421 | 3.444 | 3.216 | 0.34 |
| P1 · casa + patrocinador si no hay historia | 3.391 | 3.320 | 3.253 | 0.69 |
| P2 · sin encuestas partidistas | 3.439 | 3.316 | 3.336 | 0.57 |
| P3 · partidistas pesan la mitad | 3.398 | 3.315 | 3.289 | 0.63 |

**Error de las encuestas en Maine** (+ = sobreestimaron al demócrata)
- Pro-D en 8 de 13 contiendas.
- Los mayores son de Collins: Senado 2008 +7.2, 2014 +7.7 y 2020 +11.8 (una sola encuestadora).
- En gobernador: 2002 +11.5 y 2014 +3.3.
- Subestimaron al demócrata en 2000 Senado (−5.8) y 2002 Senado (−5.1).
- Autocorrelación del error relativo al nacional: +0.04.

**Validación estrictamente cronológica** (2004–2024)
| Ámbito | n | Con sesgo | Sin sesgo | P(sin sesgo mejor) |
|---|---|---|---|---|
| Nacional | 739 | **3.211** | 3.434 | 0.004 |
| ME | 9 | **2.834** | 3.265 | 0.014 |
| ME 2016+ | 3 | **3.247** | 4.346 | 0.000 |

**¿De dónde estimar el sesgo?** (`revision_sesgo_maine.py`)
- El sesgo de Maine con todas las contiendas es −6.0 bruto (−4.0 contraído). El 27 % del peso es del Senado 2020: Collins, con una sola encuestadora en la ventana.
- Se probaron reglas nacionales:

| Regla | Nacional | Gobernadores | ME |
|---|---|---|---|
| G · todas las contiendas del estado | 3.388 | 3.573 | 3.322 |
| Solo contiendas del mismo cargo | 3.436 (P = 0.25) | 3.507 (P = 0.65) | 3.454 (P = 0.24) |
| **Sin contiendas de una sola encuestadora (k ≥ 2)** | **3.367** (P = 0.74) | 3.545 (P = 0.66) | **3.260** (P = 0.99) |

**Decisión: G con el sesgo estimado sin contiendas de una sola encuestadora** (`sesgo_regla = "k2"`).
- El sesgo estatal mejora claramente en Maine (cronológico P = 0.014).
- **La hipótesis del «efecto Collins» no se sostiene:** estimar el sesgo solo con el mismo cargo empeora a nivel nacional.
- **Excluir las contiendas de una sola encuestadora mejora en todos los ámbitos:** en Maine con P = 0.99 y a nivel nacional en la misma dirección (P = 0.74).
- **El valor de hoy:** bruto −3.93, contracción 0.62 → **−2.43 pp**. La estimación con todas las contiendas (−4.0) se reporta como escenario.
- **Pendiente transversal:** en Nevada (revisión del 22-oct, H = 12) la misma regla daba 3.365 contra 3.375 (P = 0.56); ahora, con H = 10 y el dato de 2024 corregido, da P = 0.74. Conviene evaluar adoptarla en GA, FL, NV y PA.
- **No se usa el sesgo sin contraer (F1),** aunque gana en Maine: a nivel nacional y en gobernadores es peor (P = 0.12 y 0.002).

## 5. Mercados
- **Hoy:** Kalshi 95.7 % (D/(D+R); Bennett ~1 %) y Polymarket 96.4 %.
- **Serie desde sep-2025:** correlación de niveles 0.56 y de cambios diarios 0.04; Kalshi cotiza 3.9 pp por debajo en promedio.
  - No son dos señales independientes: se promedian en una sola, y el peso 0.30 es de ese promedio.
- **Coinciden con el modelo de solo encuestas** (95.0 %): la mezcla mueve el margen +0.2 pp.
- **Mercado por rangos:** P(D) 90.9 %, P(independiente) 2.9 %, margen ajustado +12.3 (σ 8.4) y E[margen | gana D] +13.6.
  - Es poco líquido (~$7.6 mil, diferenciales de hasta 18 ¢) y sus precios suman 1.22. Por eso es solo diagnóstico.

## 6. Limitaciones
- **En los últimos 21 días hay una sola encuesta** (Beacon/Shaw). La ventana se amplía a los 21 días previos; las encuestas tienen 4 días más de antigüedad que el horizonte, y la σ incluye esa deriva.
- **El sesgo estatal decide buena parte del margen** (+10.3 → +7.9). Con 13 contiendas de Maine es una estimación ruidosa, aunque la validación cronológica la respalda.
- **Bennett no puede ganar en el modelo:** los terceros se simulan como un total (IC80 4.6–9.0 %). Los mercados le dan 1–3 %, lo que es coherente con sus encuestas.
- **El careo forzado de CBS** (56–44) infla un poco su margen respecto de la boleta completa; pesa 12 %.
- **Voto ausente:** sin una serie del mismo día no se puede calibrar.

Fuentes:
- [Marist Poll, Maine, octubre 2026](https://maristpoll.marist.edu/polls/midterm-elections-in-maine-october-2026/)
- [270toWin, encuestas de gobernador de Maine](https://www.270towin.com/2026-governor-polls/maine)
- [PoliAgg, Maine gobernador 2026](https://poliagg.com/race/us-governor-2026-me/)
- [MultiState, Maine 2026](https://www.multistate.us/elections/governor-race/maine-2026)
- [Portland Press Herald, después del último debate](https://www.pressherald.com/2026/10/14/after-final-debate-heres-where-things-stand-in-the-race-to-become-maines-next-governor/)
- [Bangor Daily News, encuesta AARP](https://www.bangordailynews.com/2026/10/01/news/maine-election-governor-2026-hannah-pingree-bobby-charles-aarp-poll/)
- [Gigafact, voto preferencial y gobernador](https://gigafact.org/fact-briefs/is-ranked-choice-voting-used-in-maines-general-election-for-governor-fact-brief/)
- [Independent Voter Project, registro de Maine](https://independentvoterproject.org/voter-stats/me)
- [Wikipedia, elección de gobernador de Maine 2026](https://en.wikipedia.org/wiki/2026_Maine_gubernatorial_election)
- civicAPI (voto ausente de Maine), Kalshi `GOVPARTYME-26` y Polymarket `maine-governor-winner-2026` / `maine-governor-margin-of-victory-2026`
