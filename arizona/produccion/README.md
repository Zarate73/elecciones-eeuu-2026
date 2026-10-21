# Arizona 2026 · Producción (modelo general)

Versión de producción del modelo de `../modelo_general/` (notebook `ARIZONA_2026_MODELO_FINAL.ipynb`). Es un paquete de Python con línea de comandos, configuración en un solo archivo, registros, pruebas y tarea programada de Windows.

**Todas las fuentes se consultan en vivo en cada corrida:** encuestas, mercados, voto anticipado e histórico de calibración. Con las mismas encuestas y la misma semilla da exactamente los números del notebook, y una prueba lo verifica.

## Instalación (una vez)
Requisito: Python 3.10 o superior, en Windows con internet.
1. Doble clic en `scripts\instalar.bat`. Crea `.venv`, instala dependencias, corre las pruebas sin red y prueba cada fuente en vivo.
2. Opcional: en `config\arizona.toml` → `[rutas] encuestas_base` pon la ruta de tu Excel verificado (hoja «Gobernador Arizona»). Por defecto se usa `data\encuestas_verificadas_az.csv`.

## En GitHub (automático)
El flujo [`.github/workflows/pronostico_arizona.yml`](../../.github/workflows/pronostico_arizona.yml) corre todos los días a las 05:27 y 17:27 hora de Arizona (12:27 y 00:27 UTC). También se puede lanzar a mano desde **Actions → Pronóstico Arizona → Run workflow**. En cada corrida:
1. corre las pruebas sin red;
2. ejecuta `python -m az_pronostico correr` con todas las fuentes en vivo;
3. `scripts/actualizar_readme.py` reescribe el bloque de pronóstico de `arizona/README.md` y la fila de Arizona del README principal, y dibuja `salidas/evolucion.png`;
4. publica `salidas/ultimo/`, el historial y las cachés ligeras en un commit de `github-actions[bot]`.

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
| Revisar instalación y fuentes | `.venv\Scripts\python -m az_pronostico verificar` |

Códigos de salida: `0` OK · `1` error fatal (sin encuestas o con encuestas inválidas) · `2` alguna fuente no estuvo en vivo (solo con `--estricto`).

## Fuentes (todas en vivo)
| Fuente | Vía | Si falla | Uso |
|---|---|---|---|
| **Wikipedia** | API MediaWiki `action=parse` → tabla de encuestas | caché | encuestas, fuente principal (trae n, población y terceros) |
| **270toWin** | página HTML | caché | encuestas que Wikipedia aún no tiene |
| Base verificada | Excel (hoja «Gobernador Arizona») o `data\encuestas_verificadas_az.csv` | se omite | encuestas revisadas a mano |
| **Kalshi** `GOVPARTYAZ-26` | API pública, punto medio bid/ask | último precio guardado (≤ 3 días) | mezcla (peso 0.30, promediado con Polymarket) |
| **Polymarket** `arizona-governor-winner-2026` | API Gamma, punto medio bid/ask | último precio guardado (≤ 3 días) | mezcla (peso 0.30, promediado con Kalshi) |
| **Polymarket** por rangos de margen | API Gamma | caché | escenario (margen implícito) |
| **civicAPI** | `civicapi.org/api/v2/early-vote/AZ/{returned,requested}` | último snapshot | diagnóstico: boletas por partido y condado; no entra al pronóstico |
| **FiveThirtyEight raw-polls** | GitHub | caché → copia del paquete | calibración: τ, s, ν, efectos de casa, terceros |
| AZ 2024 y GA Pres 2024 | `data\` | — | calibración (histórico fijo) |

Si un mercado no tiene precio usable, sale de la mezcla. Si no hay ninguno, el pronóstico es solo de encuestas y el reporte lo indica. Si no hay **ninguna** encuesta (ni en vivo, ni en caché, ni en la base), la corrida termina con error 1.

### Cómo se arman las encuestas
1. **Una versión por encuesta.** Por firma y fecha se elige LV > RV > A, luego mayor muestra.
2. **Combinación de fuentes.** Prioridad Wikipedia > base verificada > 270toWin. Es la misma encuesta si es la misma firma (con los alias de `encuestas.ALIAS`) y su fecha de fin está a ±7 días, o si es la misma firma con las mismas cifras a ≤ 60 días (270toWin fecha por publicación).
3. **Firmas distintas nunca se fusionan** por coincidir en cifras: GQR y GrayHouse publicaron ambas 49/45 con n = 600.
4. **Filtro de fechas.** Solo encuestas posteriores a la primaria (21-jul) y no posteriores al corte.

## Salidas (`salidas\ultimo\`)
`resumen.txt` · `reporte.json` · `pronostico_gobernador.csv` · `escenarios_gobernador.csv` · `encuestas_gobernador.csv` · `encuestas_ventana_pesos.csv` · `voto_anticipado_condados.csv` · `polymarket_rangos_margen.csv` · `pronostico.png`. Además: `salidas\historial_pronosticos.csv`, `salidas\civicapi_historial_az.csv` (serie diaria propia del voto anticipado) y `salidas\evolucion.png`.

## Pruebas
`python -m pytest -q` (14 pruebas, sin red, con respuestas reales del 21-oct-2026). Cubren:
- los parsers y la deduplicación;
- Kalshi, Polymarket y sus rangos;
- civicAPI;
- caídas de fuentes, cachés viejas y modo offline;
- la equivalencia exacta con el notebook.
