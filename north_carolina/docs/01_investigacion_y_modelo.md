# North Carolina 2026 · Senado · Investigación y modelo general

Corte: 27-oct-2026 (captura en vivo del 27-oct 20:35 UTC), 7 días antes de la elección del 3-nov. Paquete `nc_pronostico` v1.0.0, base Ohio v1.2.0.

## 1. Pronóstico al 27-oct

| Senado | % de voto (IC80) | Probabilidad de ganar |
|---|---|---|
| Roy **Cooper** (D) | **53.0 %** (49.3–56.7) | **94.8 %** |
| Michael **Whatley** (R) | **43.8 %** (40.0–47.5) | **5.2 %** |
| Terceros (Bray, L; Dublin, Verde; votos por escrito) | 3.2 % (1.0–5.3) | — |

- **Margen D−R:** +9.2 pp (σ 5.7; IC95 −2.0 a +20.5).
- **Cómo se llega:** promedio de encuestas +10.68 · sesgo estatal −2.10 · mercados +0.66 → +9.23.
- **Probabilidades:** solo encuestas 93.5 %; Kalshi 96.5 %; Polymarket 97.5 %; final 94.8 %.
- **Recuento:** P(|margen| ≤ 0.26 pp) = 0.9 %.

**Lectura.** Cooper es favorito claro. Lo que limita la probabilidad a ~95 % no es el nivel (todas las encuestas desde julio de 2025 lo ponen adelante, de +4 a +15) sino tres cosas:
1. **Ventana corta.** Solo tres encuestadoras terminan en los últimos 21 días, y dos son de patrocinio republicano: Quantus (R) +8, Harper (R) +10 y ActiVote +13.8. Con k = 3, el término s²/k infla σ a 5.7.
2. **Sesgo estatal.** En NC las encuestas sobreestimaron al demócrata en las 10 contiendas desde 2014; el modelo resta 2.1 pp.
3. **Colas t.** La t de Student calibrada (ν ≈ 21) deja ~5 % de probabilidad de un error de encuestas de más de 9 pp.

Con la ventana de 45 días (11 encuestadoras) P sube a 98 %. El escenario más pesimista razonable (sin ActiVote) da 88 % sin mercados y 92 % con ellos.

## 2. ¿Sirve el modelo de gobernador para el Senado?

Es el primer estado de Senado del proyecto, así que el backtest lo probó explícitamente en lugar de suponerlo.

**Marco:** leave-one-year-out (LOYO), ventana de producción (7 ≤ días ≤ 21), 992 contiendas de 1998–2024: 383 de Senado, 23 de NC (9 de Senado). CRPS del margen (menor es mejor).

| Variante (cambia una pieza de G) | Senado nacional (383) | Senado con ventaja ≥ 8 pp (256) | NC Senado (9) | P(mejor que G), Senado nacional |
|---|---|---|---|---|
| **G** V11 + sesgo estatal contraído (producción) | **3.347** | **3.621** | 2.126 | — |
| S4 G + fundamentales (lean presidencial + entorno) | 3.349 | 3.646 | 2.103 | 0.52 |
| S1 σ calibrada solo con Senado | 3.350 | 3.625 | 2.153 | 0.24 |
| S3 G + sesgo nacional del cargo | 3.420 | 3.652 | 2.289 | 0.15 |
| S2 sesgo estatal solo con Senado | 3.422 | 3.753 | 2.043 | 0.12 |
| S5 G + escala del margen por cargo | 3.459 | 3.752 | 2.135 | 0.06 |
| H8 sin sesgo estatal | 3.496 | 3.848 | 2.070 | 0.07 |

- **Ninguna variante del Senado mejora a G.** La mezcla con fundamentales empata (β estimado ≈ 0.09: casi no mueve nada) y σ por cargo empata en CRPS con cobertura un poco más ancha.
- **Error de las encuestas por cargo** (nacional, + = pro-D): Senado +0.89 pp, gobernador +1.16, presidente +1.15. El Senado no tiene un sesgo propio que corregir; su MAE (4.86) es algo mayor, y la σ nacional ya lo cubre (cobertura 80 % de G en Senado: 78 %).
- **S5 (escala) gana en el Senado 2014+** (2.967 frente a 3.106, P = 0.97), pero pierde en el total (P = 0.06): captura el sesgo pro-D de 2014–2024, que ya corrige el sesgo estatal. No se adopta.
- **En NC_Sen (n = 9)** el sesgo solo con Senado (S2) y «sin sesgo» quedan algo mejor (P = 0.71 y 0.56): con 9 contiendas y P < 0.8 no se cambia la regla nacional. Quedan como escenarios.

**Decisión:** el modelo general de Ohio v1.2.0 funciona para el Senado y se mantiene sin cambios estructurales.

## 3. Selección del resto de piezas

**Leave-one-year-out, todas las contiendas** (`BACKTEST_NORTH_CAROLINA/salida/metricas_margen.csv`):

| Ámbito | G | Sin sesgo (H8) | Mejor alternativa |
|---|---|---|---|
| Nacional (992) | **3.202** | 3.322 | P1 casa + patrocinador 3.206 |
| Senado nacional (383) | **3.347** | 3.496 | P3 partidistas a la mitad 3.355 |
| NC, todas (23) | **1.963** | 2.021 | H3 cuota R de indecisos 1.970 |
| NC 2016+ (9) | **2.010** | 2.320 | F1 sin contraer 2.021 |

**Validación estrictamente cronológica** (parámetros solo con años anteriores, 2004–2024):

| Ámbito | G con sesgo | Sin sesgo | P(sin sesgo mejor) |
|---|---|---|---|
| Nacional (793) | **3.042** | 3.260 | 0.006 |
| Senado nacional (305) | **3.236** | 3.474 | 0.012 |
| NC (19) | **2.022** | 2.099 | 0.39 |
| NC 2016+ (9) | **2.061** | 2.413 | 0.31 |

**Regla del sesgo estatal:**
- «todas» (producción) frente a «k ≥ 2»: k2 gana a nivel nacional (LOYO P = 0.87; cronológico empata, 3.042 ambos), pero en NC pierde con claridad (LOYO P = 0.000; cronológico 2.052 frente a 2.022, P = 0.004) y hoy da casi lo mismo (−2.11 frente a −2.10). Se queda «todas», la regla de Ohio, Nueva York, Illinois y Texas.
- «por cargo» (solo Senado): cronológico NC_Sen 2.103 frente a 2.312 (P = 0.90, n = 7), pero Senado nacional 3.357 frente a 3.236 (P = 0.054). Escenario: −1.72 pp, P 94.3 % sin mercados y 95.3 % con mercados.

**Otras piezas:**
- **Indecisos:** 50/50. Repartirlos proporcionalmente (H2) o con cuota R estimada (H3) no mejora en ningún ámbito nacional.
- **Encuestas partidistas:** usar el efecto del patrocinador (P1), pesarlas a la mitad (P3) o descartarlas (P2) no mejora a G.
- **Terceros:** regla T4 (a + c·otros reportados). MAE de terceros en NC 0.79 pp frente a 2.15 con «terceros = 0».
- **Escala de ventajas grandes:** b = 1.003 fuera de muestra; las encuestas no comprimen las ventajas (ventaja ≥ 15 pp: error con signo −0.40). No se corrige.

## 4. Error histórico de las encuestas en North Carolina

Promedio V11 sin sesgo; + = las encuestas sobreestimaron al demócrata. **Pro-D en 16 de 23 contiendas y en las 10 desde 2014.**

| Año | Senado | Gobernador | Presidente |
|---|---|---|---|
| 2014 | +1.7 (Hagan −1.6) | — | — |
| 2016 | +4.6 (Burr +5.7) | +2.7 (Cooper +0.2) | +5.0 |
| 2020 | +5.2 (Tillis +1.8) | +6.2 (Cooper +4.5) | +3.5 |
| 2022 | +1.1 (Budd +3.2) | — | — |
| 2024 | — | +0.3 (Stein +14.8) | +2.2 |

- El sesgo bruto (vida media de 4 años) es +2.32 pp; la contracción por Bayes empírico (0.91) lo deja en +2.10, que se resta.
- **2024 gobernador** es el antecedente más parecido a hoy: ventaja demócrata grande con un candidato republicano débil. Ahí las encuestas acertaron (+0.3): si 2026 se parece a 2024 Gob, el sesgo sobra (escenario «sin sesgo»: +10.7, P 96.9 %).
- **Cooper en 2020** es el antecedente en contra: las encuestas le daban +10.7 y ganó por +4.5.

## 5. Encuestas

**Fuentes combinadas sin duplicados:** Wikipedia (47 encuestas tras elegir versiones), tu Excel (hoja «Histórico encuestas», 46; 45 tras aislar una) y 270toWin (10; 8 tras aislar dos). Resultado: **47 encuestas** desde el 28-jul-2025.

**Identidad (firma + periodo de campo).** El Excel marca con «¹» las encuestas con solo fecha de publicación. Se funden con su periodo de campo de Wikipedia:
- Harper 22-oct → 18–20 oct;
- Trafalgar 12-oct → 8–10 oct (y 11-sep → 8–10 sep);
- YouGov 23-sep → 15–18 sep;
- Quantus 23-sep → 21–22 sep;
- Opinion Diagnostics 25-sep → 17–20 sep.

**Alias nuevos:** «Harper Polling (R) — Carolina Journal» (Excel) = Harper Polling; «The Trafalgar Group» (Wikipedia) = Trafalgar Group. Sin el alias de Harper, la encuesta del 18–20 oct entraba dos veces en la ventana (31 % + 21 % del peso).

**Encuestas aisladas** (`data/encuestas_excluidas.csv`):
- **«YouGov» 20-oct de 270toWin (560 LV, 54–43):** es la encuesta Elon/YouGov 29 sep–8 oct (561 LV, 52–39), publicada el 20-oct; 270toWin trae la versión con indecisos inclinados. Contarla habría metido una cuarta encuestadora a la ventana con Cooper +11 (P 96.0 % en lugar de 94.8 %).
- **Catawba 30-sep (270toWin y Excel, 48–37):** es la Catawba/YouGov 4–15 sep (885 LV), publicada 15 días después del cierre, uno más que la tolerancia de 14 días de `identidad.py` (módulo común, no se toca).

**Patrocinio partidista** (marcas «(D)»/«(R)» de Wikipedia): Harper (encuestadora de Carolina Journal, de la John Locke Foundation), Trafalgar, Quantus, InsiderAdvantage, TIPP y Victory Insights (R); Change Research y PPP (D). Beacon/Shaw y Fabrizio/Impact son bipartidistas.

**Ventana de 21 días (desde el 13-oct):**

| Encuestadora | Campo | n | Cooper–Whatley | Corregido por casa | Peso |
|---|---|---|---|---|---|
| Quantus Insights (R) | 24–25 oct | 722 LV | 51–43 | +8.7 | 44 % |
| Harper Polling (R) | 18–20 oct | 600 LV | 49–39 | +10.6 | 31 % |
| ActiVote | 8–20 oct | 400 LV | 56.9–43.1 | +14.3 | 25 % |

Quedan fuera por pocos días: SurveyUSA 7–11 oct (+14), Trafalgar (R) 8–10 oct (+8), Elon/YouGov 29 sep–8 oct (+13), Change Research (D) 1–7 oct (+10), ECU 30 sep–3 oct (+7).

## 6. Mercados

- **Kalshi `SENATENC-26`:** Cooper 96.45 % (punto medio bid/ask), 1.7 M USD de volumen en el contrato D.
- **Polymarket `north-carolina-senate-election-winner`:** 97.0 / 2.5 → D / (D + R) = 97.5 %.
- **Trayectoria:** ~62–75 % a fines de 2025, ~85 % en primavera, > 90 % desde agosto y 96–97 % en octubre, tras la retirada de publicidad de Senate Leadership Fund y Old North Action.
- **Mezcla logit con peso 0.30** (fijo; no se recalibró para NC, como en Ohio): desplaza el margen +0.66 pp.
- **Polymarket por rangos de margen** (diagnóstico): 10 contratos, suma 1.016; margen ajustado +13.7 (σ 5.3). El mercado espera un margen ~4.5 pp mayor que el modelo: no corrige por el sesgo histórico de NC.

## 7. Electorado, indecisos y contexto

**Electorado**
- **Registro:** 7.82 millones de votantes: sin afiliación 39.9 %, R 29.8 %, D 29.6 %. Los republicanos superaron a los demócratas en 2026 por primera vez en décadas. Casi todas las altas nuevas (85–94 %) son sin afiliación.
- **Voto ya emitido (civicAPI, 27-oct):** 1.77 millones, 47 % del total de votos del Senado 2022. Por registro: D 41.0 %, sin afiliación 34.5 %, R 24.2 % (margen D−R +16.7). Al 18-oct el voto anticipado iba 37 % por encima de 2022 a la misma altura, y la participación republicana por debajo de 2018 y 2022.
- **Cómo leer el voto anticipado:** es registro partidario, no intención de voto. En 2024 los republicanos superaron a los demócratas en el voto anticipado en persona por primera vez; en 2026 la ventaja vuelve a los demócratas. Wake concentra el 12.6 % del voto emitido, con margen de registro +28. **Diagnóstico: no entra al pronóstico.**

**Indecisos**
- Las encuestas recientes reportan 2–12 % de indecisos y 2–5 % de terceros. Whatley es poco conocido (Harper, sep: favorable 26 % / desfavorable 42 %); Cooper tiene 47 / 43.
- Elon (20-oct) atribuye la ventaja de Cooper a moderados, independientes, votantes negros e hispanos y mujeres. Su director espera que la ventaja «se contraiga», porque los republicanos están menos motivados hoy pero suelen volver al final.
- **Regla del modelo:** 50/50. Repartir hacia el retador, hacia el conocido o proporcionalmente no mejora el backtest. El riesgo de «regreso a casa» republicano está en el sesgo estatal y en la σ.

**Contexto**
- **Escaño abierto:** Tillis (R) no se reelige. NC no elige a un demócrata al Senado desde 2008. Trump ganó NC en 2016, 2020 y 2024 por 1.3–3.6 pp.
- **Candidatos:** Cooper, exgobernador (ganó en 2016 por +0.2 y en 2020 por +4.5) y exfiscal general. Whatley, expresidente del RNC y del Partido Republicano de NC, nunca ha ocupado un cargo electo; ganó la primaria con 65 %.
- **Dinero:** Cooper recaudó más de 35 M USD frente a 16.1 M. El último anuncio de TV de Whatley salió el 7-oct, sin reservas para el cierre.
- **Temas:** costo de vida (76 % dice que está peor que hace dos años), salud, crimen y la reconstrucción del oeste tras Helene.
- **Calificaciones:** Cook y Sabato pasaron la contienda de «toss-up» a «Lean D» en abril–junio.
- **Recuento:** a petición si la diferencia es ≤ 0.5 % o ≤ 10,000 votos, lo que sea menor; con ~3.8 M de votos, ≈ 0.26 pp.

## 8. Fuentes revisadas y cuáles se agregan

| Fuente | Estado | Uso |
|---|---|---|
| Wikipedia (2026 United States Senate election in North Carolina) | En vivo | Encuestas (principal) |
| 270toWin (senado NC) | En vivo | Encuestas y fechas de publicación |
| Excel `NORTH_CAROLINA_SENADO.xlsx` | Archivo | Base verificada; en GitHub, su exportación CSV |
| Kalshi `SENATENC-26` y Polymarket (ganador y margen) | En vivo | Mezcla y diagnóstico |
| **civicAPI `early-vote/NC`**, por partido | En vivo | **Nuevo para NC:** voto emitido por partido y condado (diagnóstico) |
| FiveThirtyEight raw-polls + Wikipedia 2024 | En vivo / paquete | Calibración |
| NCSBE (estadísticas de registro, ausente) | Revisada | Registro: la página carga por JavaScript; se usa la cifra publicada (Carolina Journal). civicAPI ya trae los datos oficiales del voto anticipado |
| OnPoint Politics, poliagg | Revisadas | Sin encuestas nuevas frente a Wikipedia y 270toWin; no se agregan |
| Elon, High Point, Catawba, ECU, Carolina Journal (comunicados) | Revisadas | Verificación de cifras y fechas (Elon publicada el 20-oct) |
| ActiVote (página de NC) | 404 | — |

**Archivos de datos nuevos:**
- `data/encuestas_excluidas.csv` (aislamiento, regla traída de California y extendida a la base verificada);
- `data/mercados_nc_sen2026_diario.csv`;
- `data/diagnostico_electorado_2026.csv`.

## 9. Cambios en el código frente a Ohio v1.2.0

- **Cargo Senado en todo el paquete:**
  - `reporte.json` usa la clave `senado`;
  - las salidas se llaman `pronostico_senado.csv`, `escenarios_senado.csv` y `encuestas_senado.csv`;
  - el escenario de sesgo por cargo usa contiendas de Senado (`sesgo_contraido_cargo`, antes `_gob`).
- **`aislar_excluidas`:** filas de Wikipedia, 270toWin **y de la base verificada**. Se guardan en `salidas/ultimo/encuestas_aisladas.csv` y en `reporte.json`.
- **Gráfica:** el rango del histograma sigue a la simulación (el rango fijo −30..20 cortaba la cola de Cooper +20). El título dice «desde la nominación de hecho».
- **Sin «tercero principal»:** los terceros van en bloque.
- **Recuento 0.26 pp** y **semilla 20261103**.
- **Pruebas:** 50 pasan sin red (1 se omite en CI: la del Excel).

## 10. Limitaciones

- **La ventana de 21 días tiene solo 3 encuestadoras**, y el promedio depende de qué publiquen en la última semana. Una sola encuesta nueva puede mover el margen 1–2 pp.
- **El sesgo estatal se estima con 23 contiendas** y está dominado por 2016–2020. Si 2026 se parece a 2024 Gob (encuestas exactas con un republicano débil), el modelo subestima a Cooper en ~2 pp.
- **Los mercados (97 %) quedan por encima del modelo (95 %):** con peso 0.30 el modelo no los persigue. La diferencia es justamente el sesgo histórico de NC.
- **El voto anticipado por partido es muy favorable a los demócratas (+16.7)**, pero no se usa: los sin afiliación son un tercio y los demócratas registrados rurales de NC votan con frecuencia por republicanos.

## Fuentes
- [WFAE: candidatos al Senado de NC (20-oct-2026)](https://www.wfae.org/2026-10-20/u-s-senate-north-carolina)
- [Action Network: mercados, encuestas y dinero (21-oct-2026)](https://www.actionnetwork.com/news/north-carolina-senate-race-2026-cooper-vs-whatley-polls-predictions-nc-senate-race-odds)
- [WUNC: encuesta final de Elon (20-oct-2026)](https://www.wunc.org/2026-10-20/final-elon-university-poll-finds-double-digit-lead-for-cooper-in-the-race-for-us-senate)
- [WUNC: participación en el voto anticipado (19-oct-2026)](https://www.wunc.org/2026-10-19/north-carolina-sees-surge-in-early-voting-turnout)
- [ABC11: voto anticipado por partido](https://abc11.com/post/early-voting-turnout-surges-north-carolina/19956761/)
- [Eastern Progress: registro de votantes en NC](https://www.easternprogress.com/election-2026-choosing-independent-declines-to-only-85/article_dc1eefde-8d4f-5b66-9a6e-33993af8f638.html)
- [Newsweek: encuesta Harper de septiembre](https://newsweek.com/gop-faces-devastating-north-carolina-poll-from-republican-pollster-12457781)
- [Newsweek: encuesta AARP (Fabrizio/Impact)](https://www.newsweek.com/cooper-flips-trump-margin-with-independents-by-29-points-as-whatley-flops-12498753)
- [NC Newsline: calificaciones «Lean D»](https://ncnewsline.com/2026/06/11/north-carolinas-senate-race-no-longer-a-toss-up-top-forecasters-say-with-cooper-in-the-lead/)
- [Wikipedia: 2026 United States Senate election in North Carolina](https://en.wikipedia.org/wiki/2026_United_States_Senate_election_in_North_Carolina)
- [270toWin: encuestas del Senado de NC](https://270towin.com/2026-senate-polls/north-carolina)
