# Nevada 2026 · Modelo general (paquete `nv_pronostico`)

Paquete de Python del modelo de Nevada: Aaron Ford (D) contra Joe Lombardo (R), con Danielle Ford (I) y «None of these candidates» en la boleta. Usa la misma estructura que las producciones de Arizona y Florida: línea de comandos, configuración en `config/nevada.toml`, registros, pruebas sin red y tarea programada de Windows.

**Todas las fuentes se consultan en vivo en cada corrida.** Si una falla, se usa su última copia y el reporte lo marca.

## Modelo (elegido por backtest, ver `../docs/01_investigacion_y_modelo.md`)
- **Promedio:** V11 de Georgia: efectos de casa contraídos (k = 8), √n, vida media de 14 días y cada firma pesa ~1. La ventana es de 21 días; si hay menos de 2 encuestadoras, se toman los 21 días previos a la encuesta más reciente.
- **Sesgo estatal:** contraído por Bayes empírico (hoy +0.58 pp pro-D). Es la regla nacional; en NV quitarlo no es ni mejor ni peor.
- **Terceros:** `real = a + c·otros`, con «otros» promediado solo entre las encuestas que los reportan; si ninguna los reporta, se usa la media histórica. Incluyen a Danielle Ford y «None of these candidates».
- **Indecisos:** 50/50.
- **σ:** `√(τ² + s²/k)`, t de Student, con una deriva de 0.25 pp/día cuando las encuestas son más viejas que el horizonte.
- **Mercados:** Kalshi `GOVPARTYNV-26` y Polymarket `nevada-governor-winner-2026`, promediados, en mezcla logit con peso 0.30. La distribución se desplaza para que P(margen > 0) sea la probabilidad publicada.
- **Escenarios:** cruce 2 × 2 de sesgo × mercados, y sensibilidad. Cada escenario trae su probabilidad con y sin mercados.

## Fuentes
| Fuente | Vía | Uso |
|---|---|---|
| Wikipedia | API MediaWiki (la columna del demócrata se busca como «Aaron Ford») | Encuestas |
| 270toWin | Página HTML | Encuestas |
| Base verificada | Excel «Gobernador Nevada» o `data/encuestas_verificadas_nv.csv` | Encuestas |
| Kalshi y Polymarket | APIs públicas | Mezcla (peso 0.30) y rangos de margen (escenario) |
| civicAPI | `early-vote/NV/{returned,inperson,requested}` | Diagnóstico del voto ya emitido (los no partidistas van en «Otros») |
| FiveThirtyEight raw-polls | GitHub | Calibración |

## Uso
```
python -m nv_pronostico correr             # fuentes en vivo
python -m nv_pronostico correr --offline   # solo cachés
python -m nv_pronostico verificar          # revisa cada fuente
python -m pytest -q                        # 16 pruebas sin red (respuestas reales del 22-oct-2026)
```
En Windows: `scripts\instalar.bat` y luego `scripts\correr_pronostico.bat`.
