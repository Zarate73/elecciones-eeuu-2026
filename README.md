# Elecciones generales de EE.UU. 2026

[![CI](https://github.com/Zarate73/elecciones-eeuu-2026/actions/workflows/ci.yml/badge.svg)](https://github.com/Zarate73/elecciones-eeuu-2026/actions/workflows/ci.yml)

**Sistema de pronósticos electorales para 14 estados, los 14 implementados y automatizados (Georgia, California, Arizona, Florida, Nevada, Pennsylvania, Maine, Texas, Illinois, Nueva York, Ohio, North Carolina, Wisconsin y Washington D.C.).**

**Tablero:** [zarate73.github.io/elecciones-eeuu-2026](https://zarate73.github.io/elecciones-eeuu-2026/) · se actualiza solo con cada corrida.

Cada estado tiene su modelo elegido por backtest, una versión de producción que consulta todas sus fuentes en vivo y un flujo de GitHub Actions que actualiza el pronóstico dos veces al día. Cada estado vive en su propia carpeta y sigue la misma estructura.

## Estados
| Estado | Carrera principal | Estado del modelo | Carpeta |
|---|---|---|---|
| Georgia | Gobernador: Bottoms 50.0% · Jackson 50.0% · P(Bottoms) 50% (corte 2026-10-29) | **Producción (V11)**, actualización automática | [`georgia/`](georgia/) |
| California | Gobernador: Becerra 61.3% · Hilton 38.7% · P(Becerra) 99% (corte 2026-10-28) | **Producción (M5)**, actualización automática | [`california/`](california/) |
| Arizona | Gobernador: Hobbs 51.5% · Biggs 44.3% · P(Hobbs) 90% (corte 2026-10-28) | **Producción (general)**, actualización automática | [`arizona/`](arizona/) |
| Florida | Gobernador: Jolly 45.2% · Donalds 52.5% · P(Donalds) 96% (corte 2026-10-29) | **Producción (general)**, actualización automática | [`florida/`](florida/) |
| Nevada | Gobernador: Ford 47.9% · Lombardo 45.4% · P(Ford) 68% (corte 2026-10-28) | **Producción (general)**, actualización automática | [`nevada/`](nevada/) |
| Pennsylvania | Gobernador: Shapiro 58.7% · Garrity 39.3% · P(Shapiro) >99% (corte 2026-10-29) | **Producción (general)**, actualización automática | [`pennsylvania/`](pennsylvania/) |
| Maine | Gobernador: Pingree 49.4% · Charles 44.0% · P(Pingree) 86% (corte 2026-10-29) | **Producción (general)**, actualización automática | [`maine/`](maine/) |
| Texas | Gobernador: Hinojosa 47.1% · Abbott 50.8% · P(Hinojosa) 18% (corte 2026-10-28) | **Producción (general)**, actualización automática | [`texas/`](texas/) |
| Illinois | Gobernador: Pritzker 56.0% · Bailey 38.8% · P(Pritzker) 99% (corte 2026-10-28) | **Producción (general)**, actualización automática | [`illinois/`](illinois/) |
| Nueva York | Gobernador: Hochul 55.4% · Blakeman 44.4% · P(Hochul) 99% (corte 2026-10-29) | **Producción (general)**, actualización automática | [`new_york/`](new_york/) |
| Ohio | Gobernador: Acton 48.9% · Ramaswamy 48.1% · P(Acton) 58% (corte 2026-10-28) | **Producción (general)**, actualización automática | [`ohio/`](ohio/) |
| North Carolina | Senado: Cooper 53.4% · Whatley 43.5% · P(Cooper) 97% (corte 2026-10-28) | **Producción (general)**, actualización automática | [`north_carolina/`](north_carolina/) |
| Wisconsin | Gobernador: Crowley 52.8% · Tiffany 47.1% · P(Crowley) 82% (corte 2026-10-28) | **Producción (general)**, actualización automática | [`wisconsin/`](wisconsin/) |
| Washington D.C. | Alcaldía: Lewis George 79.6% · Hamilton 15.4% · P(Lewis George) >99% (corte 2026-10-29) | **Producción (general)**, actualización automática | [`dc/`](dc/) |

## Estructura por estado
```
<estado>/
  produccion/        paquete de Python con CLI, fuentes en vivo, pruebas y tarea programada de Windows
  modelo_*/          notebook final ejecutado + módulo del modelo (referencia y análisis)
  backtest/          scripts de backtest y selección de modelo, con sus datos y resultados
  docs/              revisiones, decisiones de modelo y resultados documentados
```
`tablero/` es la página pública (GitHub Pages); `scripts/exportar_tablero.py` lleva los resultados de cada estado a `tablero/datos/`.

## Estándares comunes (aprendidos en Georgia, California, Arizona, Florida, Nevada, Pennsylvania, Maine, Texas, Illinois, Nueva York, Ohio, North Carolina y Wisconsin)
- **Validación:** *leave-one-year-out* sobre el histórico de FiveThirtyEight (980 contiendas 1998–2024); métrica principal CRPS, más la cobertura de los intervalos del 80% y 95%.
- **Incertidumbre:** σ empírica `√(τ² + s²/k)` calibrada a la distancia de la elección; nada de pisos fijos sin calibrar.
- **Componentes:** se agregan solo si mejoran el CRPS fuera de muestra; lo no validable queda como diagnóstico.
- **Sesgo estatal:** se decide por estado con el backtest y siempre se reporta el escenario contrario. Georgia y Florida lo usan (en FL las encuestas sobreestimaron al demócrata en 18 de 23 contiendas); Arizona no (su error cambia de signo entre ciclos); en Nevada y Pennsylvania la evidencia estatal es nula (P ≈ 0.5) y se usa la regla nacional (sesgo contraído); en Maine el sesgo ayuda (cronológico P = 0.014) y se estima sin contiendas de una sola encuestadora; en Texas (14 de 20 contiendas pro-D) e Illinois (error que cambia de signo) el estado no es concluyente y se usa la regla nacional con todas las contiendas; en Nueva York es donde más ayuda en el estado (LOYO 2.929 vs 3.419); en Ohio las encuestas sobreestimaron al demócrata en todas las contiendas desde 2014 y el sesgo (−4.0 pp) gana en LOYO y en el cronológico (P = 0.002). En North Carolina (primer estado de Senado) las encuestas sobreestimaron al demócrata en las 10 contiendas desde 2014 y se usa la regla «todas» (−2.1 pp); ninguna variante propia del Senado (σ o sesgo por cargo, fundamentales, escala) mejora al modelo en las 383 contiendas de Senado. En Wisconsin el error de las encuestas cambia de signo entre ciclos y cargos (presidente 2016/2020 pro-D, gobernador 2022 pro-R) y, como en Arizona, el modelo va sin sesgo estatal (LOYO WI 2.630 vs 2.822). Washington D.C. es la excepción: sin encuestas ni mercados de la general, el modelo es de fundamentales (13 generales de alcaldía 1974–2022, LOYO) con conteo RCV. Los valores P son por contienda: con bootstrap por año la mejora nacional del sesgo (ΔCRPS −0.134, IC95 [−0.320, +0.051]) no es concluyente al 95 %.
- **Alcance de la validación:** el backtest histórico valida el componente de encuestas y su error, no la mezcla con mercados (`w = 0.30`, estudiada con 40 contiendas de 2024). Ver «Qué valida y qué no valida el backtest» en cada estado y [`docs/auditoria_2026-10-26.md`](docs/auditoria_2026-10-26.md).
- **Identidad de encuestas:** módulo común `identidad.py` en todos los paquetes (firma + periodo de campo; la fecha puntual de 270toWin es publicación). Dos olas de una firma con periodos distintos nunca se funden, aunque tengan las mismas cifras; cada fusión o caso ambiguo queda en el log.
- **Producción:** todas las fuentes en vivo, con caché y degradación explícita (`--estricto` → código 2). Que las fuentes estén en vivo no significa que las encuestas sean recientes: cada reporte trae la fecha y la antigüedad de la encuesta más reciente (`ultima_encuesta`).
- **Mercados:** en Georgia, Arizona, Florida, Nevada, Pennsylvania, Maine, Texas, Illinois, Nueva York, Ohio, North Carolina y Wisconsin la mezcla con mercados desplaza la distribución del margen, así que la probabilidad publicada es la fracción de simulaciones con margen > 0 (en AZ 2024 esto bajó el error del margen en las dos contiendas con historia de mercados). En California Kalshi ajusta solo la probabilidad publicada: margen, intervalos y % de voto son los del modelo.
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
| Wikipedia, 270toWin, medios citados en cada CSV | Encuestas publicadas (cifras de resumen); en D.C., resultados de las generales de alcaldía 1974–2022 | Cada fila lleva su URL de origen |
| [DCBOE](https://www.dcboe.org) (Junta Electoral de D.C.) | Registro por partido y resultados certificados (DC) | Información pública |
| G-Ratings | Encuesta propia (solo resultados de resumen) | Publicados por el autor |

## Autor
Saúl Zárate Feliciano · ingeniero matemático · análisis de datos, encuestas y modelos de pronóstico ([@Zarate73](https://github.com/Zarate73)).
