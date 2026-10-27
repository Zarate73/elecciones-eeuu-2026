# Elecciones generales de EE.UU. 2026

[![CI](https://github.com/Zarate73/elecciones-eeuu-2026/actions/workflows/ci.yml/badge.svg)](https://github.com/Zarate73/elecciones-eeuu-2026/actions/workflows/ci.yml)

**Sistema de pronósticos electorales para 14 estados: 11 implementados y automatizados (Georgia, California, Arizona, Florida, Nevada, Pennsylvania, Maine, Texas, Illinois, Nueva York y Ohio), 3 pendientes.**

**Tablero:** [zarate73.github.io/elecciones-eeuu-2026](https://zarate73.github.io/elecciones-eeuu-2026/) · se actualiza solo con cada corrida.

Cada estado tiene su modelo elegido por backtest, una versión de producción que consulta todas sus fuentes en vivo y un flujo de GitHub Actions que actualiza el pronóstico dos veces al día. Cada estado vive en su propia carpeta y sigue la misma estructura.

## Estados
| Estado | Carrera principal | Estado del modelo | Carpeta |
|---|---|---|---|
| Georgia | Gobernador: Bottoms 49.4% · Jackson 50.6% · P(Bottoms) 41% (corte 2026-10-27) | **Producción (V11)**, actualización automática | [`georgia/`](georgia/) |
| California | Gobernador: Becerra 60.9% · Hilton 39.1% · P(Becerra) 99% (corte 2026-10-26) | **Producción (M5)**, actualización automática | [`california/`](california/) |
| Arizona | Gobernador: Hobbs 51.7% · Biggs 44.4% · P(Hobbs) 92% (corte 2026-10-26) | **Producción (general)**, actualización automática | [`arizona/`](arizona/) |
| Florida | Gobernador: Jolly 44.6% · Donalds 52.4% · P(Donalds) 95% (corte 2026-10-27) | **Producción (general)**, actualización automática | [`florida/`](florida/) |
| Nevada | Gobernador: Ford 47.4% · Lombardo 46.0% · P(Ford) 59% (corte 2026-10-26) | **Producción (general)**, actualización automática | [`nevada/`](nevada/) |
| Pennsylvania | Gobernador: Shapiro 58.5% · Garrity 39.4% · P(Shapiro) >99% (corte 2026-10-27) | **Producción (general)**, actualización automática | [`pennsylvania/`](pennsylvania/) |
| Maine | Gobernador: Pingree 48.0% · Charles 44.5% · P(Pingree) 72% (corte 2026-10-27) | **Producción (general)**, actualización automática | [`maine/`](maine/) |
| Texas | Gobernador: Hinojosa 46.8% · Abbott 51.1% · P(Hinojosa) 15% (corte 2026-10-27) | **Producción (general)**, actualización automática | [`texas/`](texas/) |
| Illinois | Gobernador: Pritzker 55.8% · Bailey 38.9% · P(Pritzker) 99% (corte 2026-10-27) | **Producción (general)**, actualización automática | [`illinois/`](illinois/) |
| Nueva York | Gobernador: Hochul 55.8% · Blakeman 44.1% · P(Hochul) 98% (corte 2026-10-27) | **Producción (general)**, actualización automática | [`new_york/`](new_york/) |
| Ohio | Gobernador: Acton 48.9% · Ramaswamy 48.2% · P(Acton) 56% (corte 2026-10-27) | **Producción (general)**, actualización automática | [`ohio/`](ohio/) |
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

## Estándares comunes (aprendidos en Georgia, California, Arizona, Florida, Nevada, Pennsylvania, Maine, Texas, Illinois, Nueva York y Ohio)
- **Validación:** *leave-one-year-out* sobre el histórico de FiveThirtyEight (980 contiendas 1998–2024); métrica principal CRPS, más la cobertura de los intervalos del 80% y 95%.
- **Incertidumbre:** σ empírica `√(τ² + s²/k)` calibrada a la distancia de la elección; nada de pisos fijos sin calibrar.
- **Componentes:** se agregan solo si mejoran el CRPS fuera de muestra; lo no validable queda como diagnóstico.
- **Sesgo estatal:** se decide por estado con el backtest y siempre se reporta el escenario contrario. Georgia y Florida lo usan (en FL las encuestas sobreestimaron al demócrata en 18 de 23 contiendas); Arizona no (su error cambia de signo entre ciclos); en Nevada y Pennsylvania la evidencia estatal es nula (P ≈ 0.5) y se usa la regla nacional (sesgo contraído); en Maine el sesgo ayuda (cronológico P = 0.014) y se estima sin contiendas de una sola encuestadora; en Texas (14 de 20 contiendas pro-D) e Illinois (error que cambia de signo) el estado no es concluyente y se usa la regla nacional con todas las contiendas; en Nueva York es donde más ayuda en el estado (LOYO 2.929 vs 3.419); en Ohio las encuestas sobreestimaron al demócrata en todas las contiendas desde 2014 y el sesgo (−4.0 pp) gana en LOYO y en el cronológico (P = 0.002). Los valores P son por contienda: con bootstrap por año la mejora nacional del sesgo (ΔCRPS −0.134, IC95 [−0.320, +0.051]) no es concluyente al 95 %.
- **Alcance de la validación:** el backtest histórico valida el componente de encuestas y su error, no la mezcla con mercados (`w = 0.30`, estudiada con 40 contiendas de 2024). Ver «Qué valida y qué no valida el backtest» en cada estado y [`docs/auditoria_2026-10-26.md`](docs/auditoria_2026-10-26.md).
- **Identidad de encuestas:** módulo común `identidad.py` en los diez paquetes (firma + periodo de campo; la fecha puntual de 270toWin es publicación). Dos olas de una firma con periodos distintos nunca se funden, aunque tengan las mismas cifras; cada fusión o caso ambiguo queda en el log.
- **Producción:** todas las fuentes en vivo, con caché y degradación explícita (`--estricto` → código 2). Que las fuentes estén en vivo no significa que las encuestas sean recientes: cada reporte trae la fecha y la antigüedad de la encuesta más reciente (`ultima_encuesta`).
- **Mercados:** en Georgia, Arizona, Florida, Nevada, Pennsylvania, Maine, Texas, Illinois, Nueva York y Ohio la mezcla con mercados desplaza la distribución del margen, así que la probabilidad publicada es la fracción de simulaciones con margen > 0 (en AZ 2024 esto bajó el error del margen en las dos contiendas con historia de mercados). En California Kalshi ajusta solo la probabilidad publicada: margen, intervalos y % de voto son los del modelo.
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
| [Polymarket](https://polymarket.com) API Gamma pública | Precio de mercado (AZ, FL y NV, promediado con Kalshi) | Términos de Polymarket |
| [civicAPI](https://civicapi.org) voto anticipado | Diagnóstico de voto anticipado por partido y condado (AZ, FL, NV) | Uso libre con atribución |
| Wikipedia, 270toWin, medios citados en cada CSV | Encuestas publicadas (cifras de resumen) | Cada fila lleva su URL de origen |
| G-Ratings | Encuesta propia (solo resultados de resumen) | Publicados por el autor |

## Autor
Saúl Zárate Feliciano · ingeniero matemático · análisis de datos, encuestas y modelos de pronóstico ([@Zarate73](https://github.com/Zarate73)).
