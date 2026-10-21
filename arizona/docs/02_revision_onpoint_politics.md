# Revisión de On Point Politics y civicAPI (21-oct-2026)

## On Point Politics
Fuente: [metodología](https://www.onpointpolitics.us/forecast/methodology) y [cambios](https://www.onpointpolitics.us/forecast/changelog).

**Pronósticos:**
- AZ: Hobbs 55.0 / Biggs 42.6 / terceros 2.4. **D+12.4 (80 %: +5.2 a +19.8), 99 %**.
- GA: Bottoms +0.5 (55 %).
- CA: Becerra con más de 99 %.

**Modelo dominado por fundamentales:**
- Lean 2024 por condado.
- Voto genérico nacional D+12.
- Gallup 50 D / 39 R, convertido a D+15.4 entre votantes probables; pesa al menos 40 % en Senado y gobernador.
- Aprobación de su base TPSI, gasolina (AAA), centros de datos, FEC.
- 1,152 tipos de votante por condado; choques nacionales, demográficos, estatales y de condado.
- Gobernadores con β = λ = 0.6.
- Voto anticipado como corrección de participación: +0.6 en AZ.

**Datos:**
- Encuestas propias y públicas, con calificación por encuestadora.
- JSON público por contienda: `/api/polls/{az|ga|ca}-gov-2026`.
- Voto anticipado de **civicAPI**.

**Problemas:**
- Mete el promedio de RCP como encuesta en AZ.
- Promedio inconsistente: +5.7 en el JSON y +10.5 en la ficha.
- Les faltan Wick y HighGround de octubre.
- Su backtest de fundamentales en gobernadores da 15 pp de error medio.

## Backtest de sus ideas (LOYO, 782 contiendas, `../backtest/backtest_onpoint.py`)
| Idea | Nacional | AZ | Decisión |
|---|---|---|---|
| Penalizar indecisos (peso × e^(−U/15)) | 3.519 vs 3.495 (P 0.05) | 2.447 vs 2.471 (P 0.60) | No |
| Excluir encuestas con ≥ 20 % de indecisos | 3.520 (P 0.04) | 2.532 | No |
| Recortar atípicas a ±2 DE | 3.495 (P 0.45) | 2.464 (P 0.89) | No (neutro) |
| Peso por calidad de la encuestadora | **3.487 (P 0.68–0.78)** | 2.508 (P 0.06) | No en AZ; **candidata para el estándar** |
| Terceros con el historial del estado | neutro | neutro | No |
| Fundamentales | rechazado en GA (3.655 → 3.705) | | No |

## Efectos de casa y ajuste partidista (sin sesgo estatal)
| Variante | CRPS nacional | CRPS AZ (22) |
|---|---|---|
| Sin efectos de casa | **3.545** | 2.480 |
| Efecto por firma, k = 8 (en uso) | 3.561 | 2.471 |
| Ajuste por patrocinador partidista (D +2.6, R −3.1) | 3.579 | **2.447** |
| Firma, o partidista si no hay historia | 3.562 | 2.471 |

Ninguna diferencia es concluyente (P entre 0.09 y 0.67 en el bootstrap por año). Se mantiene el efecto por firma y el ajuste partidista queda como escenario.

## civicAPI (integrado en producción como diagnóstico)
- API gratuita, sin clave; pide atribución.
- **Solo AZ trae desglose por partido y condado.** CA y GA dan totales sin partido («Unspecified»); ahí se quedan Civiq (CA) y Civic Forge (GA).
- Endpoints: `/api/v2/early-vote/AZ/{returned|requested}` (por condado y partido) y `.../demographics?by=party`.
- **Arizona al 21-oct:**
  - 642,253 boletas devueltas (D 39.2 / R 38.2 / otros 22.6) de 3.26 millones solicitadas.
  - Tasas de devolución: D 24.0 %, R 21.3 %, otros 13.6 %.
  - Maricopa: 59.7 % de lo devuelto, D+0.8. Pima D+24.3.
- **Su pronóstico combinado** (`/api/v2/forecast/governor/2026/civicapi`) da AZ Likely D, 81 %.
