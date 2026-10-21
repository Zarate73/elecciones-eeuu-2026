# California 2026 · Producción (modelo M5)

Versión de producción del notebook M5 ([`../modelo_m5/`](../modelo_m5/)): paquete de Python, línea de comandos, configuración en un solo archivo, registros, pruebas y tarea programada de Windows. Con las mismas encuestas da los mismos números que el notebook, y una prueba lo verifica.

**Las encuestas se leen en vivo** (Wikipedia y 270toWin) en cada corrida y se combinan con una base verificada a mano. En GitHub, Actions corre el pronóstico dos veces al día y actualiza [`../README.md`](../README.md).

## Instalación (una vez)
Requisito: Python 3.10 o superior.
1. Doble clic en `scripts\instalar.bat`. Crea `.venv`, instala dependencias, revisa rutas y corre las pruebas.
2. Revisa `config\california.toml` → `[rutas]`:
   - `encuestas_base`: base verificada a mano. Puede ser el Excel `CALIFORNIA_GOBERNADOR-v3.xlsx` o su exportación `data\encuestas_verificadas.csv` (la que usa el repositorio).
   - `carpeta_sentimiento`: `entrega_sentimiento` (opcional, solo diagnóstico).

## Uso diario
| Acción | Comando |
|---|---|
| Correr el pronóstico | `scripts\correr_pronostico.bat` |
| Ver el último resultado | `scripts\abrir_ultimo.bat` |
| Programar todos los días a las 08:00 | `powershell -ExecutionPolicy Bypass -File scripts\programar_tarea.ps1` |
| Varias veces al día | `... programar_tarea.ps1 -Horas 08:00,20:00` |
| Quitar la tarea | `... programar_tarea.ps1 -Eliminar` |
| Sin red (solo cachés) | `scripts\correr_pronostico.bat --offline` |
| Reproducir un corte | `scripts\correr_pronostico.bat --corte 2026-10-15` |
| Noche electoral | `scripts\correr_pronostico.bat --modo-conteo` |
| Proyección del conteo | `.venv\Scripts\python -m ca_pronostico conteo --votos-d N --votos-r N --restantes N` |
| Revisar instalación | `.venv\Scripts\python -m ca_pronostico verificar` |

Códigos de salida: `0` OK · `1` error fatal (ninguna encuesta: ni base, ni en vivo, ni caché) · `2` alguna fuente no estuvo en vivo (solo con `--estricto`).

## Salidas (`salidas\`)
- `ultimo\`: la corrida más reciente. Contiene:
  - `resumen.txt`: lectura rápida.
  - `reporte.json`: todo el detalle, incluido el estado de cada fuente.
  - `pronostico_porcentajes.csv/.png`: % de voto de cada candidato con IC 80% y 95%.
  - `comparacion_modelos.csv`: M5 frente a M1–M4 legados.
  - `encuestas_pesos.csv`, `distribucion_margen.png`, `componentes_varianza.png`.
- `corridas\AAAA-MM-DD_HHMMSS\`: una carpeta por corrida. Se conservan las últimas 60 (`ejecucion.conservar_corridas`).
- `historial_pronosticos.csv`: una fila por corrida. Es la serie de tiempo del pronóstico, para el panel.
- `cache\`: últimos datos de cada fuente. Se usan si una fuente falla, y el reporte lo indica.

Registro de ejecución: `logs\pronostico.log`, con rotación de 5 × 5 MB.

## Fuentes y qué hace cada una
| Fuente | Vía | Si falla | Efecto en el pronóstico |
|---|---|---|---|
| **Wikipedia** (tabla de encuestas Becerra–Hilton) | API MediaWiki `action=parse` | caché | media (agregado M5); fuente principal: fechas de campo exactas |
| **270toWin** | página HTML | caché | encuestas que Wikipedia aún no tiene (fecha de publicación) |
| Base verificada (Excel o `data\encuestas_verificadas.csv`) | archivo | se omite con aviso | encuestas que no están en los agregadores (p. ej. las encargadas por campañas) |
| Civiq | API pública → Brave/Playwright (no en GitHub Actions) → caché | caché | diagnóstico de participación; no entra a la media mientras `w_m2 = 0` |
| Civiq historia y condados | API pública | caché | comparación al mismo día; base del módulo de conteo |
| Kalshi | API pública | último snapshot → histórico | mezcla de la probabilidad (`w_kalshi = 0.30`); se descarta si tiene más de 3 días o en `--modo-conteo` |
| GDELT | API DOC 2.0 | caché (12 h) | diagnóstico; solo entra con `validado_sentimiento = true` |
| Sentimiento propio | `entrega_sentimiento\` | se omite | diagnóstico (y M4 legado) |
| PDI | `data\pdi_retornos_manual.csv` (manual) | se omite | contraste |
| Backtest 2018–2025 | `data\generales_*.csv` | — | calibra σ en cada corrida |

### Cómo se combinan las encuestas
1. Una versión por encuesta (misma firma y fecha): LV > RV > A, luego mayor muestra, luego más indecisos.
2. Prioridad Wikipedia > base verificada > 270toWin. Misma encuesta = misma familia de encuestadora con fin a ≤ 7 días, o con las mismas cifras a ≤ 21 días (270toWin fecha por publicación).
3. La familia se normaliza sin etiquetas: «Manhattan Institute (R)» = «Manhattan Institute». La marca (D)/(R) o «encargada por la campaña» aplica el peso `penal_interna`.
4. Se excluyen las encuestas de la primaria (anteriores al 2-jun) y las posteriores al corte.
5. `encuestas_en_vivo = false` en `[fuentes]` usa solo la base verificada (= notebook).

## Parámetros clave (`config\california.toml` → `[modelo]`)
- `w_m2` (0): peso de la participación. Súbelo (p. ej. a 0.25) solo si la evidencia de participación se sostiene.
- `validado_sentimiento` (false): activa el multiplicador de volatilidad por sentimiento.
- `w_kalshi` (0.30): peso del mercado en la probabilidad. No afecta los porcentajes de voto.
- `penal_interna` (0.5): peso de las encuestas de campaña o partidistas.
- `sigma_sis_pp` (vacío): vacío = calibrar automáticamente. Pon un número para fijarlo.

## Estructura del código
```
ca_pronostico/
  config.py            carga y valida el .toml
  encuestas.py         base verificada (Excel o CSV), agregado legado y M5
  encuestas_web.py     Wikipedia y 270toWin en vivo, caché y combinación sin duplicados
  civiq.py             API de Civiq, caché, historia, condados y diagnósticos de participación
  civiq_navegador.py   respaldo con Brave/Playwright
  externas.py          Kalshi, GDELT, PDI
  sentimiento_propio.py  señal M4
  modelo.py            calibración de σ, simulación M5, porcentajes, conteo
  legado.py            M1–M4 originales (comparación)
  reporte.py           escritura de salidas y gráficas
  pipeline.py          orquestación de una corrida
  cli.py               línea de comandos
tests/                 pruebas sin red con respuestas reales de Civiq (19-oct), Wikipedia y 270toWin (21-oct-2026)
```

## Mantenimiento
- **Nuevas encuestas:** llegan solas desde Wikipedia y 270toWin. Agrega a la base verificada solo las que no publiquen los agregadores.
- **PDI:** agrega una fila a `data\pdi_retornos_manual.csv`.
- **Si cambia el formato de la API de Civiq:** el reporte mostrará `civiq: ... caché` o `navegador`. Revisa `logs\pronostico.log`.
- **Después de cambiar código:** corre `.venv\Scripts\python -m pytest -q`.
