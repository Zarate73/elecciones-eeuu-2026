# Florida 2026 · Gobernador (general) · Investigación, backtest y modelo final

Corte: 22-oct-2026 (12 días a la elección del 3-nov).

Carpetas:
- [`modelo_general/`](../modelo_general/): notebook ejecutado, módulo, 8 pruebas y salidas.
- [`produccion/`](../produccion/): paquete `fl_pronostico` con todas las fuentes en vivo (GitHub Actions dos veces al día).
- [`backtest/`](../backtest/): backtest, datos y resultados.

## 1. Pronóstico
| Candidato | % de voto (IC80) | Probabilidad de ganar |
|---|---|---|
| David Jolly (D) | 44.8 % (41.5–48.2) | **5 %** |
| **Byron Donalds (R)** | **53.1 %** (49.8–56.5) | **95 %** |
| Terceros (Jewett, L; independientes) | 2.0 % | — |

- **Margen Jolly − Donalds:** −8.3 pp (σ 5.1; IC95 −18.4 a +1.8).
- **Cómo se llega:**
  - Promedio de encuestas: −5.3.
  - Sesgo estatal de Florida: −4.8 (las encuestas de FL sobreestiman al demócrata).
  - Resultado solo con encuestas: −10.1, con P(Jolly) 2.6 %.
  - Los mercados (21 %) suben la probabilidad a 5 % y mueven el margen +1.8.
- **P(recuento por máquina, |margen| ≤ 0.5 pp):** 1.9 %.

**Sensibilidad**

| Escenario | Margen | P(Jolly) |
|---|---|---|
| Final | −8.3 | 0.050 |
| Solo encuestas | −10.1 | 0.026 |
| **Sin sesgo estatal (regla de Arizona)** | −5.2 | 0.143 |
| Sesgo estatal sin contraer | −10.7 | 0.021 |
| Ventana de 45 días (11 encuestadoras) | −9.2 | 0.015 |
| Solo Kalshi | −3.7 | 0.223 |
| Solo Polymarket | −4.1 | 0.200 |
| Polymarket por rangos de margen | −4.8 | 0.213 |

La diferencia principal entre el modelo y los mercados es el sesgo estatal. Los mercados (y el mercado de rangos de Polymarket, que centra el margen en R+4.8) se parecen al promedio crudo de encuestas. El modelo agrega la corrección por el error histórico de las encuestas en Florida, que el backtest respalda con claridad (sección 4).

## 2. Fuentes

| Fuente | Qué aporta | Uso |
|---|---|---|
| Wikipedia (API) | 33 encuestas, 17 desde la primaria, con n, población y terceros | Pronóstico |
| 270toWin | 10 encuestas recientes; agrega Stetson, MDW y Change Research con fecha de publicación | Pronóstico (se deduplica) |
| Tu Excel (`FLORIDA_GOBERNADOR-v2.xlsx`) | 25 encuestas; 9 posteriores a la primaria | Pronóstico (se deduplica) |
| **Kalshi** `GOVPARTYFL-26` | Jolly 22.3 % | Mezcla, peso 0.30 (promedio con Polymarket) |
| **Polymarket** `florida-governor-winner-2026` | Jolly 20.0 % | Mezcla, peso 0.30 |
| Polymarket por rangos de margen | Margen implícito R+4.8 (σ 7.2) | Escenario |
| **civicAPI (FL)** | Votos ya emitidos por partido y condado (correo + en persona) | Diagnóstico |
| División de Elecciones de FL | Registro al cierre (5-oct) y reportes de voto anticipado | Electorado |
| On Point Politics `/api/polls/fl-gov-2026` | Promedio Donalds +4.8 | Contraste |

**Fuentes nuevas respecto a Arizona**
- **civicAPI de Florida** sí trae desglose por partido, igual que Arizona, y además separa correo y voto en persona.
- **Kalshi y Polymarket:** en Florida no son el mismo precio. Los niveles están correlacionados (0.86), pero los cambios diarios casi no (0.20), y la diferencia media es de 2.2 pp. Se promedian.
- **Se recomienda agregar** (no entra hoy porque no hay serie histórica para validarla) **la serie diaria de la División de Elecciones** (Vote-by-Mail y Early Voting por partido). Los reportes por votante son de acceso restringido; las estadísticas agregadas son públicas.

## 3. Electorado y comportamiento de los indecisos

**Registro al cierre (5-oct-2026, División de Elecciones vía WLRN)**
- Republicanos 5.69 millones (41.5 %), demócratas 4.15 millones (30.3 %), sin partido (NPA) 3.35 millones (24.5 %), otros 0.44 millones. Total: 13.7 millones.
- **Ventaja republicana: 1.54 millones (11.2 pp).** En 2018 era de unos 0.26 millones a favor de los demócratas.
- Entre la primaria y el cierre, ambos partidos sumaron casi lo mismo (+86.7 mil R, +85.1 mil D). En septiembre, los demócratas ganaron más registros netos por primera vez desde 2021.

**Primarias cerradas del 18-ago:** 1.70 millones de votos republicanos contra 1.25 millones demócratas. Donalds ganó con 47.8 % y Jolly con 61.0 %.

**Voto ya emitido (civicAPI, 22-oct)**
- **Total:** 1.68 millones de votos (1.12 millones por correo, 0.55 millones en persona).
- **Por partido:** D 41.2 %, R 38.2 %, NPA 18.2 % → **D+3.1**.
- **Por modalidad:** correo D+6.7; en persona R+4.4.

**Para leerlo con cuidado**
- Los demócratas votan por correo antes que los republicanos, y los republicanos dominan el día de la elección.
- En 2024, al 21-oct, los demócratas iban adelante en el correo por 71 mil, y Trump ganó Florida por 13.
- En 2022, al 31-oct, los republicanos ya iban adelante por 96 mil (R+3.5), y DeSantis ganó por 19.
- Que en 2026 los demócratas vayan adelante es mejor para ellos que 2022, pero se parece a 2024. Sin una serie del mismo día no se puede validar, así que queda como diagnóstico.

**Indecisos**
- Las encuestas recientes tienen entre 4 % y 11 % de indecisos. Mason-Dixon (28-sep a 1-oct) encontró a los independientes 47–28 a favor de Jolly y a los hispanos 48–43 a favor de Donalds, con más indecisos entre hombres (11 %) que entre mujeres (9 %).
- En el histórico nacional (848 contiendas), la cuota de indecisos que termina votando republicano se estima en **0.55**, estable en todos los años.
- Aplicarla (variante H3) no mejora el CRPS en Florida (2.209 contra 2.200), porque el error de Florida no viene de los indecisos. En 2022 y 2024 las encuestas tenían solo entre 0 % y 5 % de indecisos, y aun así fallaron por 7 a 8 pp: el error está en la composición de la muestra, y eso lo captura el sesgo estatal.
- **Regla adoptada: indecisos 50/50.**

## 4. Backtest (LOYO, horizonte de 12 días)
- **Datos:** FiveThirtyEight raw-polls 1998–2022 más 45 contiendas de 2024 (encuestas finales de Wikipedia; incluye Florida Presidente y Senado 2024). En total, 848 contiendas, 23 de ellas de Florida.
- **Métrica:** CRPS, más bootstrap por años.

| Variante | CRPS nacional | CRPS Florida (23) | CRPS FL 2016+ (9) | P(mejor que G) en FL |
|---|---|---|---|---|
| **G · Georgia V11 con sesgo estatal contraído** | **3.374** | 2.200 | 2.265 | — |
| F1 · sesgo estatal sin contraer | 3.502 | **2.168** | **2.144** | 0.67 |
| H8 · sin sesgo estatal (regla de Arizona) | 3.468 | 2.643 | 3.521 | **0.06** |
| H3 · cuota R de indecisos estimada | 3.393 | 2.209 | 2.339 | 0.41 |
| F2 · indecisos de la primaria FL (40/35/25) | 3.581 | 2.351 | 2.297 | 0.14 |
| H7 · pesos ∝ n (primaria FL) | 3.386 | 2.206 | 2.311 | 0.39 |
| H4 · Dirichlet y shocks (primaria) | 3.410 | 2.362 | 2.422 | 0.02 |
| H2 · indecisos proporcionales | 3.650 | 2.383 | 2.323 | 0.16 |

**Error de las encuestas en Florida** (promedio V11, + = sobreestimó al demócrata)
- Pro-D en 18 de 23 contiendas.
- 2018: Gob +3.9, Sen +2.0.
- 2020: Pres +4.3.
- 2022: Gob +8.2, Sen +8.3.
- 2024: Pres +6.6, Sen +8.4.

**Error relativo a la media nacional del año:** +3.0 (2018), +6.4 (2022), +4.7 (2024). La autocorrelación año a año es casi nula (0.04), pero el nivel medio es claramente positivo. Por eso el sesgo estatal ayuda en Florida y no en Arizona: en Arizona el error cambia de signo entre ciclos, mientras que en Florida apunta casi siempre hacia el mismo lado.

**Decisión: G**, con sesgo estatal contraído (−4.83 pp; el bruto es −5.42 y la contracción 0.89).
- F1 es algo mejor en Florida, pero no de forma significativa (P = 0.67) y empeora a nivel nacional (P = 0.03). Adoptarla sería elegir con 23 contiendas una regla que falla en general.
- Queda como escenario (−10.7, P(Jolly) 2.1 %).

**Modelo de la primaria de Florida.** No se adopta nada:
- el reparto de indecisos FIX v8 (40 % proporcional, 35 % fragmentado, 25 % consolidación hacia el líder) es peor en todos los ámbitos;
- los pesos ∝ n y el motor Dirichlet también empeoran el error;
- el prior bayesiano de fundamentales no se puede validar (en Georgia, los fundamentales empeoraron el CRPS).

**Terceros calibrados** (`real = 1.85 + 0.64 · otros en encuestas`): bajan el error del % de Jolly de 2.10 a 1.49 pp en Florida. Desde la v1.1.0, «no reportado» ≠ 0 %: `real = 0.81 + 0.73 · otros reportados`, o 1.92 pp si ninguna encuesta los reporta ([revisión del 22-oct](02_revision_externa_2026-10-22.md)).

## 5. Mercados
- **Hoy:** Kalshi 22.3 %, Polymarket 20.0 %, promedio 21.1 %.
- **Peso:** 0.30, estimado por máxima verosimilitud con 40 contiendas de 2024 (ver `arizona/docs/03_peso_mercados.md`; la contienda FL Pres 2024 está incluida).
- **En Florida 2024 los mercados ayudaron.** A 13 días daban a Trump 92.5 % y las encuestas tenían un margen de −10.4; el resultado fue −13.1.
- **Lo que mueven hoy:** la distribución se desplaza +1.8 pp y P(Jolly) pasa de 2.6 % a 5.0 %.

## 6. Limitaciones
- **Ventana de 4 encuestadoras.** Solo 4 terminan en los últimos 21 días: Univision/YouGov (RV), ActiVote, UNF y co/efficient (R). Con 45 días entran 11 y el margen casi no cambia (−9.2).
- **El sesgo estatal es el supuesto que más pesa:** sin él, P(Jolly) sería 14 %. El backtest lo respalda con fuerza (P = 0.06 de que quitarlo mejore), pero es un supuesto sobre el futuro: si los encuestadores de Florida corrigieron su muestra después de 2024, el modelo estaría sobrecorrigiendo.
- **El voto anticipado (D+3.1)** va en dirección contraria a la corrección, pero sin una serie histórica del mismo día no se puede usar.

Fuentes: [WLRN, registro al 5-oct-2026](https://www.wlrn.org/government-politics/2026-10-19/florida-democrats-see-minor-gain-but-republicans-keep-large-1-5-million-edge-with-registered-voters) · [Newsweek, encuestas de octubre](https://www.newsweek.com/byron-donalds-vs-david-jolly-latest-polls-show-two-very-different-results-12564501) · [NBC 6, Mason-Dixon](https://www.nbcmiami.com/elections/florida-poll/3869071/) · [Florida Trend, correo al 13-oct](https://www.floridatrend.com/articles/2026/10/13/more-than-500000-votes-cast-general-election/) · [FOX 35, voto anticipado 2022](https://www.fox35orlando.com/news/republicans-outpace-democrats-in-floridas-early-voting) · [MCI Maps, correo 2024](https://mcimaps.substack.com/p/issue-204-in-person-early-voting) · [Political Wire, Change Research](https://politicalwire.com/2026/10/12/dead-heat-in-florida-governors-race/) · [WLRN, encuesta de NPA (abril)](https://www.wlrn.org/government-politics/2026-04-13/poll-npas-giving-florida-democrats-a-legitimate-chance-in-november)
