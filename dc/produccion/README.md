# Washington D.C. 2026 · Alcaldía · Modelo general (paquete `dc_pronostico`)

Paquete de Python del pronóstico de la general de la alcaldía de D.C.: Janeese Lewis George (D), Rhonda Hamilton (I), Robert L. Gross (Statehood Green) y votos por escrito, con voto preferencial (RCV). Misma estructura que los demás paquetes de producción.

**Todas las fuentes se consultan en vivo en cada corrida.** Si una falla, se usa su última copia (y, para las 13 elecciones históricas, el respaldo versionado `data/historico_alcaldias_respaldo.csv`); el reporte lo marca.

## Modelo (elegido por backtest, ver `../docs/01_investigacion_y_modelo.md`)
- **Sin encuestas ni mercados de la general** (28-oct). El % de Lewis George en la primera ronda sale de las 13 generales de alcaldía 1974–2022: `logit(%D) = 1.424 − 0.911·opositor_fuerte`, predictiva t (gl 11).
- **Opositor fuerte** = concejal o alcalde, actual o anterior (`data/contexto_alcaldias.csv`, con el cargo de cada opositor). Si apareciera uno (p. ej., por escrito), cambiar `opositor_fuerte = true` en `config/dc.toml`.
- **Reparto** del voto no demócrata: Gross y votos por escrito con lognormales calibradas en resultados reales; Hamilton el resto.
- **RCV:** conteo de la Iniciativa 83 en cada simulación (`rcv.py`, el mismo conteo que `run_rcv` del modelo de la primaria).
- **Encuestas y mercados:** se buscan en cada corrida. Si aparecen, entran solos: encuestas por precisión en logit (sd 7 pp, indecisos proporcionales) y mercados en mezcla logit con peso 0.30.
- **Escenarios:** solo opositor débil (σ propia), nivel reciente 2018–2022, protesta moderada, opositor fuerte, % de la primaria como variable y transferencias desfavorables.

## Reconstruir un corte pasado
`python -m dc_pronostico correr --corte 2026-10-25`: solo entran encuestas ya publicadas al corte (cierre + 3 días). Los mercados se marcan `no_aplica` (no hubo).

## Fuentes
| Fuente | Vía | Uso |
|---|---|---|
| Wikipedia, «AAAA Washington, D.C., mayoral election» (13 páginas) | API MediaWiki (User-Agent identificado) | Resultados de las generales 1974–2022 y % del nominado en la primaria |
| Wikipedia, página 2026 | API MediaWiki | Boleta (aviso si cambia), encuestas de la general, % de la primaria |
| DCBOE | Página de estadísticas, luego PDF del último informe mensual | Registro por partido (contexto) |
| Kalshi | `/series?category=Elections` + series KXMAYORDC y similares | Mercado de la general, si aparece |
| Polymarket | `public-search` | Mercado de la general, si aparece (la primaria no cuenta) |
| Encuestas complementarias | `data/encuestas_complementarias_dc.csv` | Encuestas de la general que falten en Wikipedia (hoy vacío) |

## Uso
```
python -m dc_pronostico correr             # fuentes en vivo
python -m dc_pronostico correr --offline   # solo cachés
python -m dc_pronostico historico          # las 13 generales en vivo y el backtest LOYO
python -m dc_pronostico verificar          # revisa cada fuente
python -m pytest -q                        # pruebas sin red (respuestas reales del 28-oct-2026)
```
En Windows: `scripts\instalar.bat` y luego `scripts\correr_pronostico.bat`.
