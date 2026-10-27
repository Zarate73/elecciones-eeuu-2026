# Ohio 2026 · Modelo general (paquete `oh_pronostico`)

Paquete de Python del modelo de Ohio: Amy Acton (D), exdirectora de Salud del estado, contra Vivek Ramaswamy (R), por la gubernatura que deja Mike DeWine (R). En la boleta también está Don Kissick (Libertario). Gana la mayoría simple. Usa la misma estructura que las producciones de Arizona, Florida, Nevada, Pennsylvania, Maine, Texas, Illinois y Nueva York.

**Todas las fuentes se consultan en vivo en cada corrida.** Si una falla, se usa su última copia y el reporte lo marca.

## Modelo (elegido por backtest, ver `../docs/01_investigacion_y_modelo.md`)
- **Promedio:** V11 de Georgia.
  - Efectos de casa contraídos (k = 8), √n, vida media de 14 días; cada firma pesa ~1.
  - Ventana de 21 días; si hay menos de 2 encuestadoras, se toman los 21 días previos a la encuesta más reciente.
  - **Hoy entran seis encuestadoras:** RedBox (D) 20–23 oct, Verasight 1–20 oct, Beacon/Shaw 15–19 oct, ActiVote 27 sep–19 oct, Marist 15–18 oct y GS Strategy/New River 9–13 oct.
- **Identidad de una encuesta = firma + periodo de campo** (`identidad.py`, común a los paquetes). La fecha puntual de 270toWin es de publicación: Marist aparece el 20-oct; el campo fue del 15 al 18.
- **Alias:**
  - el «Siena College» de 270toWin = NYT/Siena;
  - CNN/SSRS = SSRS;
  - Fox News = Beacon/Shaw;
  - «New River / GSG» = GS Strategy Group/New River;
  - BGSU/YouGov con tres nombres;
  - Marist University = Marist College.
- **Cifras y n de la publicación original:**
  - Marist LV 50–43 (Wikipedia: 51–43), n = 883;
  - ActiVote 48.6–51.4 (Wikipedia y 270toWin redondean a 49–51).
- **Sesgo estatal:** contraído por Bayes empírico con todas las contiendas del estado (`sesgo_regla = "todas"`).
  - Hoy **resta 4.04 pp** a Acton: en Ohio las encuestas sobreestimaron al demócrata en 16 de 24 contiendas, y en todas desde 2014 (+2.9 a +8.1 pp).
  - En el backtest el sesgo mejora con claridad: LOYO 2.066 frente a 2.478; cronológico 1.802 frente a 2.464 (P = 0.002).
  - «Sin sesgo», «k ≥ 2», «solo gobernador» y «sin cada contienda» quedan como escenarios.
- **Terceros (Kissick y votos por escrito):** `real = a + c·(otros en las encuestas que los reportan)`, la regla T4. Es la mejor en Ohio y a nivel nacional.
- **Indecisos:** 50/50.
- **σ:** `√(τ² + s²/k + 0.25²·d)`, t de Student; d = días que las encuestas son más viejas que el horizonte calibrado. La deriva es un paseo aleatorio: la varianza crece linealmente con d y la desviación estándar adicional con √d (0.25 pp por √día; con 3 días, +0.43 pp en cuadratura), no 0.25 pp por día. El escenario «deriva al doble» usa σ_d = 0.50 (cuatro veces la varianza de la deriva).
- **Mercados:** Kalshi `GOVPARTYOH-26` y Polymarket `ohio-governor-winner-2026`, promediados, en mezcla logit con peso 0.30 (D / (D + R)). Hoy los mercados (~82 %) están muy por encima de las encuestas corregidas (41 %).
- **Recuento:** automático si el margen es ≤ 0.25 % de los votos; se reporta P(|margen| ≤ 0.25).
- **Voto anticipado (civicAPI):** Ohio no tiene registro partidario, así que solo hay volumen por condado (correo y en persona). Es diagnóstico: no entra al pronóstico.

## Reconstruir un corte pasado (revisión OH-05)
`python -m oh_pronostico correr --corte 2026-10-21` con un corte anterior a hoy es una **reconstrucción**: las fuentes se descargan hoy y traen información posterior al corte. Por eso:
- **Encuestas:** solo entran las ya **publicadas** al corte.
  - La fecha de publicación sale de 270toWin, que fecha por publicación, o de la columna `publicacion` del archivo complementario.
  - Sin fecha conocida se usa cierre de campo + `retraso_publicacion_dias` (3).
  - Nunca entra una encuesta con campo posterior al corte, aunque la fuente la traiga.
  - Cada encuesta lleva `publicacion`, `tipo_fecha` y `disponible_desde`. Las excluidas quedan en `reporte.json` (`reconstruccion.no_disponibles_al_corte`) y en los avisos.
- **Mercados:** precio al cierre del día del corte, con la vela diaria de Kalshi y el historial de Polymarket, para el ganador y para cada rango de margen. No se escribe en la caché de consultas en vivo.
- **Voto anticipado:** solo snapshots guardados con fecha ≤ corte; sin ellos, «no aplica» (diagnóstico).
- **Marcas:** el resumen dice «RECONSTRUCCIÓN» y el historial marca la fila con `reconstruccion = True`.

La corrida diaria (corte = hoy) no cambia: todo lo que trae una fuente en vivo ya está publicado.

## Fuentes
| Fuente | Vía | Uso |
|---|---|---|
| Wikipedia | API MediaWiki | Encuestas |
| 270toWin | Página HTML | Encuestas |
| Base verificada | Excel (hoja «Histórico encuestas» de `OHIO_GOBERNADOR-v1.xlsx`) o `data/encuestas_verificadas_oh.csv` | Encuestas |
| Kalshi y Polymarket | APIs públicas | Mezcla (peso 0.30) y rangos de margen (escenario) |
| civicAPI | `early-vote/OH/{returned,requested,inperson}` (88 condados, sin partido) | Diagnóstico del voto ya emitido |
| FiveThirtyEight raw-polls | GitHub | Calibración |
| Encuestas complementarias | `data/encuestas_complementarias_oh.csv` (con URL de la fuente) | Encuestas que faltan en las fuentes web y en el Excel (hoy vacío) |
| Correcciones de cifras | `data/correcciones_cifras.csv` | D, R y opcionalmente otros/indecisos de la publicación original (hoy: Marist LV y ActiVote) |
| Correcciones de n | `data/correcciones_tamano_muestra.csv` | Tamaños verificados (hoy: Marist LV = 883); un n faltante se imputa en 600 y queda marcado en `n_imputado` (hoy: Wedgewood, solo en el Excel) |

## Uso
```
python -m oh_pronostico correr             # fuentes en vivo
python -m oh_pronostico correr --offline   # solo cachés
python -m oh_pronostico verificar          # revisa cada fuente
python -m pytest -q                        # pruebas sin red (respuestas reales del 26-oct-2026)
```
En Windows: `scripts\instalar.bat` y luego `scripts\correr_pronostico.bat`.
