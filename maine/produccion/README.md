# Maine 2026 · Modelo general (paquete `me_pronostico`)

Paquete de Python del modelo de Maine: Hannah Pingree (D) contra Bobby Charles (R), con Rick Bennett (independiente). Elección abierta, por mayoría simple: la general de gobernador no usa voto preferencial. Usa la misma estructura que las producciones de Arizona, Florida, Nevada y Pennsylvania: línea de comandos, configuración en `config/maine.toml`, registros, pruebas sin red y tarea programada de Windows.

**Todas las fuentes se consultan en vivo en cada corrida.** Si una falla, se usa su última copia y el reporte lo marca.

## Modelo (elegido por backtest, ver `../docs/01_investigacion_y_modelo.md`)
- **Promedio:** V11 de Georgia: efectos de casa contraídos (k = 8), √n, vida media de 14 días y cada firma pesa ~1. La ventana es de 21 días; si hay menos de 2 encuestadoras, se toman los 21 días previos a la encuesta más reciente. Si una encuesta trae versión LV y RV, se usa la LV.
- **Alias:** la misma encuestadora aparece con el medio o con la firma (Fox News = Beacon/Shaw, AARP = Fabrizio Ward/Impact, CNN = SSRS, NYT/PPH = Siena). Se unifica con la clave del histórico de FiveThirtyEight. Las encuestas bipartidistas no se tratan como partidistas.
- **Sesgo estatal:** contraído por Bayes empírico y estimado **sin contiendas de una sola encuestadora** (`sesgo_regla = "k2"`). Hoy resta 2.43 pp al margen: en Maine las encuestas sobreestimaron al demócrata. La estimación con todas las contiendas (−4.03) queda como escenario.
- **Terceros (Bennett):** `real = a + c·otros`, con «otros» promediado solo entre las encuestas que los reportan; si ninguna los reporta, se usa la media histórica. Un careo forzado (CBS/YouGov, sin Bennett) cuenta como «no reportado», no como 0.
- **Indecisos:** 50/50.
- **σ:** `√(τ² + s²/k)`, t de Student, con una deriva de 0.25 pp/día cuando las encuestas son más viejas que el horizonte.
- **Mercados:** Kalshi `GOVPARTYME-26` y Polymarket `maine-governor-winner-2026`, promediados, en mezcla logit con peso 0.30. Kalshi tiene además un contrato de Bennett; la probabilidad comparable es D / (D + R).
- **Escenarios:** cruce 2 × 2 de sesgo × mercados, sesgo con todas las contiendas, influencia de cada encuesta, terceros con reducción, peso de mercados 0.15/0.50 y Polymarket por rangos (con el contrato «gana un independiente»).

## Fuentes
| Fuente | Vía | Uso |
|---|---|---|
| Wikipedia | API MediaWiki | Encuestas |
| 270toWin | Página HTML | Encuestas |
| Base verificada | Excel (hoja «Histórico encuestas») o `data/encuestas_verificadas_me.csv` | Encuestas |
| Kalshi y Polymarket | APIs públicas | Mezcla (peso 0.30) y rangos de margen (escenario) |
| civicAPI | `early-vote/ME/{returned,inperson,requested}` (por municipio) | Diagnóstico del voto ausente |
| FiveThirtyEight raw-polls | GitHub | Calibración |
| Correcciones de n | `data/correcciones_tamano_muestra.csv` | Tamaños verificados (hoy vacío); n faltante = 600 marcado en `n_imputado` |

## Uso
```
python -m me_pronostico correr             # fuentes en vivo
python -m me_pronostico correr --offline   # solo cachés
python -m me_pronostico verificar          # revisa cada fuente
python -m pytest -q                        # pruebas sin red (respuestas reales del 24-oct-2026)
```
En Windows: `scripts\instalar.bat` y luego `scripts\correr_pronostico.bat`.
