# Revisión externa del modelo de Pennsylvania (23-oct-2026)

Cambios en `pa_pronostico` v1.1.0. Pruebas: `tests/test_produccion.py` (`test_kalshi_y_polymarket_en_vivo`, `test_rangos_incompletos_no_dan_probabilidad`, `test_correccion_n_franklin_marshall`).

## Resumen
| Observación | Veredicto | Acción |
|---|---|---|
| Polymarket por rangos: se descarta el contrato «Republican wins» y P(D) sale 1 por construcción | **Correcta** | Se incluye el contrato. Margen por normal ajustada a la partición completa; E[M \| D] se publica por separado |
| Los precios de los rangos suman 1.147 antes de normalizar | **Correcta** (es microestructura, no un error de cálculo) | Se reporta la suma; la normalización queda declarada como supuesto |
| Documentación con 24.33 y JSON con 20.99 | **Correcta** | Cifras fechadas por captura |
| F&M con n = 600 cuando el LV real es ≈ 433 | **Correcta** | Archivo de correcciones verificadas; los n imputados quedan marcados |

**El pronóstico publicado casi no cambia.** Los rangos son un escenario de diagnóstico, y el n de F&M mueve el promedio de encuestas de +22.30 a +22.40 y el margen final de +18.80 a +18.84; P(Shapiro) sigue en 99.7 %.

## 1. Polymarket por rangos
**El problema.** El evento `pennsylvania-governor-margin-of-victory-2026` tiene ocho contratos activos: siete rangos del margen demócrata (0–5, …, 25–30, «30 % o más») y uno sin rango, «Will the Republican Party candidate win…?». La expresión regular solo reconocía contratos con «by X%», así que descartaba el octavo. Con siete intervalos positivos, `P_D = Σ p̃(desde ≥ 0) = 1` por construcción, y la «media» publicada era en realidad E[M | D]. En NV, FL y AZ el problema no existe: sus eventos tienen rangos de los dos partidos.

**Propuesta recibida.** Separar P(D), tomada del mercado de ganador, de la distribución de M | D, tomada de los rangos positivos. Es correcta, pero tiene dos costos:
- mezcla dos mercados distintos, con precios no sincronizados;
- para el margen incondicional, E[M] = P(D)·E[M|D] + P(R)·E[M|R], sigue haciendo falta un supuesto sobre E[M|R], y el rango abierto «30 % o más» sigue necesitando una cota arbitraria.

**Alternativa adoptada.** El propio evento de rangos es una partición completa de la recta: (−∞, 0) del contrato R y [0, ∞) de los siete rangos D.
1. **P(D) sale de los contratos:** 1 − p̃_R. Usa un solo mercado y es coherente internamente.
2. **El margen incondicional sale de una normal** ajustada por máxima verosimilitud con censura por intervalos: max Σ p̃ᵢ · log[Φ((hastaᵢ − μ)/σ) − Φ((desdeᵢ − μ)/σ)]. Los intervalos abiertos entran tal como son; no hace falta suponer E[M|R] ni inventar una cota para «30 % o más».
3. **E[M | D] se publica aparte** (`margen_cond_D`), con los rangos positivos renormalizados. Es el objeto que pedía la observación.
4. **Control:** Φ(μ/σ) debe parecerse a la P(D) de los contratos. Si la partición no está completa (falta el contrato del lado perdedor), no se publica P(D) ni el margen incondicional, solo E[M | D].

| Captura (23-oct) | Contratos | Σ precios | P(D) contratos | Normal: μ (σ) | Φ(μ/σ) | E[M \| D] |
|---|---|---|---|---|---|---|
| Mañana (fixture de las pruebas) | 8 | 0.923 | 97.3 % | +23.9 (9.6) | 99.3 % | +24.3 |
| 16:34 ET (corrida de GitHub; R no guardado) | 7 | 1.147 | — (incompleta) | — | — | +21.0 |
| 16:34 ET con R ≈ 0.0245 (reconstrucción) | 8 | 1.172 | 97.9 % | +20.7 (10.7) | 97.4 % | +21.0 |

- La P(D) de los contratos (97–98 %) coincide con el mercado de ganador (97.7 %). Antes era 100 %.
- En la captura de la mañana la normal da 99.3 % contra 97.3 % de los contratos. La masa de 0–15 pp es baja y la de R es 2.7 %: la distribución del mercado no es normal (tiene cola izquierda). Por eso la probabilidad del escenario sale de los contratos y la normal solo resume el margen.
- **Suma de precios ≠ 1** (0.92 a 1.17). En los rangos bajos los diferenciales bid/ask son anchos (0.004–0.045) y cotizan poco. La normalización proporcional da una distribución, no garantiza que esté calibrada. La suma se reporta en `resumen.txt` y en el JSON (`suma_precios`). Alternativas como el método de Shin o el de potencia no se justifican para un escenario de diagnóstico.
- **24.33 contra 20.99:** las dos cifras son E[M | D] de capturas distintas del 23-oct (mañana y 16:34 ET). Ahora la documentación fecha cada cifra.

## 2. Tamaño de muestra de Franklin & Marshall
- **El problema.** En F&M, oct-2026, la muestra completa es de 808 votantes registrados (±4.1 con efecto de diseño), pero el 59–36 corresponde a votantes probables, con ±5.6.
  - Wikipedia comparte la celda «808 (RV)» entre las filas RV y LV, y 270toWin dice «Sample size not reported».
  - El lector de 270toWin rellenaba el faltante con 600 sin marcarlo, así que parecía un dato reportado.
- **El n de la versión LV, con el mismo efecto de diseño:**
  - deff = 808·(0.041/0.98)² ≈ 1.41;
  - n_LV = 0.25·deff·(1.96/0.056)² ≈ **433**.
  - Coincide con lo que reporta PoliticsPA.
- **Acción:**
  - `data/correcciones_tamano_muestra.csv` (clave, fin, población, n, fuente) aplica tamaños verificados por versión (LV/RV) y deja la fuente en la columna `n_fuente`.
  - El lector web ya no imputa. `encuestas.py` corrige, o imputa 600 (el mismo valor que la calibración histórica) y lo marca en `n_imputado`; si un n imputado entra a la ventana, `resumen.txt` lo dice.
- **Impacto** (peso ∝ √n):
  - F&M pasa de 51 % a ≈ 47 % del peso frente a ActiVote.
  - Promedio de encuestas: +22.30 → +22.40.
  - Margen final: +18.80 → +18.84.
  - Es pequeño porque las dos encuestas dan +23 en bruto y solo difieren en su efecto de casa (F&M +1.8, ActiVote −0.5).

Fuentes: [F&M Poll, octubre 2026](https://www.fandmpoll.org/franklin-marshall-college-poll-release-october-2026/) · [PoliticsPA](https://politicspa.com/fm-poll/154375/) · Polymarket `pennsylvania-governor-margin-of-victory-2026`.
