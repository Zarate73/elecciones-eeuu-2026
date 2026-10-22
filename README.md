# Elecciones generales de EE.UU. 2026

[![CI](https://github.com/Zarate73/elecciones-eeuu-2026/actions/workflows/ci.yml/badge.svg)](https://github.com/Zarate73/elecciones-eeuu-2026/actions/workflows/ci.yml)

**Sistema de pronósticos electorales para 14 estados: 3 implementados y automatizados (Georgia, California y Arizona), 11 pendientes.**

**Tablero:** [zarate73.github.io/elecciones-eeuu-2026](https://zarate73.github.io/elecciones-eeuu-2026/) · se actualiza solo con cada corrida.

Cada estado tiene su modelo elegido por backtest, una versión de producción que consulta todas sus fuentes en vivo y un flujo de GitHub Actions que actualiza el pronóstico dos veces al día. Cada estado vive en su propia carpeta y sigue la misma estructura.

## Estados
| Estado | Carrera principal | Estado del modelo | Carpeta |
|---|---|---|---|
| Georgia | Gobernador: Bottoms 49.4% · Jackson 50.6% · P(Bottoms) 40% (corte 2026-10-22) | **Producción (V11)**, actualización automática | [`georgia/`](georgia/) |
| California | Gobernador: Becerra 61.1% · Hilton 38.9% · P(Becerra) 99% (corte 2026-10-21) | **Producción (M5)**, actualización automática | [`california/`](california/) |
| Arizona | Gobernador: Hobbs 51.7% · Biggs 44.2% · P(Hobbs) 93% (corte 2026-10-21) | **Producción (general)**, actualización automática | [`arizona/`](arizona/) |
| … | | pendiente | |

## Estructura por estado
```
<estado>/
  produccion/        paquete de Python con CLI, fuentes en vivo, pruebas y tarea programada de Windows
  modelo_*/          notebook final ejecutado + módulo del modelo (referencia y análisis)
  backtest/          scripts de backtest y selección de modelo, con sus datos y resultados
  docs/              revisiones, decisiones de modelo y resultados documentados
```
`tablero/` es la página pública (GitHub Pages); `scripts/exportar_tablero.py` lleva los resultados de cada estado a `tablero/datos/`.

## Estándares comunes (aprendidos en Georgia, California y Arizona)
- **Validación:** *leave-one-year-out* sobre el histórico de FiveThirtyEight (980 contiendas 1998–2024); métrica principal CRPS, más la cobertura de los intervalos del 80% y 95%.
- **Incertidumbre:** σ empírica `√(τ² + s²/k)` calibrada a la distancia de la elección; nada de pisos fijos sin calibrar.
- **Componentes:** se agregan solo si mejoran el CRPS fuera de muestra; lo no validable queda como diagnóstico.
- **Producción:** todas las fuentes en vivo, con caché y degradación explícita (`--estricto` → código 2). Que las fuentes estén en vivo no significa que las encuestas sean recientes: cada reporte trae la fecha y la antigüedad de la encuesta más reciente (`ultima_encuesta`).
- **Mercados:** en Georgia y Arizona la mezcla con mercados desplaza la distribución del margen, así que la probabilidad publicada es la fracción de simulaciones con margen > 0 (en AZ 2024 esto bajó el error del margen en las dos contiendas con historia de mercados). En California Kalshi ajusta solo la probabilidad publicada: margen, intervalos y % de voto son los del modelo.
- **Salidas para tableros:** `salidas/ultimo/reporte.json` es JSON estricto (RFC 8259, sin `NaN` ni `Infinity`; los valores faltantes son `null`).
- **Pruebas:** sin red, con fixtures que reproducen el formato de cada fuente; el flujo [CI](.github/workflows/ci.yml) las corre en cada push y pull request.

## Requisitos
Python 3.10+. Cada `produccion/` trae `requirements.txt` y `scripts\instalar.bat`.

## Fuentes de datos y licencias
| Fuente | Uso | Licencia / condiciones |
|---|---|---|
| [FiveThirtyEight pollster ratings – raw polls](https://github.com/fivethirtyeight/data/tree/master/pollster-ratings) | Calibración histórica (1998–2022) | CC BY 4.0 |
| [Civic Forge – Georgia early vote](https://www.civicforge.solutions/data/ga-2026-general) | Diagnóstico de voto anticipado (GA) | CC BY 4.0 |
| [Civiq – California ballot returns](https://abev.civiq.vote/) API pública | Diagnóstico de voto anticipado (CA) | Términos de Civiq |
| [GDELT DOC 2.0](https://www.gdeltproject.org/) | Tono de cobertura (diagnóstico, CA) | Uso libre con atribución |
| [Kalshi](https://kalshi.com) API pública | Precio de mercado | Términos de Kalshi |
| [Polymarket](https://polymarket.com) API Gamma pública | Precio de mercado (AZ, promediado con Kalshi) | Términos de Polymarket |
| [civicAPI](https://civicapi.org) voto anticipado | Diagnóstico de voto anticipado por partido y condado (AZ) | Uso libre con atribución |
| Wikipedia, 270toWin, medios citados en cada CSV | Encuestas publicadas (cifras de resumen) | Cada fila lleva su URL de origen |
| G-Ratings | Encuesta propia (solo resultados de resumen) | Publicados por el autor |

## Autor
Saúl Zárate Feliciano · ingeniero matemático · análisis de datos, encuestas y modelos de pronóstico ([@Zarate73](https://github.com/Zarate73)).
