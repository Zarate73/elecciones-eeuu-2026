# Texas 2026 · Modelo general (paquete `tx_pronostico`)

Paquete de Python del modelo de Texas: Gina Hinojosa (D) contra el gobernador Greg Abbott (R), con Pat Dixon (libertario). Gana la mayoría simple; no hay segunda vuelta en la general. Usa la misma estructura que las producciones de Arizona, Florida, Nevada, Pennsylvania y Maine: línea de comandos, configuración en `config/texas.toml`, registros, pruebas sin red y tarea programada de Windows.

**Todas las fuentes se consultan en vivo en cada corrida.** Si una falla, se usa su última copia y el reporte lo marca.

## Modelo (elegido por backtest, ver `../docs/01_investigacion_y_modelo.md`)
- **Promedio:** V11 de Georgia: efectos de casa contraídos (k = 8), √n, vida media de 14 días y cada firma pesa ~1. La ventana es de 21 días; si hay menos de 2 encuestadoras, se toman los 21 días previos a la encuesta más reciente. Si una encuesta trae versión LV y RV, se usa la LV.
- **Alias:** la misma encuestadora aparece con el medio o con la firma (Fox News = Beacon/Shaw, Texas A&M = ReconMR/Siena, UH Hobby School = University of Houston, UT/Texas Politics Project, Cook Political Report = GS Strategy/New River). Se unifica con la clave del histórico de FiveThirtyEight. Las encuestas bipartidistas no se tratan como partidistas.
- **Duplicados:** se busca el candidato más cercano en fecha. Una firma que repite cifras en fechas distintas dentro de la misma fuente (Beacon/Shaw 47–52 el 28-sep y el 19-oct) cuenta dos veces; «YouGov» genérico de 270toWin con las mismas cifras que «CBS News/YouGov» a ≤ 7 días es la misma encuesta.
- **Sesgo estatal:** contraído por Bayes empírico con todas las contiendas del estado (`sesgo_regla = "todas"`). Hoy resta 2.50 pp al margen: en Texas las encuestas sobreestimaron al demócrata en 14 de 20 contiendas. Las estimaciones sin contiendas de una sola encuestadora (−2.88), solo con contiendas de gobernador (+0.08) y «sin sesgo» quedan como escenarios.
- **Terceros (Dixon):** `real = a + c·otros`, con «otros» promediado solo entre las encuestas que los reportan; si ninguna los reporta, se usa la media histórica.
- **Indecisos:** 50/50.
- **σ:** `√(τ² + s²/k)`, t de Student, con una deriva de 0.25 pp/día cuando las encuestas son más viejas que el horizonte.
- **Mercados:** Kalshi `GOVPARTYTX-26` y Polymarket `texas-governor-winner-2026`, promediados, en mezcla logit con peso 0.30 (D / (D + R)).
- **Escenarios:** cruce 2 × 2 de sesgo × mercados, sesgo k ≥ 2 y por cargo, influencia de cada encuesta, sin encuestas partidistas, terceros con reducción, peso de mercados 0.15/0.50 y Polymarket por rangos.
- **Voto anticipado (civicAPI):** Texas no tiene registro partidario: solo volumen (en persona + correo) por condado. Diagnóstico, no entra al pronóstico.

## Fuentes
| Fuente | Vía | Uso |
|---|---|---|
| Wikipedia | API MediaWiki | Encuestas |
| 270toWin | Página HTML | Encuestas |
| Base verificada | Excel (hoja «Histórico encuestas» de `TEXAS_GOBERNADOR.xlsx`) o `data/encuestas_verificadas_tx.csv` | Encuestas |
| Kalshi y Polymarket | APIs públicas | Mezcla (peso 0.30) y rangos de margen (escenario) |
| civicAPI | `early-vote/TX/{returned,inperson}` (por condado, sin partido) | Diagnóstico del voto ya emitido |
| FiveThirtyEight raw-polls | GitHub | Calibración |
| Correcciones de n | `data/correcciones_tamano_muestra.csv` | Tamaños verificados; n faltante = 600 marcado en `n_imputado` (hoy: Marist 8–11 oct LV, «TBA») |

## Uso
```
python -m tx_pronostico correr             # fuentes en vivo
python -m tx_pronostico correr --offline   # solo cachés
python -m tx_pronostico verificar          # revisa cada fuente
python -m pytest -q                        # pruebas sin red (respuestas reales del 25-oct-2026)
```
En Windows: `scripts\instalar.bat` y luego `scripts\correr_pronostico.bat`.
