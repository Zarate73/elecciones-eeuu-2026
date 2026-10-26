# Nueva York 2026 · Modelo general (paquete `ny_pronostico`)

Paquete de Python del modelo de Nueva York: la gobernadora Kathy Hochul (D, también en la línea del Working Families Party) contra Bruce Blakeman (R, también en la línea Conservadora), ejecutivo del condado de Nassau. **No hay terceros en la boleta**: la Junta Electoral rechazó todas las peticiones de partidos no calificados. Usa la misma estructura que las producciones de Arizona, Florida, Nevada, Pennsylvania, Maine, Texas e Illinois.

**Todas las fuentes se consultan en vivo en cada corrida.** Si una falla, se usa su última copia y el reporte lo marca.

## Modelo (elegido por backtest, ver `../docs/01_investigacion_y_modelo.md`)
- **Promedio:** V11 de Georgia: efectos de casa contraídos (k = 8), √n, vida media de 14 días y cada firma pesa ~1. La ventana es de 21 días; si hay menos de 2 encuestadoras, se toman los 21 días previos a la encuesta más reciente. **Hoy entran Quinnipiac (15–19 oct), OnMessage (R) (12–14 oct) y ActiVote (1–23 oct)**. Las encuestas del 1 al 12 de octubre (Marist, Emerson, OnMessage 1–6 oct, Beacon, Pollfinity) quedan fuera por pocos días; los escenarios «ventana de 45 días» y «fechas por el punto medio del campo» las incluyen.
- **Identidad de una encuesta = firma + periodo de campo.** La fecha puntual de 270toWin es de publicación (Quinnipiac aparece el 21-oct; el campo fue 15–19 oct).
- **Alias:** Siena College Research Institute **no** se unifica con NYT/Siena: tiene su propio historial en FiveThirtyEight (62 encuestas, casi todas de NY). Marist University = Marist College.
- **Encuestas complementarias** (`data/encuestas_complementarias_ny.csv`, revisión del 26-oct): verificadas en la publicación original y ausentes de Wikipedia, 270toWin y el Excel: OnMessage (R) 12–14 oct (50.3–45.9, pagada por la campaña de Komatireddy) y Pollfinity 8–12 oct (47–44, RV). Sus fechas mandan: dos periodos distintos de la misma firma no se funden aunque coincidan cifras y n.
- **Cifras con decimales del Excel verificado:** si Wikipedia/270toWin redondean (Emerson 52–40, McLaughlin 50–46) y el Excel trae decimales compatibles (52.4–39.7, 49.6–45.7), se usan los del Excel.
- **Sesgo estatal:** contraído por Bayes empírico con todas las contiendas del estado (`sesgo_regla = "todas"`). Hoy **resta** 1.95 pp a Hochul: desde 2020 las encuestas en NY sobreestimaron al demócrata (+9.5 en 2020, +4.3 en 2024). Es el estado donde el sesgo más ayuda en el backtest. «Sin sesgo», «k ≥ 2», «solo gobernador» y «sin cada contienda» quedan como escenarios.
- **Terceros:** solo dos candidatos en la boleta → votos por escrito fijos (`terceros_fijos = [0.15, 0.05]`, como el 0.16 % de 2022). El «otro» de las encuestas se reparte como los indecisos.
- **Indecisos:** 50/50.
- **σ:** `√(τ² + s²/k)`, t de Student, con una deriva de 0.25 pp/día cuando las encuestas son más viejas que el horizonte.
- **Mercados:** Kalshi `GOVPARTYNY-26` y Polymarket `new-york-governor-winner-2026`, promediados, en mezcla logit con peso 0.30 (D / (D + R)).
- **Recuento:** automático si el margen es ≤ 0.5 pp (o ≤ 20 votos): se reporta P(|margen| ≤ 0.5).
- **Voto anticipado:** civicAPI no publica Nueva York (404). Se consulta en vivo por si empieza a hacerlo, pero es diagnóstico opcional: no cuenta como fuente degradada.
  Mientras tanto se leen los check-ins de la Junta Electoral de NYC (vote.nyc): acumulado por condado y por día, solo la ciudad, solo en persona y sin partido. Es diagnóstico (no entra al pronóstico); si la página no responde se usa la caché y la fuente `nyc_boe` cuenta como degradada. Salidas: `salidas/ultimo/voto_anticipado_condados.csv` y `salidas/nyc_voto_anticipado_historial.csv`.

## Fuentes
| Fuente | Vía | Uso |
|---|---|---|
| Wikipedia | API MediaWiki | Encuestas |
| 270toWin | Página HTML | Encuestas |
| Base verificada | Excel (hoja «Histórico encuestas» de `NUEVA_YORK_GOBERNADOR-v1.xlsx`) o `data/encuestas_verificadas_ny.csv` | Encuestas |
| Kalshi y Polymarket | APIs públicas | Mezcla (peso 0.30) y rangos de margen (escenario) |
| civicAPI | `early-vote/NY/...` (hoy 404) | Diagnóstico opcional del voto ya emitido |
| Junta Electoral de NYC | `vote.nyc/page/early-voting-check-ins` | Check-ins de voto anticipado en persona por condado (diagnóstico) |
| FiveThirtyEight raw-polls | GitHub | Calibración |
| Encuestas complementarias | `data/encuestas_complementarias_ny.csv` (con URL de la fuente) | Encuestas que faltan en las fuentes web y en el Excel |
| Correcciones de cifras | `data/correcciones_cifras.csv` | D, R y opcionalmente otros/indecisos de la publicación original (hoy: Quinnipiac, «no sabe» + «rechazó» en lugar de terceros) |
| Correcciones de n | `data/correcciones_tamano_muestra.csv` | Tamaños verificados; n faltante = 600 marcado en `n_imputado` (hoy vacío) |

## Uso
```
python -m ny_pronostico correr             # fuentes en vivo
python -m ny_pronostico correr --offline   # solo cachés
python -m ny_pronostico verificar          # revisa cada fuente
python -m pytest -q                        # pruebas sin red (respuestas reales del 25-oct-2026)
```
En Windows: `scripts\instalar.bat` y luego `scripts\correr_pronostico.bat`.
