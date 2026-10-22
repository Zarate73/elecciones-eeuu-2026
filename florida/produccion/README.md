# Florida 2026 · Producción (modelo general)

Versión de producción del modelo de `../modelo_general/` (notebook `FLORIDA_2026_MODELO_FINAL.ipynb`). Es un paquete de Python (`fl_pronostico`) con línea de comandos, configuración en un solo archivo, registros, pruebas y tarea programada de Windows. Comparte estructura con la producción de Arizona; la diferencia de modelo es que **Florida usa sesgo estatal** (el backtest lo respalda: CRPS de FL 2.200 con sesgo contraído contra 2.643 sin él).

**Todas las fuentes se consultan en vivo en cada corrida:** encuestas, mercados, voto ya emitido e histórico de calibración. Con las mismas encuestas y la misma semilla da exactamente los números del notebook (margen −8.31, P(Jolly) 5.0 % al 22-oct), y una prueba lo verifica.

## Instalación (una vez)
Requisito: Python 3.10 o superior, en Windows con internet.
1. Doble clic en `scripts\instalar.bat`. Crea `.venv`, instala dependencias, corre las pruebas sin red y prueba cada fuente en vivo.
2. Opcional: en `config\florida.toml` → `[rutas] encuestas_base` pon la ruta de tu Excel verificado (hoja «Gobernador Florida», `FLORIDA_GOBERNADOR-v2.xlsx`). Por defecto se usa `data\encuestas_verificadas_fl.csv`.

## En GitHub (automático)
El flujo [`.github/workflows/pronostico_florida.yml`](../../.github/workflows/pronostico_florida.yml) corre todos los días a las 06:41 y 18:41 hora del Este (10:41 y 22:41 UTC mientras rige el horario de verano; una hora antes desde el 1-nov). También se puede lanzar a mano desde **Actions → Pronóstico Florida → Run workflow**. En cada corrida:
1. corre las pruebas sin red;
2. ejecuta `python -m fl_pronostico correr` con todas las fuentes en vivo;
3. `scripts/actualizar_readme.py` reescribe el bloque de pronóstico de `florida/README.md` y la fila de Florida del README principal, y dibuja `salidas/evolucion.png`;
4. `scripts/exportar_tablero.py` actualiza los datos del tablero;
5. publica `salidas/ultimo/`, el historial y las cachés ligeras en un commit de `github-actions[bot]`.

## Uso diario (Windows)
| Acción | Comando |
|---|---|
| Correr el pronóstico | `scripts\correr_pronostico.bat` |
| Ver el último resultado | `scripts\abrir_ultimo.bat` |
| Ver qué encuestas usaría hoy (sin correr) | `scripts\ver_encuestas.bat` |
| Programar todos los días a las 08:00 | `powershell -ExecutionPolicy Bypass -File scripts\programar_tarea.ps1` |
| Varias veces al día | `... programar_tarea.ps1 -Horas 08:00,20:00` |
| Quitar la tarea | `... programar_tarea.ps1 -Eliminar` |
| Sin red (solo cachés) | `scripts\correr_pronostico.bat --offline` |
| Fallar si algo no está en vivo | `scripts\correr_pronostico.bat --estricto` |
| Revisar instalación y fuentes | `.venv\Scripts\python -m fl_pronostico verificar` |

Códigos de salida: `0` OK · `1` error fatal (sin encuestas o con encuestas inválidas) · `2` alguna fuente no estuvo en vivo (solo con `--estricto`).

## Fuentes (todas en vivo)
| Fuente | Vía | Si falla | Uso |
|---|---|---|---|
| **Wikipedia** | API MediaWiki `action=parse` → tabla de encuestas (se normalizan los `rowspan="2;"` de la página de FL) | caché | encuestas, fuente principal (trae n, población y terceros) |
| **270toWin** | página HTML | caché | encuestas que Wikipedia aún no tiene |
| Base verificada | Excel (hoja «Gobernador Florida») o `data\encuestas_verificadas_fl.csv` | se omite | encuestas revisadas a mano (se excluye la columna del promedio) |
| **Kalshi** `GOVPARTYFL-26` | API pública, punto medio bid/ask | último precio guardado (≤ 3 días) | mezcla (peso 0.30, promediado con Polymarket) |
| **Polymarket** `florida-governor-winner-2026` | API Gamma, punto medio bid/ask | último precio guardado (≤ 3 días) | mezcla (peso 0.30, promediado con Kalshi) |
| **Polymarket** por rangos de margen | API Gamma | caché | escenario (margen implícito) |
| **civicAPI** | `civicapi.org/api/v2/early-vote/FL/{returned,inperson,requested}` | último snapshot | diagnóstico: votos ya emitidos por partido registrado (D, R, NPA) y condado, separados en correo y en persona; no entra al pronóstico |
| **FiveThirtyEight raw-polls** | GitHub | caché → copia del paquete | calibración: τ, s, ν, efectos de casa, terceros y sesgo estatal |
| 2024 (FL Pres/Sen y 43 contiendas más, AZ, GA) | `data\` | — | calibración (histórico fijo) |

Si un mercado no tiene precio usable, sale de la mezcla. Si no hay ninguno, el pronóstico es solo de encuestas y el reporte lo indica. Si no hay **ninguna** encuesta (ni en vivo, ni en caché, ni en la base), la corrida termina con error 1.

### Cómo se arman las encuestas
1. **Una versión por encuesta.** Por firma y fecha se elige LV > RV > A, luego mayor muestra.
2. **Combinación de fuentes.** Prioridad Wikipedia > base verificada > 270toWin. Es la misma encuesta si es la misma firma (con los alias de `encuestas.ALIAS`) y su fecha de fin está a ±7 días, o si es la misma firma con las mismas cifras a ≤ 60 días (270toWin fecha por publicación). Ejemplos de Florida: Univision/YouGov = «YouGov» de 270toWin; «Mason-Dixon — NBC 6 / Telemundo» = Mason-Dixon.
3. **Firmas distintas nunca se fusionan** por coincidir en cifras.
4. **Filtro de fechas.** Solo encuestas posteriores a las primarias (18-ago) y no posteriores al corte.

### Sesgo estatal
Se recalcula en cada corrida con el histórico (vida media de 4 años, contracción por Bayes empírico): al 22-oct, bruto +5.42 pp pro-D, contraído +4.83 (contracción 0.89). El pronóstico resta el contraído al promedio de encuestas. Siempre se reportan los escenarios **sin sesgo estatal** (regla de Arizona) y **sesgo sin contraer**.

## Salidas (`salidas\ultimo\`)
`resumen.txt` · `reporte.json` · `pronostico_gobernador.csv` · `escenarios_gobernador.csv` · `encuestas_gobernador.csv` · `encuestas_ventana_pesos.csv` · `voto_anticipado_condados.csv` · `polymarket_rangos_margen.csv` · `pronostico.png`. Además: `salidas\historial_pronosticos.csv`, `salidas\civicapi_historial_fl.csv` (serie diaria propia del voto ya emitido) y `salidas\evolucion.png`.

## Pruebas
`python -m pytest -q` (19 pruebas, sin red, con respuestas reales del 22-oct-2026; una solo corre si la base es un Excel local). Cubren:
- los parsers, la deduplicación y el Excel;
- Kalshi, Polymarket y sus rangos;
- civicAPI de Florida (correo, en persona, NPA);
- el sesgo estatal y sus escenarios;
- caídas de fuentes, cachés viejas y modo offline;
- la equivalencia exacta con el notebook.
