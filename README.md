# Elecciones generales de EE.UU. 2026

Modelos de pronóstico, backtests y versiones de producción para las contiendas de 2026 en **14 estados**. Cada estado vive en su propia carpeta y sigue la misma estructura.

## Estados
| Estado | Carrera principal | Estado del modelo | Carpeta |
|---|---|---|---|
| Georgia | Gobernador: Bottoms 49.2% · Jackson 50.8% · P(Bottoms) 37% (corte 2026-10-21) | **Producción (V11)**, actualización automática | [`georgia/`](georgia/) |
| California | Gobernador: Becerra 61.1% · Hilton 38.9% · P(Becerra) 99% (corte 2026-10-21) | **Producción (M5)**, actualización automática | [`california/`](california/) |
| … | | pendiente | |

## Estructura por estado
```
<estado>/
  produccion/        paquete de Python con CLI, fuentes en vivo, pruebas y tarea programada de Windows
  modelo_*/          notebook final ejecutado + módulo del modelo (referencia y análisis)
  backtest/          scripts de backtest y selección de modelo, con sus datos y resultados
  docs/              revisiones, decisiones de modelo y resultados documentados
```

## Estándares comunes (aprendidos en Georgia y California)
- **Validación:** *leave-one-year-out* sobre el histórico de FiveThirtyEight (980 contiendas 1998–2024); métrica principal CRPS, más la cobertura de los intervalos del 80% y 95%.
- **Incertidumbre:** σ empírica `√(τ² + s²/k)` calibrada a la distancia de la elección; nada de pisos fijos sin calibrar.
- **Componentes:** se agregan solo si mejoran el CRPS fuera de muestra; lo no validable queda como diagnóstico.
- **Producción:** todas las fuentes en vivo, con caché y degradación explícita (`--estricto` → código 2).
- **Pruebas:** sin red, con fixtures que reproducen el formato de cada fuente.

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
| Wikipedia, 270toWin, medios citados en cada CSV | Encuestas publicadas (cifras de resumen) | Cada fila lleva su URL de origen |
| G-Ratings | Encuesta propia (solo resultados de resumen) | Publicados por el autor |

## Autor
Saúl Zárate Feliciano · ingeniero matemático · análisis de datos, encuestas y modelos de pronóstico ([@Zarate73](https://github.com/Zarate73)).
