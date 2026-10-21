# Georgia · Modelo final V11 (lo mejor de V5–V10), 20-oct-2026

- **Código:** `georgia/modelo_v11/` (notebook ejecutado, módulo, 17 pruebas, LEEME).
- **Backtests:** `georgia/backtest/` (`backtest_componentes_versiones.py`, `combinacion_final.py`, `backtest_observaciones.py`).

## Revisión de versiones (V5–V9)
| Versión | Aporta | Problema principal |
|---|---|---|
| Sin sentimiento | M1, M2, M3 + Civic Forge | σ de 2.1 a 2.7, sin calibrar |
| M4 Monte Carlo | M4-H + M4-E (contra el mismo día de 2022) | M4-E sin datos; M4-H no validable |
| V5 | M4-H sin comparador | extrapola 2018→2022, pro-D |
| V6–V8 | tres categorías, auditoría, escenarios de redistribución | escenarios no inferidos |
| V9 | integrado: shocks, Beta de indecisos, territorial | sesgos documentados en `01_revision_v9.md` |

## Backtest de componentes (LOYO, 15 días, CRPS nacional / GA)
| Componente | Resultado | Decisión |
|---|---|---|
| Base V10 | 3.455 / 2.783 | — |
| **Colas t (V8-M3)** | **3.450 / 2.763**; P(mejor) 0.86 / 0.84 | **se adopta** |
| Vida media de 5 días / pesos 1/var / firma 1/√rep / Kalman / shocks Poisson | 3.457 / 3.464 / 3.456 / 3.475 / 3.456 | descartados |
| M4-E: % negro del anticipado al mismo día | RMSE GA 2.94 contra 1.63 | diagnóstico |
| Tres categorías | reporte | se adopta |

## Revisión externa (20-oct)
| Observación | Prueba (LOYO, CRPS) | Decisión |
|---|---|---|
| Prior estructural (lean + entorno nacional), peso 15–25% | Gobernadores del país (232): 3.655 sin prior, 3.705 con β≈0.08, 3.971 con β=0.20. GA (21): 2.755 → 2.573 → 2.468 | **No entra**: empeora en gobernadores |
| Correlación con el Senado | ρ errores Gob–Sen mismo estado-año = **0.42** (IC95 0.23–0.58; 120 pares) | **Entra**: Senado y t bivariada conjunta |
| Composición del electorado (edad, volumen) | Civic Forge a 15 días; solo 2 comparaciones por tipo de ciclo | **Diagnóstico** |
| Gasto / autofinanciamiento | Sin serie histórica | **Fuera** |

## Pronóstico al 20-oct (14 días antes)
| | Resultado |
|---|---|
| **Gobernador** (encuestas + Kalshi, colas t) | Bottoms − Jackson **−1.4** (σ 5.4), P(Bottoms) = **0.39** |
| Gobernador, solo encuestas | −2.0, P = 0.35 |
| **Senado** | Ossoff − Collins **+8.2** (σ 6.2), P(Ossoff) = **0.91** |
| Jackson + Ossoff / Bottoms + Ossoff / Jackson + Collins / Bottoms + Collins | 0.54 / 0.38 / 0.08 / 0.01 |

## Voto anticipado (Civic Forge, CC BY 4.0) — % negro a 15 días
| 2018 | 2020 | 2022 | 2024 | 2026 |
|---|---|---|---|---|
| 30.1 | 30.5 | 32.2 | 27.4 | **34.8** |

Solo diagnóstico; sin valor predictivo demostrado.
