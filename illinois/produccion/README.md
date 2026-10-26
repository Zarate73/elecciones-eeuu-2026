# Illinois 2026 · Modelo general (paquete `il_pronostico`)

Paquete de Python del modelo de Illinois: el gobernador JB Pritzker (D) contra Darren Bailey (R), con Collin Corbett (independiente). Gana la mayoría simple. Usa la misma estructura que las producciones de Arizona, Florida, Nevada, Pennsylvania, Maine y Texas: línea de comandos, configuración en `config/illinois.toml`, registros, pruebas sin red y tarea programada de Windows.

**Todas las fuentes se consultan en vivo en cada corrida.** Si una falla, se usa su última copia y el reporte lo marca.

## Modelo (elegido por backtest, ver `../docs/01_investigacion_y_modelo.md`)
- **Promedio:** V11 de Georgia: efectos de casa contraídos (k = 8), √n, vida media de 14 días y cada firma pesa ~1. La ventana es de 21 días; si hay menos de 2 encuestadoras, se toman los 21 días previos a la encuesta más reciente. **Hoy se amplía:** solo ActiVote (2–22 oct) termina en los últimos 21 días; con la ampliación entra PPP (30 sep–1 oct).
- **Identidad de una encuesta = firma + periodo de campo** (revisión de Texas). La fecha puntual de 270toWin es de publicación (PPP aparece el 6-oct; el campo fue 30 sep–1 oct).
- **Alias:** «Public Policy Polling — Chicago News Weekly» (Excel) = «Public Policy Polling (D)» (Wikipedia); WGN-TV = Emerson.
- **Sesgo estatal:** contraído por Bayes empírico con todas las contiendas del estado (`sesgo_regla = "todas"`). Hoy **suma** 1.20 pp al demócrata: en Illinois las encuestas tendieron a subestimarlo. «Sin sesgo», «k ≥ 2» y «solo gobernador» quedan como escenarios.
- **Terceros (Corbett):** `real = a + c·otros`, con «otros» promediado solo entre las encuestas que los reportan. El Excel junta «indecisos / otros», así que no reporta terceros.
- **Indecisos:** 50/50.
- **σ:** `√(τ² + s²/k)`, t de Student, con una deriva de 0.25 pp/día cuando las encuestas son más viejas que el horizonte.
- **Mercados:** Kalshi `GOVPARTYIL-26` y Polymarket `illinois-governor-winner-2026`, promediados, en mezcla logit con peso 0.30 (D / (D + R)). Con probabilidades cercanas a 1 la mezcla baja el margen (hoy −2.2 pp) aunque los mercados también den ganador a Pritzker.
- **Escenarios:** cruce 2 × 2 de sesgo × mercados, sesgo k ≥ 2 y por cargo, influencia de cada encuesta, sin encuestas partidistas, terceros con reducción, peso de mercados 0.15/0.50 y Polymarket por rangos.
- **Voto anticipado (civicAPI):** Illinois no tiene registro partidario: solo volumen (correo + en persona) por condado y por las ciudades con junta electoral propia (Chicago, Rockford…). Diagnóstico, no entra al pronóstico.

## Fuentes
| Fuente | Vía | Uso |
|---|---|---|
| Wikipedia | API MediaWiki | Encuestas |
| 270toWin | Página HTML | Encuestas |
| Base verificada | Excel (hoja «Histórico encuestas» de `ILLINOIS_GOBERNADOR-v1.xlsx`) o `data/encuestas_verificadas_il.csv` | Encuestas |
| Kalshi y Polymarket | APIs públicas | Mezcla (peso 0.30) y rangos de margen (escenario) |
| civicAPI | `early-vote/IL/{returned,inperson}` (por condado y ciudad, sin partido) | Diagnóstico del voto ya emitido |
| FiveThirtyEight raw-polls | GitHub | Calibración |
| Correcciones de cifras | `data/correcciones_cifras.csv` | D y R de la publicación original cuando Wikipedia redondea (hoy vacío) |
| Correcciones de n | `data/correcciones_tamano_muestra.csv` | Tamaños verificados; n faltante = 600 marcado en `n_imputado` (hoy vacío: las dos encuestas traen n) |

## Uso
```
python -m il_pronostico correr             # fuentes en vivo
python -m il_pronostico correr --offline   # solo cachés
python -m il_pronostico verificar          # revisa cada fuente
python -m pytest -q                        # pruebas sin red (respuestas reales del 25-oct-2026)
```
En Windows: `scripts\instalar.bat` y luego `scripts\correr_pronostico.bat`.
