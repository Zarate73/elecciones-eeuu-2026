# Wisconsin 2026 · Gobernador · Modelo general (paquete `wi_pronostico`)

Paquete de Python del modelo de Wisconsin: David Crowley (D), ejecutivo del condado de Milwaukee, contra Tom Tiffany (R), congresista del distrito 7, por la gubernatura que deja Tony Evers (D). Solo ellos dos están en la boleta (más votos por escrito). Gana la mayoría simple. Usa la misma estructura que las producciones de North Carolina, Ohio, Nueva York, Illinois, Texas, Maine, Pennsylvania, Nevada, Florida y Arizona.

**Todas las fuentes se consultan en vivo en cada corrida.** Si una falla, se usa su última copia y el reporte lo marca.

## Modelo (elegido por backtest, ver `../docs/01_investigacion_y_modelo.md`)
- **Promedio:** V11 de Georgia.
  - Efectos de casa contraídos (k = 8), √n, vida media de 14 días; cada firma pesa ~1.
  - Ventana de 21 días a la elección (desde el 13-oct); si hay menos de 2 encuestadoras, se toman los 21 días previos a la encuesta más reciente.
  - **Hoy entran dos encuestadoras:** Marquette (14–22 oct, 51–44 LV) y Wick (R) (19–23 oct, 48–45).
- **Identidad de una encuesta = firma + periodo de campo** (`identidad.py`, común a los paquetes).
- **Alias:** Marquette con tres nombres («Marquette University», «Marquette Law School»); «TIPP» = TIPP Insights; Badger Battleground = Platform Communications; RMG/Napolitan y YouGov/City Forward (Excel).
- **Sin sesgo estatal (regla de Arizona).** El error de las encuestas en Wisconsin cambia de signo: presidente 2016 +5.9 y 2020 +7.4 pro-D; gobernador 2022 −4.1 pro-R.
  - LOYO WI: sin sesgo 2.630 frente a 2.822 con sesgo (P = 0.88); gobernador WI 2.924 frente a 3.147 (P = 0.93).
  - Cronológico WI: 2.049 frente a 2.129.
  - A nivel nacional el sesgo sí ayuda: «con sesgo» queda como escenario (hoy −0.50 pp, P 80.4 %).
- **Terceros:** solo Crowley y Tiffany en la boleta; votos por escrito fijos (0.10 ± 0.05 %), como Nueva York.
- **Indecisos:** 50/50.
- **σ:** `√(τ² + s²/k + 0.25²·d)`, t de Student. Con k = 2, σ = 6.5 pp.
- **Mercados:** Kalshi `GOVPARTYWI-26` y Polymarket `wisconsin-governor-winner-2026`, promediados, en mezcla logit con peso 0.30 (D / (D + R)).
- **Recuento:** un candidato puede pedirlo si pierde por ≤ 1 % del total (gratis si es ≤ 0.25 %); se reporta P(|margen| ≤ 1).
- **Voto anticipado (civicAPI):** Wisconsin no tiene registro partidario, así que solo hay volumen por condado (72): boletas por correo solicitadas y devueltas, y voto en persona. Es diagnóstico: no entra al pronóstico.

## Reconstruir un corte pasado
`python -m wi_pronostico correr --corte 2026-10-24` con un corte anterior a hoy es una **reconstrucción** (regla OH-05): solo entran encuestas publicadas al corte, los mercados se toman al cierre del día del corte y el voto anticipado solo de snapshots ≤ corte.

## Fuentes
| Fuente | Vía | Uso |
|---|---|---|
| Wikipedia | API MediaWiki (UA identificado según la política de Wikimedia) | Encuestas |
| 270toWin | Página HTML | Encuestas y fechas de publicación |
| Base verificada | Excel (hoja «Histórico encuestas» de `WISCONSIN_GOBERNADOR.xlsx`) o `data/encuestas_verificadas_wi.csv` | Encuestas |
| Kalshi y Polymarket | APIs públicas | Mezcla (peso 0.30) y rangos de margen (escenario) |
| civicAPI | `early-vote/WI/{returned,requested,inperson}` (72 condados, sin partido) | Diagnóstico del voto ya emitido |
| FiveThirtyEight raw-polls | GitHub | Calibración |
| Encuestas complementarias, aisladas y correcciones | `data/encuestas_complementarias_wi.csv`, `data/encuestas_excluidas.csv`, `data/correcciones_*.csv` | Hoy vacías |

## Uso
```
python -m wi_pronostico correr             # fuentes en vivo
python -m wi_pronostico correr --offline   # solo cachés
python -m wi_pronostico verificar          # revisa cada fuente
python -m pytest -q                        # pruebas sin red (respuestas reales del 28-oct-2026)
```
En Windows: `scripts\instalar.bat` y luego `scripts\correr_pronostico.bat`.
