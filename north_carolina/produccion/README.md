# North Carolina 2026 · Senado · Modelo general (paquete `nc_pronostico`)

Paquete de Python del modelo del Senado de North Carolina: Roy Cooper (D), exgobernador, contra Michael Whatley (R), expresidente del RNC, por el escaño abierto que deja Thom Tillis (R). En la boleta también están Shannon Bray (Libertario) y Michael Dublin (Verde). Gana la mayoría simple. Usa la misma estructura que las producciones de Ohio, Nueva York, Illinois, Texas, Maine, Pennsylvania, Nevada, Florida y Arizona. Es el **primer paquete de Senado**.

**Todas las fuentes se consultan en vivo en cada corrida.** Si una falla, se usa su última copia y el reporte lo marca.

## Modelo (elegido por backtest, ver `../docs/01_investigacion_y_modelo.md`)
- **¿Sirve el modelo de gobernador para el Senado?** Sí. El backtest probó cinco variantes propias del Senado en las 383 contiendas de Senado (1998–2024): σ calibrada solo con Senado, sesgo estatal solo con Senado, sesgo nacional del cargo, mezcla con fundamentales y escala del margen. Ninguna mejora a V11 + sesgo estatal (CRPS 3.347).
- **Promedio:** V11 de Georgia.
  - Efectos de casa contraídos (k = 8), √n, vida media de 14 días; cada firma pesa ~1.
  - Ventana de 21 días a la elección (desde el 13-oct); si hay menos de 2 encuestadoras, se toman los 21 días previos a la encuesta más reciente.
  - **Hoy entran tres encuestadoras:** Quantus Insights (R) 24–25 oct, Harper Polling (R) 18–20 oct y ActiVote 8–20 oct. SurveyUSA (7–11 oct), Trafalgar (8–10 oct) y Elon/YouGov (29 sep–8 oct) quedan fuera por pocos días; el escenario «Ventana 45 días» las incluye.
- **Identidad de una encuesta = firma + periodo de campo** (`identidad.py`, común a los paquetes).
- **Alias:** «Harper Polling (R) — Carolina Journal» (Excel) = Harper Polling; «The Trafalgar Group» = Trafalgar Group; AARP = Fabrizio/Impact; Fox News = Beacon/Shaw.
- **Encuestas aisladas** (`data/encuestas_excluidas.csv`), para no contarlas dos veces:
  - el «YouGov» del 20-oct de 270toWin (560 LV, 54–43) es la encuesta Elon/YouGov 29 sep–8 oct (561 LV, 52–39);
  - el Catawba del 30-sep (270toWin y Excel, fecha de publicación) es la Catawba/YouGov 4–15 sep, publicada 15 días después del cierre (la tolerancia de `identidad.py` es 14).
- **Sesgo estatal:** contraído por Bayes empírico con todas las contiendas del estado (`sesgo_regla = "todas"`).
  - Hoy **resta 2.10 pp** a Cooper: en NC las encuestas sobreestimaron al demócrata en 16 de 23 contiendas y en las 10 desde 2014 (Senado 2014 +1.7, 2016 +4.6, 2020 +5.2, 2022 +1.1).
  - Cronológico, Senado nacional: 3.236 con sesgo frente a 3.474 sin sesgo (P = 0.012).
  - «Sin sesgo», «k ≥ 2», «solo Senado» (−1.72) y «sin cada contienda» quedan como escenarios.
- **Terceros (Bray, Dublin y votos por escrito):** `real = a + c·(otros en las encuestas que los reportan)`, la regla T4. Van en bloque: no hay «tercero principal», porque el registro de un partido en NC depende del voto a gobernador o presidente, no al Senado.
- **Indecisos:** 50/50.
- **σ:** `√(τ² + s²/k + 0.25²·d)`, t de Student. Con k = 3, el término s²/k pesa: σ = 5.7 pp.
- **Mercados:** Kalshi `SENATENC-26` y Polymarket `north-carolina-senate-election-winner`, promediados, en mezcla logit con peso 0.30 (D / (D + R)). Hoy ~97 %, por encima de las encuestas corregidas (93.5 %).
- **Recuento:** a petición si la diferencia es ≤ 0.5 % o ≤ 10,000 votos, lo que sea menor (G.S. 163-182.7): con ~3.8 millones de votos manda el tope de 10,000 ≈ 0.26 pp. Se reporta P(|margen| ≤ 0.26).
- **Voto anticipado (civicAPI):** NC tiene registro partidario, así que hay desglose por partido y condado (100). Es diagnóstico: el registro no es intención de voto (un tercio es sin afiliación) y no entra al pronóstico.

## Reconstruir un corte pasado
`python -m nc_pronostico correr --corte 2026-10-22` con un corte anterior a hoy es una **reconstrucción** (regla de la revisión OH-05 de Ohio): solo entran encuestas ya publicadas al corte (fecha de 270toWin, columna `publicacion` del archivo complementario o cierre de campo + 3 días), los mercados se toman al cierre del día del corte y el voto anticipado solo de snapshots ≤ corte. La corrida diaria (corte = hoy) no cambia.

## Fuentes
| Fuente | Vía | Uso |
|---|---|---|
| Wikipedia | API MediaWiki | Encuestas |
| 270toWin | Página HTML | Encuestas |
| Base verificada | Excel (hoja «Histórico encuestas» de `NORTH_CAROLINA_SENADO.xlsx`) o `data/encuestas_verificadas_nc.csv` | Encuestas |
| Kalshi y Polymarket | APIs públicas | Mezcla (peso 0.30) y rangos de margen (escenario) |
| civicAPI | `early-vote/NC/{returned,requested,inperson}` (100 condados, por partido) | Diagnóstico del voto ya emitido |
| FiveThirtyEight raw-polls | GitHub | Calibración |
| Encuestas complementarias | `data/encuestas_complementarias_nc.csv` | Encuestas que faltan en las fuentes web y en el Excel (hoy vacío) |
| Encuestas aisladas | `data/encuestas_excluidas.csv` | Filas de una fuente que repiten otra encuesta con otro nombre o fecha |
| Correcciones | `data/correcciones_cifras.csv`, `data/correcciones_tamano_muestra.csv` | Cifras y n de la publicación original (hoy vacías) |

## Uso
```
python -m nc_pronostico correr             # fuentes en vivo
python -m nc_pronostico correr --offline   # solo cachés
python -m nc_pronostico verificar          # revisa cada fuente
python -m pytest -q                        # pruebas sin red (respuestas reales del 27-oct-2026)
```
En Windows: `scripts\instalar.bat` y luego `scripts\correr_pronostico.bat`.
