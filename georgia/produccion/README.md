# ODISEO · Georgia 2026 · Producción (modelo V11)

Versión de producción de `ODISEO_Georgia_2026_Modelo_Final_v11`. Es un paquete de Python con línea de comandos, configuración en un solo archivo, registros, pruebas y tarea programada de Windows.

**Todas las fuentes se consultan en vivo en cada corrida.** No hay que mantener a mano ningún CSV de encuestas. Con las mismas encuestas da los mismos números que el notebook V11, y una prueba lo verifica.

## Instalación (una vez)
Requisito: Python 3.10 o superior, en Windows con internet.
1. Doble clic en `scripts\instalar.bat`. Crea `.venv`, instala dependencias, corre las pruebas sin red y prueba cada fuente en vivo.
2. Opcional: en `config\georgia.toml` → `[rutas] encuestas_propias` pon la ruta local de tus Excel G-Ratings (separados por `;`). Sin Excel, sus resultados se toman de `data\ajustes_encuestas.csv`.

## En GitHub (automático)
El flujo [`.github/workflows/pronostico_georgia.yml`](../../.github/workflows/pronostico_georgia.yml) corre todos los días a las 08:07 y 20:07 hora de Georgia. También se puede lanzar a mano desde la pestaña **Actions → Pronóstico Georgia → Run workflow**. En cada corrida:
1. instala dependencias y corre las pruebas sin red;
2. ejecuta `python -m ga_pronostico correr` con todas las fuentes en vivo;
3. `scripts/actualizar_readme.py` reescribe el bloque de pronóstico de `georgia/README.md` y la fila de Georgia del README principal, y dibuja `salidas/evolucion.png`;
4. publica `salidas/ultimo/`, `salidas/historial_pronosticos.csv` y las cachés ligeras en un commit de `github-actions[bot]`.

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
| Revisar instalación y fuentes | `.venv\Scripts\python -m ga_pronostico verificar` |

Códigos de salida: `0` OK · `1` error fatal (sin encuestas o con encuestas inválidas) · `2` alguna fuente no estuvo en vivo (solo con `--estricto`).

## Fuentes (todas en vivo)
| Fuente | Vía | Si falla | Uso |
|---|---|---|---|
| **Wikipedia** (Gobernador y Senado) | API MediaWiki `action=parse` → tabla de encuestas | caché | encuestas, fuente principal |
| **270toWin** (Gobernador y Senado) | página HTML | caché | encuestas que Wikipedia aún no tiene |
| **Encuestas propias G-Ratings** | Excel (hojas METHODOLOGY + estado) | se omiten | encuestas |
| **Kalshi** `GOVPARTYGA-26` | API pública | último snapshot (≤ 3 días) | mezcla de probabilidad (peso 0.30) |
| **Civic Forge** | API pública: raza y edad del voto anticipado contra el mismo día de 2018–2024 | caché | diagnóstico; no entra al pronóstico |
| **FiveThirtyEight raw-polls** | GitHub | caché → copia del paquete | calibración: τ, s, ν, efectos de casa, sesgo GA |
| GA Presidente 2024 | `data\ga_pres2024_polls.csv` | — | calibración (histórico fijo) |

Cada fuente tiene caché en `salidas\cache\`. Si una falla, se usa su última copia, el reporte lo indica en `FUENTES` y la corrida no se cae. Si no hay **ninguna** encuesta de gobernador (ni en vivo, ni caché, ni propias), la corrida termina con error 1: no se pronostica a ciegas.

### Cómo se arman las encuestas
1. **Una versión por encuesta.** Por firma y fecha se elige LV > RV > A, luego mayor muestra y luego la versión con más indecisos (sin *leaners* ni reasignación).
2. **Combinación de fuentes.** Se unen sin duplicar, con prioridad Wikipedia > propias > 270toWin. Se considera la misma encuesta si es la misma firma con fecha de fin a ±7 días.
3. **Ajustes documentados.** Se aplica `data\ajustes_encuestas.csv`:
   - `reemplazar`: por ejemplo, Big Data Poll, que los agregadores publican con indecisos reasignados;
   - `agregar`: encuestas verificadas que aún no llegan a Wikipedia. Solo se usan si faltan, o si solo vinieron de 270toWin (fecha de publicación y cifras redondeadas);
   - `excluir`.
4. **Filtro y validación.** Solo encuestas posteriores a la nominación (16-jun) y no posteriores al corte. Se validan duplicados, D+R ≤ 100, fechas y claves.
5. **Claves de encuestadora.** `data\alias_encuestadoras.csv` traduce nombres a la clave de FiveThirtyEight (para el efecto de casa). Si aparece una firma nueva, agrega una fila.

## Modelo (igual al V11 validado)
```
margen   = Σ w_i (margen_i − casa_i) / Σ w_i − sesgo_GA       w_i = 2^(−Δdías/14) · √n_i / (# encuestas de la firma)
ventana  = encuestas que terminan en los últimos 21 días antes de la elección (si hay < 2 firmas: la más reciente de cada una)
σ        = √(τ² + s²/k), calibrada al horizonte del corte; distribución Student-t (ν estimado)
P_final  = mezcla logit: 0.7 · encuestas + 0.3 · Kalshi
votos    = (100 − write-ins ± margen)/2; write-ins 0.001–0.02 pp; segunda vuelta si nadie > 50 %
Senado   = mismo método; t bivariada con ρ = 0.42 respecto a gobernador (no cambia el pronóstico de gobernador)
```
Parámetros en `config\georgia.toml` → `[modelo]`:
- `w_kalshi = 0` usa solo encuestas.
- `colas_t = false` usa la distribución normal.
- `[senado] activar = false` quita el Senado.

## Salidas (`salidas\`)
- `ultimo\`: la corrida más reciente.
  - `resumen.txt`: lectura rápida; gobernador primero.
  - `pronostico_gobernador.csv`: % de cada candidato con IC80 y probabilidad de ganar.
  - `escenarios_gobernador.csv`: sensibilidad (sin Kalshi, sin sesgo GA, normal, ventanas de 30 y 45 días, Kalshi solo).
  - `encuestas_gobernador.csv` / `encuestas_senado.csv`: cada encuesta con su origen, efecto de casa y si entró en la ventana.
  - `senado_y_conjunto.csv`, `voto_anticipado_diagnostico.csv`, `reporte.json` (todo el detalle) y `pronostico.png`.
- `corridas\AAAA-MM-DD_HHMMSS\`: una carpeta por corrida; se conservan 60.
- `historial_pronosticos.csv`: una fila por corrida (serie de tiempo para el panel).
- `cache\`: última copia de cada fuente.
- Registro: `logs\pronostico.log`.

## Mantenimiento
- **Si una fuente cambia de formato:** el reporte la marca como `cache (...)` y el log explica el motivo. `python -m ga_pronostico verificar` prueba cada fuente por separado.
- **Encuesta propia nueva:** agrega la ruta del Excel en `encuestas_propias`.
- **Corrección de una encuesta:** agrega una fila en `data\ajustes_encuestas.csv`, con fuente y motivo.
- **Después de cambiar código:** corre `.venv\Scripts\python -m pytest -q`. Las 15 pruebas no usan red.

## Limitaciones
- **Parsers sin prueba en vivo desde aquí.** Los de Wikipedia y 270toWin se probaron con tablas en el formato estándar de esas páginas, porque desde el entorno de desarrollo no hay acceso a esos sitios. La primera corrida en tu equipo (`verificar`) confirma que leen las páginas reales; si no, quedan en caché y se avisa.
- **Fechas de 270toWin.** 270toWin da la fecha de publicación, no la de campo. Por eso Wikipedia tiene prioridad y existen los ajustes verificados.
- **Peso de Kalshi.** El 0.30 no está validado con historia.
