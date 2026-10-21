# Arizona 2026 · Gobernador (general) · Investigación, backtest y modelo final

Corte: 21-oct-2026 (13 días a la elección del 3-nov).
Carpetas:
- `modelo_general/`: notebook ejecutado, módulo, 10 pruebas y salidas.
- `backtest/`: backtest, comparación de mercados y datos.

## 1. Pronóstico
| Candidato | % de voto (IC80) | Probabilidad de ganar |
|---|---|---|
| **Katie Hobbs (D)** | **51.9 %** (48.5–55.3) | **93.5 %** |
| Andy Biggs (R) | 44.0 % (40.6–47.4) | 6.5 % |
| Terceros (Hourihan, No Labels; Lombardo, Green; otros) | 4.1 % (1.6–6.5) | — |

- **Margen Hobbs − Biggs:** +7.8 pp (σ 5.1; IC95 −2.3 a +18.0).
- **Solo encuestas:** P = 94.1 %. **Mercados:** 92.1 % (Kalshi 90.6 %, Polymarket 93.5 %).
- **P(recuento automático, margen ≤ 0.5 pp):** 2.1 %.

**Sensibilidad.** Todos los escenarios dan P(Hobbs) entre 0.90 y 0.96:

| Escenario | Margen | P(Hobbs) |
|---|---|---|
| Final | +7.8 | 0.935 |
| Con sesgo estatal V11 (+1.4 a favor de Biggs) | +6.4 | 0.903 |
| Regla literal de V11 (solo GrayHouse y HighGround) | +11.0 | 0.956 |
| Ventana de 60 días | +7.9 | 0.959 |
| Sin terceros, como en Georgia | +7.8 | 0.940 (Hobbs 53.9 %) |
| Solo Kalshi (margen implícito) | +6.5 | 0.906 |
| Polymarket por rangos de margen | +9.0 | 0.925 |

**Pronósticos públicos de referencia** (no entran al modelo):
- [VotePredictor](https://votepredictor.com/races/2026_GOV_AZ): D+5.4, 88 %.
- [Decision Desk HQ](https://votes.decisiondeskhq.com/forecast/2026/governor): Lean D, 73 %.
- [civicAPI](https://civicapi.org/forecasts): Likely D, 81 %.
- [On Point Politics](https://www.onpointpolitics.us/forecast/az/governor): D+12.4, 99 % (ver sección 8).

## 2. Modelo elegido y por qué (backtest)
Validación leave-one-year-out sobre FiveThirtyEight raw polls (Gob/Sen/Pres 1998–2022) más AZ 2024 (Presidente y Senado) y GA 2024. Son 782 contiendas con encuestas a 13 o más días, 22 de ellas en Arizona. La métrica principal es el CRPS: menor es mejor.

| Modelo | CRPS nacional | CRPS AZ | P(mejor que V11), nacional / AZ |
|---|---|---|---|
| **G** Georgia V11 | **3.495** | 2.630 | — |
| **H8** V11 sin sesgo estatal (**elegido para AZ**) | 3.561 | **2.471** | 0.16 / **0.85** |
| H4 V11 + Dirichlet y shocks de la primaria | 3.531 | 2.599 | 0.00 / 0.75 |
| H5 Pesos de la primaria + resto V11 | 3.502 | 2.643 | 0.41 / 0.46 |
| H6 V11 con vida media 10 d | 3.501 | 2.643 | 0.01 / 0.20 |
| H7 V11 con pesos ∝ n | 3.510 | 2.607 | 0.06 / 0.78 |
| H3 V11 + cuota R de indecisos estimada (≈0.55) | 3.522 | 2.686 | 0.30 / 0.23 |
| H1 V11 + escenarios de indecisos de la primaria | 3.579 | 2.904 | 0.09 / 0.05 |
| **A** Primaria AZ tal cual | 3.647 | 2.718 | 0.02 / 0.38 |
| H2 V11 + indecisos proporcionales | 3.759 | 3.139 | 0.00 / 0.02 |

**Por qué sin sesgo estatal.** A nivel nacional, el error relativo de cada estado persiste entre ciclos (correlación +0.22), y por eso V11 lo corrige. En Arizona no persiste (correlación −0.11): el error alterna de signo.
- Años presidenciales: +3.4 (2016), +3.2 (2020) y +5.4 (2024). Las encuestas sobrestimaron a los demócratas.
- Intermedias: −4.9 (2018) y −2.5 (2022). Las encuestas los subestimaron.

Arrastrar el sesgo de 2024 movería a Biggs +1.4 pp, en la dirección que falló en las dos últimas intermedias. La diferencia entre intermedias y presidenciales (−0.8 contra +2.8, con 11 contiendas cada una) **no se aplica**: queda como hipótesis.

**Terceros (aporte de la primaria):**
- Se modelan por nombre, sin un bucket «Otros» genérico.
- La calibración sale del histórico: real = 1.87 + 0.69 × lo que dicen las encuestas (DE 1.9).
- MAE del % D: Georgia (terceros = 0) 3.08 → 2.56 a nivel nacional; 2.53 → 1.94 en AZ.
- En contiendas con terceros por encima de 3 %: 4.18 → 2.97.

**Descartado de la primaria por el backtest:**
- Pesos √n × 1/MOE (≡ ∝ n) y vida media de 10 días.
- Dirichlet N_ef 750 con shocks por facción.
- Escenarios de indecisos por facción.
- Calibración por cuota de Maricopa (no tiene equivalente validable en la general).

**Lo que sí se adopta de la primaria:**
- Terceros nombrados.
- Auditoría de fuentes (columna `tambien_en`, duplicados entre fuentes explicados).
- Correcciones de nombres de encuestadoras (`ALIAS`).

## 3. Encuestas 2026
Fuentes combinadas sin duplicados: Wikipedia > tu Excel > 270toWin. Quedan 15 encuestas desde la primaria (22-jul).
- **Todas las de tu Excel quedaron emparejadas con su fuente.**
- Wikipedia trae **3 encuestas más recientes** que el Excel (que llega al 5-oct): Wick (R) del 3–6 oct (+6), GrayHouse (R) del 6–8 oct (+6) y HighGround del 6–8 oct (+17).

**Duplicados corregidos:**
- «AARP» en 270toWin = Fabrizio/Impact.
- «BSP Research» del 19-oct en 270toWin = ASU/BSP de ago–sep: mismas cifras y misma n, publicada 45 días después.
- **Falso duplicado evitado:** GQR (sep–oct) y GrayHouse (ago) coinciden en 49/45 con n = 600. Nunca se fusionan firmas distintas solo por coincidir en cifras.

**Ventana.** No hay encuestas en los últimos 21 días: la más reciente terminó el 8-oct. Se usan los 21 días previos a la encuesta más reciente (GQR, Wick, GrayHouse, HighGround; 4 encuestadoras), con la misma estructura que el backtest. Se suma una deriva de 0.25 pp/día por los 13 días que las encuestas son más viejas que el horizonte calibrado. Ese supuesto viene de California M5 y **no es validable**: FiveThirtyEight solo guarda los últimos 21 días. Sin la deriva, P = 0.943.

## 4. Kalshi vs Polymarket: ¿son lo mismo?
| | Gob AZ 2026 | Pres AZ 2024 | Sen AZ 2024 |
|---|---|---|---|
| Días con ambos | 337 | 28 | 28 |
| Último precio D, Kalshi / Polymarket | 0.906 / 0.935 | 0.289 / 0.250 | 0.757 / 0.782 |
| Diferencia absoluta media | 3.3 pp (máx. 19.2) | 2.2 pp | 2.7 pp |
| Correlación de niveles | 0.96 | 0.88 | 0.90 |
| Correlación de cambios diarios (logit) | **0.16** | 0.62 | 0.43 |
| Brier, últimos 30 días (Kalshi / Polymarket) | — | 0.100 / 0.086 | 0.044 / 0.035 |

**No son lo mismo.** Comparten la tendencia, pero no los movimientos diarios, y ninguno se adelanta al otro de forma consistente. Polymarket es menos líquido: unos USD 120 mil en el mercado ganador y unos 15 mil en el de rangos, contra unos 440 mil contratos en Kalshi. En 2024 Polymarket fue algo más preciso en AZ, pero con n = 2 no es evidencia.

**Decisión:** promedio de ambos, con peso 0.30 en la mezcla logit, igual que GA y CA (no validable). Polymarket además tiene un mercado por **rangos de margen** que da una distribución completa: media +9.0, DE 6.2. Es útil como contraste del margen.

**On Point Politics:** revisado en la sección 8.

## 5. Electorado de Arizona 2026 (diagnóstico; no entra al pronóstico)
- **Registro (20-oct):**
  - Republicanos 34.8 %, demócratas 28.3 %, **sin partido u otros 34.9 % (el grupo más grande)**, No Labels 1.1 %, libertarios 0.7 %, Green 0.1 %. Total: 4.37 millones.
  - Desde 2024: R −39 mil, D −27 mil, sin partido +56 mil, No Labels +17 mil ([FOX 10 / SOS](https://www.fox10phoenix.com/news/arizona-voter-registration-numbers-released-2026-election)).
- **Voto anticipado:**
  - Al 16-oct: 259,584 boletas, D 40.8 %, R 36.9 %, otros 22.3 %. En 2022, al mismo punto: D 41.2 %, R 36.4 %. Prácticamente **la misma composición que 2022** ([Derek Weech](https://derekweech.substack.com/p/az-abev-returns-10162026)).
  - Al 20-oct: unas 500 mil boletas, D ~40 % y R ~38 % ([KJZZ](https://www.kjzz.org/the-show/2026-10-20/new-poll-shows-democrats-winning-big-in-arizona-heres-how-to-read-the-numbers)).
  - Maricopa: unas 310 mil boletas, ~50 mil más que en 2022 ([FOX 10](https://www.fox10phoenix.com/election/maricopa-county-early-voting-surges-mail-in-ballots-exceed-2022-totals)).
  - En GA y CA la composición del voto anticipado no mejoró el error fuera de muestra, por eso queda como diagnóstico.
- **Voto dividido y cruce partidista:**
  - 2024: Trump +5.5 y Gallego +2.4 en la misma boleta (unos 8 pp de voto dividido).
  - 2026: Biggs retiene ~71 % de los republicanos en HighGround (Trump tuvo 88 % y Lake 84 %) ([KJZZ](https://www.kjzz.org/the-show/2026-10-20/new-poll-shows-democrats-winning-big-in-arizona-heres-how-to-read-the-numbers)).
  - Equis: ~10 % de los votantes de Trump 2024 apoya a Hobbs, 15 % entre latinos ([AZPM](https://news.azpm.org/p/azpmnews/2026/10/15/231597-statewide-poll-shows-trump-voters-shift-left-this-election/)).
- **Indecisos:**
  - En el backtest el reparto 50/50 es el mejor.
  - La cuota R estimada (~0.55, estable 1998–2024) empeora el error porque los efectos de casa ya la capturan.
  - El tamaño del bloque de indecisos no predice la dirección del error (correlación 0.01).
  - En 2026, las encuestas con muchos indecisos (NextGen 22 %, Stealth 18 %) dan márgenes chicos: es método de la encuestadora, no señal.
- **Terceros:** Green sacó 2.3 % al Senado en 2024. En 2026 hay dos en la boleta (No Labels y Green). Las encuestas dicen ~3 %, y la calibración da 4.1 %.
- **Conteo:** Maricopa reporta primero el voto anticipado temprano (más demócrata). Las boletas anticipadas entregadas el día de la elección tienden a ir a los republicanos y tardan días en contarse. Habrá un corrimiento hacia Biggs durante el conteo.

## 6. Fuentes
| Fuente | Uso | Estado |
|---|---|---|
| Wikipedia (API MediaWiki) | Encuestas 2026, 2024, 2022, 2018 | Capturada el 21-oct vía GitHub Actions (`scripts/capturar_arizona.py`, rama `diagnostico-arizona`) |
| 270toWin | Encuestas (fecha de publicación) | Capturada el 21-oct |
| Tu Excel `ARIZONA_GOBERNADOR-v1.xlsx` | Encuestas verificadas a mano | Hasta el 5-oct |
| Kalshi `GOVPARTYAZ-26`, `PRESPARTYAZ-24`, `SENATEAZ-24` | Probabilidad (mezcla) | Velas diarias |
| Polymarket (ganador y rangos de margen) | Probabilidad (mezcla) y distribución del margen | Historia diaria |
| FiveThirtyEight raw polls 2023 | Calibración (σ, ν, efectos de casa, terceros) | CC BY 4.0 |
| SOS, condados, Weech, Data Orbital | Registro y voto anticipado (diagnóstico) | Manual |
| **civicAPI** `/api/v2/early-vote/AZ/{returned,requested}` | Voto anticipado diario por partido y condado (diagnóstico) | **En vivo, gratis, sin clave** (pide atribución). Al 21-oct: 642,253 devueltas |
| On Point Politics `/api/polls/az-gov-2026` | Contraste de encuestas (JSON público) | No aporta encuestas nuevas |
| Civiq | **No cubre Arizona** (solo California) | — |

**Fuentes que conviene agregar en producción:**
1. **civicAPI** para el voto anticipado por partido y condado. **Ya integrado en el modelo de AZ.** Para CA y GA solo da totales sin partido; ahí se quedan Civiq y Civic Forge.
2. Polymarket en vivo, igual que Kalshi.
3. Encuestas de HighGround, Noble Predictive y Data Orbital, que publican primero en sus sitios.

## 7. Limitaciones
- 22 contiendas de Arizona: la elección de «sin sesgo estatal» tiene evidencia moderada (P = 0.85), no concluyente.
- La deriva por encuestas viejas y el peso de los mercados son supuestos.
- No hay encuestas del último tramo. Si sale una encuesta nueva, el pronóstico puede moverse más de lo habitual.

## 8. Revisión de On Point Politics (21-oct)
**Qué es.** El sitio de pronósticos de On Point Polling, una encuestadora de Miami: [metodología](https://www.onpointpolitics.us/forecast/methodology), [cambios](https://www.onpointpolitics.us/forecast/changelog). Para Arizona da Hobbs 55.0, Biggs 42.6, Hourihan 1.5 y Lombardo 0.9: **D+12.4 (80 %: +5.2 a +19.8), 99 %**. Para Georgia, Bottoms +0.5 (55 %); para California, Becerra con más de 99 %.

**Cómo llega a ese número.** Es un modelo **dominado por fundamentales**:
- Lean 2024 por condado.
- Voto genérico nacional D+12.
- Identificación partidista de Gallup (50 D / 39 R), convertida a D+15.4 entre votantes probables. Pesa al menos 40 % en Senado y gobernador.
- Aprobación presidencial de su propia base de encuestados (TPSI).
- Términos locales: gasolina (AAA) y centros de datos (Economist/YouGov).
- Finanzas de campaña (FEC).
- 1,152 tipos de votante por condado y simulaciones con choques nacionales, demográficos, estatales y de condado.

En Arizona, sus fundamentales dan D+11.9 y las encuestas, con su propio promedio, D+10.5. El voto anticipado suma +0.6.

**Cómo obtienen los datos:**
- Encuestas propias y públicas, con calificación por encuestadora.
- Resultados certificados.
- Gallup, AAA, FEC, censo y primarias 2026.
- **Voto anticipado de civicAPI**, que lo recopila de las autoridades electorales estatales.
- Publican un JSON por contienda (`/api/polls/{estado}-gov-2026`).

**Problemas encontrados:**
- Su lista de AZ mete el **promedio de RealClearPolitics como si fuera una encuesta**.
- Incluye 11 encuestas anteriores a la primaria y le faltan Wick y HighGround de octubre.
- Su promedio no coincide entre páginas: +5.7 en el JSON y +10.5 en la ficha.
- Su propio backtest de gobernadores reporta **15 pp de error medio** en el componente de fundamentales.
- El entorno D+12/D+15 es un supuesto fuerte, no validado: en el backtest de Georgia, el prior estructural empeoró el CRPS en gobernadores (3.655 → 3.705).

**Qué probamos de su metodología** (mismo backtest, 782 contiendas; P = probabilidad de mejorar a la base, remuestreando años):

| Idea | CRPS nacional (base 3.495) | AZ (base sin sesgo 2.471) | P nacional / AZ | Decisión |
|---|---|---|---|---|
| Penalizar encuestas con muchos indecisos (peso × e^(−U/15)) | 3.519 | 2.447 | 0.05 / 0.60 | No |
| Excluir encuestas con ≥ 20 % de indecisos | 3.520 | 2.532 | 0.04 / 0.23 | No |
| Recortar atípicas a ±2 DE | 3.495 | 2.464 | 0.45 / 0.89 | No (no cambia nada) |
| Peso por calidad histórica de la encuestadora | **3.487** | 2.508 | **0.68–0.78** / 0.06 | No en AZ; **candidata** para el estándar |
| Terceros con el voto histórico de terceros del estado | MAE % D 2.597 → 2.601 | 1.855 → 1.826 | — | No (neutro) |
| Fundamentales con entorno nacional | ya rechazado en Georgia | | | No |

Su reparto 50/50 de indecisos y la corrección de RV a LV (0.3 pp) coinciden con lo que ya hacemos.

**Qué sí adoptamos:**
1. **civicAPI** como fuente en vivo del voto anticipado por partido y condado. Solo AZ trae partido; CA y GA vienen sin desglose. Integrado en `arizona_modelo_final.voto_anticipado_civicapi()`, con snapshot de respaldo e historial diario en `datos/civicapi/historial_az.csv`.
2. PredictIt como tercer mercado, que civicAPI ya promedia. Pendiente de evaluar.
3. Los pronósticos de On Point y civicAPI como **referencias externas**, no como insumo.

**Diagnóstico de civicAPI (21-oct).** 642,253 boletas devueltas: D 39.2 %, R 38.2 %, otros 22.6 %, de 3.26 millones solicitadas. Los demócratas devuelven más rápido (24.0 % de sus solicitudes) que los republicanos (21.3 %) y los independientes (13.6 %). Las boletas pendientes se inclinan a R e independientes. Es lo esperable: según el registrador de Maricopa, los demócratas votan más por correo y los republicanos más en persona y el día de la elección. No entra al pronóstico.
