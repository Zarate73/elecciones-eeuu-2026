# Resultados preliminares vs pronóstico final

Seguimiento de la noche electoral (3-nov-2026) y de los días de escrutinio: se descargan los conteos preliminares de cada una de las 14 contiendas y se comparan con el **pronóstico final** de cada estado. El resultado se publica en el tablero (panel «Noche electoral») y en [`salidas/`](salidas/).

## Pronóstico final (congelado)
- **Último pronóstico:** los flujos de pronóstico dejan de correr el **3-nov a las 10:00 ET** ([`scripts/ventana_pronostico.py`](../scripts/ventana_pronostico.py)). La última corrida es la de la mañana del día de la elección, antes de que se cuente un solo voto.
- **Congelado:** la primera corrida de este flujo después de ese corte copia el `tablero/datos/<estado>.json` de cada estado a [`pronosticos_finales/`](pronosticos_finales/). Contra esa copia se mide el error, aunque después cambie el tablero.
- **Congelados de prueba:** si alguno se hizo antes del corte, se rehace solo.

## Fuentes (en orden de prioridad por estado; ver [`config/carreras.toml`](config/carreras.toml))
| Estado | Fuente oficial | Avance que reporta |
|---|---|---|
| North Carolina | NCSBE `er.ncsbe.gov/enr/20261103/data/results_0.txt` (ya publicado en cero) | precintos |
| Florida | Florida DOS `…/20261103_ElecResultsFL.txt` (ya publicado en cero) | precintos |
| California | `api.sos.ca.gov/returns/governor` (ya publicado en cero) | precintos |
| Pennsylvania | `electionreturns.pa.gov` API (elección 2026 activa, en cero) | distritos |
| Georgia | `results.sos.ga.gov` (Enhanced Voting): la elección del 3-nov aparece en su lista ese día | precintos |
| Texas | `results.texas-election.com` (la general 2026 se descubre cuando la publiquen) | precintos |
| Washington D.C. | DCBOE `cityWide/getCityWide/2026-General-Election` (1.ª ronda RCV) | — |
| Arizona, Nevada, Maine, Illinois, Nueva York, Ohio, Wisconsin | Wikipedia (respaldo común; AZ bloquea las IP de GitHub, y los demás no tienen un conteo estatal en vivo que se pueda leer) | — |

- **Manual:** `data/manuales.csv` (columnas `clave, hora_utc, votos_D, votos_R, votos_otros, avance, fuente, url`) va por encima de todo. Sirve para anotar cifras de AP u otro medio en los estados sin fuente oficial legible.
- **El avance cuenta precintos, no votos.** Con el 100 % de los precintos todavía faltan votos por correo y provisionales (muchos en CA, AZ y NV), así que el error es **provisional** hasta el escrutinio.

## Métricas
- **Error del margen:** conteo − pronóstico, en pp. Si es mayor que 0, el demócrata va mejor de lo pronosticado.
- **Percentil:** dónde cae el conteo dentro de la distribución pronosticada (t con la media, la sd y los grados de libertad publicados).
- **Intervalos:** si el conteo cae dentro del IC80 y del IC95.
- **Líder:** si el que va adelante es el favorito del pronóstico.
- **Brier:** sobre P(D).
- **CRPS:** de la t, en forma cerrada.
- **Agregados:** para todos los estados con conteo y para los casi completos (≥ 95 % de precintos).

## Calendario ([flujo](../.github/workflows/resultados.yml))
- Cada 15 minutos del 3-nov 18:00 ET al 5-nov 07:00 ET.
- Cada hora hasta el 10-nov.
- Una vez al día hasta el 30-nov.
- También se puede correr a mano.

```
python -m res_eeuu          # desde resultados/: consulta, compara y escribe salidas/ y tablero/datos/resultados.json
python -m pytest -q         # pruebas sin red con los formatos reales de cada fuente
```
