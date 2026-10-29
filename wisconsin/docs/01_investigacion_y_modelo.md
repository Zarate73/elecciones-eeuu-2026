# Wisconsin 2026 · Gobernador · Investigación y modelo general

Corte: 28-oct-2026, con la captura en vivo del 29-oct a las 02:15 UTC (28-oct, 21:15 CT), 6 días antes de la elección del 3-nov. Paquete `wi_pronostico` v1.0.0, base North Carolina v1.0.0 / Ohio v1.2.0.

## 1. Pronóstico al 28-oct

| Gobernador | % de voto (IC80) | Probabilidad de ganar |
|---|---|---|
| David **Crowley** (D) | **52.8 %** (48.7–56.9) | **81.9 %** |
| Tom **Tiffany** (R) | **47.1 %** (43.0–51.1) | **18.1 %** |
| Votos por escrito | 0.1 % | — |

- **Margen D−R:** +5.8 pp (σ 6.5; IC95 −7.2 a +18.7).
- **Cómo se llega:** promedio de encuestas +5.49 · sin sesgo estatal · mercados +0.27 → +5.76.
- **Probabilidades:** solo encuestas 80.8 %; Kalshi 83.5 %; Polymarket 85.3 %; final 81.9 %.
- **Recuento:** P(|margen| ≤ 1 pp, recuento a petición) = 8.2 %.

**Lectura.** Crowley es favorito, pero no por mucho, y el modelo coincide con los mercados. La probabilidad queda en ~82 % por dos razones:
1. **Muy pocas encuestas.** En la ventana de 21 días solo hay dos encuestadoras:
   - Marquette (14–22 oct): 51–44 entre probables y 47–44 entre registrados;
   - Wick (R) (19–23 oct): 48–45.

   Con k = 2, σ = 6.5. Quitar Marquette baja el margen a +4.1 (P 74 % sin mercados). Quitar Wick lo deja en +5.3 (P 83 %).
2. **El modelo de votantes probables importa.** Marquette muestra que la ventaja de Crowley viene de quienes están seguros de votar. Entre quienes son «muy probables pero no seguros», Tiffany va 42–30: si la participación se amplía, la carrera se cierra.

## 2. Selección del modelo

**Marco:** leave-one-year-out (LOYO), ventana de producción (6 ≤ días ≤ 21), 1003 contiendas de 1998–2024, 25 de Wisconsin (8 de gobernador). CRPS del margen (menor es mejor).

| Ámbito | G (con sesgo) | **Sin sesgo (H8)** | P(H8 mejor), bootstrap por año |
|---|---|---|---|
| Nacional (1003) | **3.158** | 3.278 | 0.08 |
| Gobernador nacional (307) | 3.317 | **3.290** | 0.55 |
| WI, todas (25) | 2.822 | **2.630** | 0.88 |
| WI, gobernador (8) | 3.147 | **2.924** | 0.93 |
| WI 2016+ (9) | 2.693 | **2.462** | — |

**Validación estrictamente cronológica** (parámetros solo con años anteriores):

| Ámbito | Con sesgo | Sin sesgo | Por cargo |
|---|---|---|---|
| Nacional (800) | **3.016** | 3.221 | 3.104 |
| WI (20) | 2.129 | **2.049** | 2.101 |
| WI gobernador (6) | 1.985 | **1.658** | 1.726 |

**Decisión: sin sesgo estatal** (regla de Arizona).
- El sesgo estatal ayuda a nivel nacional, pero en Wisconsin empeora el pronóstico en LOYO y en el cronológico. La razón es que **el error de las encuestas en WI cambia de signo**:
  - presidente 2016 +5.9 y 2020 +7.4 pro-D, Senado 2016 +5.9;
  - gobernador 2022 −4.1, Senado 2022 −2.1 y gobernador 2010 −2.4, pro-R;
  - 2024 casi exacto: presidente +1.6, Senado +0.6.
- La autocorrelación del error relativo entre ciclos es **−0.36**: el error de un ciclo no predice el del siguiente, y si acaso lo revierte.
- Hoy el sesgo contraído es pequeño (+0.50 pp pro-D). Aplicarlo daría +5.0 y P 80.4 %. Queda como escenario, junto con sus variantes:
  - sin contraer: −0.65;
  - solo gobernador: +0.51 (signo contrario);
  - sin 2022 gobernador: −0.96.

**Otras piezas:**
- **Variantes por cargo:** σ por cargo, sesgo nacional del cargo, fundamentales y escala del margen no mejoran a G en ningún ámbito de WI. El sesgo por cargo mejora en WI (2.669), pero menos que quitar el sesgo.
- **Indecisos:** 50/50. Repartirlos proporcionalmente (H2) o con cuota R estimada (H3) empeora en WI y a nivel nacional.
- **Encuestas partidistas:** efecto del patrocinador (P1), pesarlas a la mitad (P3) o descartarlas (P2) no mejoran.
- **Escala de ventajas grandes:** b = 1.005; no se corrige.
- **Terceros:** solo dos candidatos en la boleta. Los votos por escrito son fijos en 0.10 ± 0.05 % (2022: 0.07 %), como en Nueva York; la regla T4 asignaría ~3 % a terceros que no existen.

## 3. Encuestas

- **Fuentes combinadas sin duplicados:** Wikipedia (11 encuestas tras elegir versiones), tu Excel (hoja «Histórico encuestas», 9) y 270toWin (9). Resultado: **11 encuestas** desde marzo.
- **Nuevas frente a tu Excel:**
  - Marquette 14–22 oct (51–44 LV; 47–44 RV), publicada el 28-oct;
  - Wick (R) 19–23 oct (48–45, 1,213 LV).
- **Alias nuevos:** Marquette con tres nombres («Marquette University», «Marquette Law School»); «TIPP» = TIPP Insights; Badger Battleground = Platform Communications; RMG/Napolitan y YouGov/City Forward. Sin estos alias las encuestas se contaban dos veces.
- **Patrocinio partidista** (marcas de Wikipedia): TIPP, Platform y Wick (R); GBAO, Z to A y YouGov/City Forward (D).

| Ventana de 21 días (desde el 13-oct) | Campo | n | Crowley–Tiffany | Corregido por casa | Peso |
|---|---|---|---|---|---|
| Wick (R) | 19–23 oct | 1,213 LV | 48–45 | +4.4 | 59 % |
| Marquette | 14–22 oct | 668 LV | 51–44 | +7.0 | 41 % |

Quedan fuera por pocos días: YouGov/City Forward (22 sep–9 oct, adultos, 46–42), Z to A (D) (28 sep–1 oct, 49–44) y Marquette de septiembre (49–46).

## 4. Mercados

- **Kalshi `GOVPARTYWI-26`:** 83.5 / 16.5 (punto medio); ~1.6 M USD entre los dos contratos.
- **Polymarket `wisconsin-governor-winner-2026`:** 84 / 14.5 → 85.3 % D/(D+R); ~0.9 M USD.
- **Trayectoria** (serie diaria):
  - 62–75 % a fines de 2025, sin candidato demócrata definido;
  - ~80 % en primavera;
  - caída a ~55 % antes de la primaria, cuando Hong lideraba las encuestas de la primaria;
  - 78–85 % desde la victoria de Crowley.
- **Mezcla logit con peso 0.30:** desplaza el margen +0.27 pp.
- **Polymarket por rangos de margen** (diagnóstico): margen ajustado +4.9 (σ 4.1), muy cerca del modelo.

## 5. Electorado, indecisos y contexto

**Electorado**
- Wisconsin **no tiene registro partidario**.
- **Voto ya emitido** (civicAPI, 28-oct): 873 mil boletas (574 mil por correo devueltas, 299 mil en persona), el 33 % del total de votos de gobernador 2022. Milwaukee aporta el 15.8 %. Es solo volumen: no entra al pronóstico.
- **Identificación partidista** (Marquette, sept, registrados): R 36 %, D 32 %, independientes 25 %.
- **Participación:** el 84 % de los demócratas está seguro de votar, frente al 77 % de los republicanos. La ventaja de entusiasmo demócrata es de 8 pp, estable desde septiembre.

**Indecisos** (Marquette, 28-oct)
- Indecisos: 4 % entre votantes probables y 9 % entre registrados. Los partidarios casi no tienen indecisos: 3 % de los R y 2 % de los D.
- **Independientes probables:** Crowley 56, Tiffany 26, indecisos 18. En septiembre los indecisos eran 38 % y Crowley iba 44–18: los independientes que decidieron se fueron mayoritariamente con Crowley.
- **Quienes no están seguros de votar** se inclinan por Tiffany: 42–30 entre los «muy probables», 45–35 entre los que «quizá no voten». El riesgo para Crowley es una participación más alta de lo previsto, no los indecisos.
- **Regla del modelo:** 50/50. El backtest no premia otros repartos, y los indecisos actuales son pocos.

**Contexto**
- **Escaño abierto:** Evers (D) no busca un tercer periodo y respaldó a Crowley.
- **Primarias:**
  - Crowley ganó la demócrata por 0.46 pp sobre la socialista democrática Francesca Hong, que ahora hace campaña por él.
  - Tiffany ganó la republicana con 95 %.
- **Dinero:** Tiffany y sus aliados superan a Crowley en publicidad, 53 M USD frente a ~35 M (AdImpact). Tiffany recaudó más de 26 M en el último bimestre, más de 24 M de tres donantes.
- **Temas:**
  - Tiffany se distancia de Trump en la guerra con Irán y en los centros de datos de IA, y ataca a Crowley por crimen y por los centros de datos.
  - Crowley ata a Tiffany a Trump, los aranceles y la gasolina.
  - Aprobación de Trump en WI: 37 %.
- **Historia:** cinco de las últimas siete presidenciales se decidieron por menos de 1 pp. Evers ganó en 2018 por +1.1 y en 2022 por +3.4.
- **Calificaciones:** «Toss-up» o «Lean D» desde agosto.
- **Recuento:** un candidato puede pedirlo si pierde por ≤ 1 % (gratis si es ≤ 0.25 %).

## 6. Fuentes revisadas y cuáles se agregan

| Fuente | Estado | Uso |
|---|---|---|
| Wikipedia (2026 Wisconsin gubernatorial election) | En vivo | Encuestas (principal) |
| 270toWin (gobernador WI) | En vivo | Encuestas y fechas de publicación |
| Excel `WISCONSIN_GOBERNADOR.xlsx` | Archivo | Base verificada; en GitHub, su exportación CSV |
| Kalshi `GOVPARTYWI-26` y Polymarket (ganador y margen) | En vivo | Mezcla y diagnóstico |
| civicAPI `early-vote/WI` | En vivo | Volumen por condado (72), sin partido |
| FiveThirtyEight raw-polls + Wikipedia 2024 (WI Pres y Sen) | En vivo / paquete | Calibración |
| **Marquette Law School Poll** (comunicado) | Revisada | Detalle de indecisos, independientes y participación (no cambia cifras: Wikipedia ya la trae) |
| WEC (Comisión Electoral) | 403 desde GitHub | civicAPI ya trae sus datos de voto anticipado |
| OnPoint Politics, poliagg | Revisadas | Sin encuestas nuevas frente a Wikipedia y 270toWin |

## 7. Cambios en el código frente a North Carolina v1.0.0

- **`sesgo_estatal = false`** (regla de Arizona). El primer escenario se rotula «Sin sesgo estatal, sin mercados (solo encuestas)»; antes decía «Con sesgo» aunque no se aplicara.
- **Clave del cargo genérica:** `reporte.json` y los CSV usan el cargo de la configuración (`gobernador`, `senado`).
- **Votos por escrito fijos** (`terceros_fijos = [0.10, 0.05]`), como en Nueva York.
- **Alias de Wisconsin** y población «Adultos» del Excel → A.
- **Recuento 1 pp**, zona horaria Central y semilla 20261104.
- **Cliente de Wikipedia:** identificado según la política de Wikimedia (corrección del 27-oct).
- **Pruebas:** 52 pasan sin red.

## 8. Limitaciones

- **Dos encuestadoras en la ventana:** una encuesta nueva puede mover el margen 1–3 pp.
- **Sin sesgo estatal:** si 2026 repite el patrón de las presidenciales 2016 y 2020 (encuestas pro-D), Crowley estaría sobreestimado. La evidencia de gobernador (2022 pro-R) apunta en contra. El escenario «con sesgo» da P 80 %.
- **El voto anticipado no tiene partido:** no sirve para leer la participación por bando.

## Fuentes
- [Marquette Law School Poll: encuesta final (28-oct-2026)](https://law.marquette.edu/poll/)
- [AP vía TMJ4: Tiffany se distancia de Trump; dinero y publicidad](https://www.tmj4.com/america-votes/wisconsins-republican-candidate-for-governor-keeps-his-distance-from-trump-in-nail-biter-campaign)
- [Ballotpedia: candidatos y contexto](https://news.ballotpedia.org/2026/08/24/crowley-tiffany-run-in-wisconsin-governor-race-that-will-influence-trifecta-triplex-status/)
- [Fox 11: Marquette de septiembre](https://fox11online.com/news/election/2026-wisconsin-governor-race-democrat-david-crowley-republican-tom-tiffany-marquette-university-law-school-poll-september)
- [TMJ4: Badger Battleground (agosto)](https://www.tmj4.com/news/local-news/new-wisconsin-poll-shows-independent-voters-could-be-key-in-governors-race)
- [Political Wire: YouGov/City Forward](https://politicalwire.com/2026/10/16/crowley-leads-tiffany-in-wisconsin-governors-race-2/)
- [Wikipedia: 2026 Wisconsin gubernatorial election](https://en.wikipedia.org/wiki/2026_Wisconsin_gubernatorial_election)
