# ODISEO · Georgia Gobernador 2026 · Modelo final (v11)

**Lo mejor de V5 a V10, validado por backtest.** Se probó cada componente de las versiones anteriores en el mismo marco *leave-one-year-out* (980 contiendas de 1998 a 2024, a 15 días de la elección; ver `../BACKTEST_GEORGIA/backtest_componentes_versiones.py`). Solo se quedaron los que mejoran el CRPS fuera de muestra.

## Uso (Windows / VS Code)
1. `py -m pip install -r requirements.txt`
2. Abre `GEORGIA_2026_MODELO_FINAL_V11.ipynb` y ejecuta todas las celdas.
3. Para actualizar:
   - agrega las encuestas a `datos/ga_gob2026_encuestas.csv`;
   - cambia `corte`;
   - opcional: `kalshi_en_vivo=True`;
   - para el diagnóstico de voto anticipado, agrega la fila del día a `datos/civicforge_raza_T15.csv` desde `https://www.civicforge.solutions/api/ga-2026-general/crosstab?groupBy=race`.
4. Pruebas: `py pruebas.py`. Son 17, escriben en una carpeta temporal y no tocan `salida/`.

## Qué se tomó de cada versión
| Versión | Componente | Resultado en backtest (CRPS nacional / GA) | Decisión |
|---|---|---|---|
| V8-M1 / V9 | promedio con recencia y un voto por firma | base | **se queda** (vida media de 14 días) |
| V8-M1 | vida media de 5 días | 3.457 / 2.777 (base 3.455 / 2.783) | descartado: no generaliza |
| V8 / V9 | pesos 1/varianza muestral | 3.464 / 2.778 | descartado |
| V9 | penalización por firma 1/√repeticiones | 3.456 / 2.785 | descartado |
| V8-M2 | filtro de Kalman de nivel local | 3.475 / 2.785 | descartado |
| **V8-M3** | **colas Student-t (ν ≈ 10.5)** | **3.450 / 2.763**; P(mejor) 0.86 / 0.84 | **se queda** |
| V9 | shocks Poisson | 3.456 / 2.791 | descartado |
| V9 | Beta de indecisos (0.436 a R) | 3.545 / 2.837 | descartado (50/50 es mejor) |
| V5–V9 | territorial M4-H | no validable (solo hay mapas 2018 y 2022); +0.6 a +1.5 pp pro-D por construcción | descartado |
| V5 M4-E | voto anticipado contra el mismo día (Civic Forge) | RMSE GA 2.94 contra 1.63 sin corregir | **solo diagnóstico** |
| V6–V8 | tres categorías (Other/None separado) | es un formato de reporte | **se queda** como reporte |
| V10 | efectos de casa, sesgo GA, σ(k), Kalshi | 3.455 / 2.783 | **se queda** |

## Revisión externa (20-oct): qué se aplicó
| Observación | Prueba | Decisión |
|---|---|---|
| Prior estructural débil (lean del estado + entorno nacional, peso 15–25%) | LOYO a 15 días. Gobernadores del país (232): CRPS 3.655 sin prior, 3.705 con β estimado (≈0.08), 3.971 con β = 0.20. GA: 2.755 → 2.573 / 2.468 | **No entra.** Empeora justo en las carreras a gobernador; la mejora en GA (n = 21) no generaliza. Evidencia en `evidencia_backtest/G_prior_estructural.csv` |
| Correlación con el Senado | ρ de errores Gob–Sen del mismo estado y año = 0.42 (IC95 0.23–0.58; 120 pares) | **Entra:** Senado modelado y simulación conjunta (t bivariada) |
| Composición del electorado (edad) y volumen del anticipado | Civic Forge a 15 días, 2018–2026: solo hay 2 comparaciones por tipo de ciclo | **Diagnóstico** (tabla en el notebook) |
| Gasto y autofinanciamiento | No hay series históricas para calibrarlo | **Fuera** |
| Peso de Kalshi | Sin historia para validarlo | Se mantiene en 0.30 |

Además se corrigió un error en la ventana de respaldo: al ampliarla arrastraba encuestas viejas de las mismas firmas. Ahora usa la encuesta más reciente de cada una.

## Modelo
```
margen  = Σ w_i (margen_i − casa_i) / Σ w_i − sesgo_GA      w_i = 2^(−Δdías/14) · √n_i / (# encuestas de la firma)
σ       = √(τ² + s²/k)       τ = 3.0, s = 7.4 a 15 días; k = encuestadoras distintas
M ~ μ + σ·√((ν−2)/ν)·t_ν     ν ≈ 10.5 (MLE con 701 errores estandarizados)
P_final = mezcla logit: 0.7 · encuestas + 0.3 · Kalshi   (peso de Kalshi no validado)
votos   : B = (100 − W + M)/2, J = (100 − W − M)/2,  W = write-ins ~ U(0.001, 0.02) pp
```

## Resultado al 20-oct-2026 (14 días antes)
- **Gobernador:**
  - final: margen Bottoms − Jackson **−1.4 pp**, σ = 5.4, P(Bottoms) = **0.39**, P(segunda vuelta) ≈ 0.2%;
  - solo encuestas: −2.0 y P = 0.35; Kalshi solo: P = 0.49.
- **Senado:** Ossoff − Collins **+8.2 pp**, σ = 6.2, P(Ossoff) = **0.91**. La ventana se amplió al 9-oct (Trafalgar y Quantus).
- **Conjunto:**
  - Jackson + Ossoff: 0.54, el más probable;
  - Bottoms + Ossoff: 0.38;
  - Jackson + Collins: 0.08;
  - Bottoms + Collins: 0.01;
  - P(Bottoms | gana Ossoff) = 0.41 y P(Bottoms | gana Collins) = 0.14.
- **Voto anticipado** (diagnóstico): 34.8% negro (+2.6 contra 2022) y 46.8% de 65+ (+2.0 contra 2022) al mismo día.

## Cómo agregar encuestas
Una fila por encuesta en `datos/ga_gob2026_encuestas.csv`:

| columna | contenido |
|---|---|
| `pollster` | nombre de la encuestadora |
| `clave_538` | nombre en minúsculas, solo letras, máx. 14 (permite usar el efecto de casa histórico; p. ej. `insideradvanta`, `rasmussenrepor`, `universityofge`, `yougov`, `emersoncollege`, `trafalgargroup`) |
| `inicio`, `fin` | fechas de campo, AAAA-MM-DD |
| `n`, `pop` | tamaño de muestra; `pop` = LV, RV o A |
| `D`, `R` | % Bottoms y % Jackson |
| `tipo_pregunta` | `general`, `dos_opciones` o `reasignacion` |
| `fuente` | URL de la fuente |
| `version`, `notas` | opcionales |

- **Senado:** mismo formato en `datos/ga_sen2026_encuestas.csv` (D = Ossoff, R = Collins).
- **Regla para versiones:** si hay varias, usa la de votantes probables (LV) sin reasignar indecisos y sin *leaners*.
- **Validación:** el modelo revisa el archivo antes de calcular y se detiene si encuentra duplicados, fechas inválidas, D+R > 100, tipos desconocidos o claves mal escritas.

## Salidas (`salida/`)
`resumen_escenarios.csv`, `senado_y_conjunto.csv`, `encuestas_senado_corregidas.csv`, `tres_categorias_encuestas.csv`, `encuestas_corregidas.csv`, `metadatos.json`, `simulaciones_muestra.csv`, `historial_pronosticos.csv`, `errores_historicos_GA.csv`, `pronostico_georgia_v11.png`, `cache/`.
