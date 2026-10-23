# Pennsylvania 2026 · Modelo general (paquete `pa_pronostico`)

Paquete de Python del modelo de Pennsylvania: Josh Shapiro (D, gobernador) contra Stacy Garrity (R, tesorera estatal), con Ken Krawchuk (L) y otros como terceros. Usa la misma estructura que las producciones de Arizona, Florida y Nevada: línea de comandos, configuración en `config/pennsylvania.toml`, registros, pruebas sin red y tarea programada de Windows.

**Todas las fuentes se consultan en vivo en cada corrida.** Si una falla, se usa su última copia y el reporte lo marca.

## Modelo (elegido por backtest, ver `../docs/01_investigacion_y_modelo.md`)
- **Promedio:** V11 de Georgia: efectos de casa contraídos (k = 8), √n, vida media de 14 días y cada firma pesa ~1. La ventana es de 21 días; si hay menos de 2 encuestadoras, se toman los 21 días previos a la encuesta más reciente. Si una encuesta trae versión LV y RV, se usa la LV.
- **Sesgo estatal:** contraído por Bayes empírico (hoy 1.05 pp pro-D, que se restan). Es la regla nacional; en PA quitarlo no es ni mejor ni peor (P = 0.52).
- **Terceros:** `real = a + c·otros`, con «otros» promediado solo entre las encuestas que los reportan; si ninguna los reporta, se usa la media histórica.
- **Indecisos:** 50/50 (el reparto proporcional es el peor en PA y a nivel nacional).
- **Sin ajuste por paliza:** en contiendas con ventaja ≥ 15 pp la escala estimada del margen es 0.99.
- **σ:** `√(τ² + s²/k)`, t de Student, con una deriva de 0.25 pp/día cuando las encuestas son más viejas que el horizonte.
- **Mercados:** Kalshi `GOVPARTYPA-26` y Polymarket `pennsylvania-governor-winner-2026`, promediados, en mezcla logit con peso 0.30. La distribución se desplaza para que P(margen > 0) sea la probabilidad publicada.
- **Escenarios:** cruce 2 × 2 de sesgo × mercados, influencia de cada encuesta, terceros, peso de mercados y sensibilidad. Cada escenario trae su probabilidad con y sin mercados.

## Fuentes
| Fuente | Vía | Uso |
|---|---|---|
| Wikipedia | API MediaWiki | Encuestas |
| 270toWin | Página HTML | Encuestas |
| Base verificada | Excel «Gobernador Pennsylvania» o `data/encuestas_verificadas_pa.csv` | Encuestas |
| Kalshi y Polymarket | APIs públicas | Mezcla (peso 0.30) y rangos de margen (escenario: partición completa con «Republican wins», normal ajustada y E[M \| D]) |
| civicAPI | `early-vote/PA/{returned,requested}` (PA no tiene voto anticipado en persona) | Diagnóstico de las boletas por correo |
| FiveThirtyEight raw-polls | GitHub | Calibración |
| Correcciones de n | `data/correcciones_tamano_muestra.csv` | Tamaños verificados por versión LV/RV (p. ej. F&M oct: 433 LV); sin corrección, n faltante = 600 marcado en `n_imputado` |

## Uso
```
python -m pa_pronostico correr             # fuentes en vivo
python -m pa_pronostico correr --offline   # solo cachés
python -m pa_pronostico verificar          # revisa cada fuente
python -m pytest -q                        # 18 pruebas sin red (respuestas reales del 23-oct-2026)
```
En Windows: `scripts\instalar.bat` y luego `scripts\correr_pronostico.bat`.
