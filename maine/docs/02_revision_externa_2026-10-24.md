# Revisión externa del modelo de Maine (24-oct-2026)

Pruebas: [`backtest/revision_maine.py`](../backtest/revision_maine.py) (resultados en `backtest/salida/revision_*.csv`). Cambios en `me_pronostico` v1.1.0.

## Resumen
| Observación | Veredicto | Acción |
|---|---|---|
| Ventana ampliada: el 65 % del peso tiene más de 21 días y el backtest no valida ese régimen | **Correcta** | Emulación del régimen en el backtest. Ampliar es mejor que no ampliar; k efectivo y deriva ponderada apenas cambian el error: quedan como escenario |
| Independiente: P(D > R) no es P(gana D) en una elección a tres; D/(D+R) de los mercados es condicional | **Correcta** | P(gana) a tres bandas, cota de P(gana un tercero) en el modelo y probabilidades de Bennett de los mercados (Kalshi y Polymarket), todo en el reporte |
| La regla k ≥ 2 solo se validó en LOYO, no en cronológico | **Correcta** | Validación cronológica de las tres reglas: k ≥ 2 sigue siendo la mejor en Maine |
| Corregir Axis Research (ME-02) en todos los estados y medir el efecto | **Correcta** | Corrección en FL, NV y PA; recalibración, pruebas actualizadas y movimiento de los pronósticos medido |
| La normal del mercado de márgenes es condicional a que gane un partido principal | **Correcta** | Rotulada así en el reporte, en el escenario y en el código; sigue como diagnóstico |

**El pronóstico de Maine no cambia:** P(Pingree) 95.4 % y margen +8.1 en la corrida en vivo de las 03:20 ET.

## 1. Ventana ampliada
**El problema.** Hoy en Maine hay una sola encuestadora en los últimos 21 días: Beacon/Shaw, que pesa 35 %. Por eso la ventana se amplía a los 21 días previos a esa encuesta.
- El 65 % del peso tiene entre 23 y 34 días.
- k pasa de 1 a 6, lo que reduce s²/k.
- El backtest ordinario solo usa encuestas de 10 a 21 días, así que no valida ese régimen.

**Límite de los datos.** FiveThirtyEight solo publica las encuestas de los últimos 21 días antes de cada elección. El régimen no se puede reproducir a escala real; se emuló a escala 9/21:
- ventana nominal de 3 a 9 días;
- con menos de 2 encuestadoras, se amplía a los 9 días previos a la más reciente.

Resultado: 274 de 1,023 contiendas se amplían; 113 tienen además alguna encuesta en la ventana nominal.

| Variante (en las 113 contiendas ampliadas) | CRPS | Cob80 | Cob95 | σ media | P(mejor que A1) |
|---|---|---|---|---|---|
| A0 · sin ampliar (solo la encuesta nominal) | 3.670 | 0.83 | 0.97 | 7.27 | 0.12 |
| **A1 · producción** (k = firmas, deriva de la más reciente) | **3.397** | 0.76 | 0.95 | 5.63 | — |
| A2 · k efectivo por firma 1/Σ_f W_f² | 3.394 | 0.77 | 0.95 | 5.69 | 0.67 |
| A3 · deriva por antigüedad ponderada | 3.397 | 0.76 | 0.96 | 5.65 | 0.67 |
| A4 · A2 + A3 | 3.394 | 0.77 | 0.95 | 5.71 | 0.69 |

- **Ampliar es mejor que no ampliar:** la ganancia es de 0.27 en CRPS. Las encuestas viejas sí informan.
- **En el régimen ampliado, la cobertura del 80 % es 0.76**, un poco corta. El k efectivo por firma la sube a 0.77, pero apenas cambia el CRPS (3.394 contra 3.397; P = 0.67; en todas las contiendas, 0.61). La deriva ponderada no cambia nada.
- **Corrección posterior (k efectivo por firma).** La primera versión calculaba 1/Σw² sobre encuestas, así que contaba como independientes las encuestas repetidas de una misma firma y podía superar a k: en las contiendas sin ampliar daba 4.085 contra 4.072 firmas. Ahora se suman primero los pesos de cada firma (W_f = Σ w de sus encuestas) y k_ef = 1/Σ_f W_f², con 1 ≤ k_ef ≤ k. Con esa corrección la ventaja aparente bajó (P de 0.74 a 0.67): parte venía de contar de más. El escenario de producción usa la misma fórmula; hoy coincide con la anterior (seis encuestas de seis firmas): 4.8.
- **Decisión:** no se cambia la σ publicada. Se agrega el escenario «Incertidumbre con k efectivo 4.8 (no 6 firmas) y deriva por antigüedad ponderada (14 días)»: σ 5.12 en lugar de 4.79, y P(Pingree) 94.7 % en lugar de 95.3 %. Es candidato a regla transversal si otro estado lo confirma.
- **La emulación tiene un límite:** en ella el k efectivo por firma es 2.45 contra 2.61 firmas. En Maine hoy la diferencia es mayor (4.8 contra 6), así que el efecto real puede ser algo mayor que el medido.

## 2. Independiente y probabilidad de ganar
- **El modelo simula el margen D−R y el total de terceros (T)** = Bennett + otros. «Ganar» con mayoría simple exige D > R **y** D > Bennett.
- **Ahora el reporte trae:**
  - P(D gana) = P(D > R y D > T): 95.3 %, igual a P(D > R);
  - una **cota superior** de P(gana un tercero) = P(T > máx(D, R)): 0.00 %;
  - **Kalshi Bennett** (`GOVPARTYME-26-RBEN`): 2 %;
  - **Polymarket «gana un independiente»:** 2.9 %.
- **La probabilidad de mercados que entra a la mezcla** es D / (D + R), condicional a que gane un partido principal; el reporte lo dice.
- **Por qué no se modela a Bennett por separado:** con 6–11 % en todas las encuestas, la distancia hasta el primer lugar (~40 pp) está muy lejos del error histórico. El 2–3 % de los mercados es coherente con el sesgo favorito–longshot en mercados poco líquidos (Polymarket: ~$7.6 mil y precios que suman 1.22). Se reporta, pero no entra al pronóstico.
- **Límite del backtest:** las contiendas donde un independiente terminó segundo (King, Cutler 2010) no son D contra R y no están en el backtest.

## 3. Sesgo estatal: validación cronológica de la regla
| Ámbito (2004–2024) | n | G todas | G k ≥ 2 | Sin sesgo | P(k ≥ 2 mejor que todas) |
|---|---|---|---|---|---|
| Nacional | 739 | 3.211 | 3.210 | 3.434 | 0.51 |
| Gobernadores | 211 | 3.221 | 3.230 | 3.317 | 0.37 |
| **Maine** | 9 | 2.834 | **2.797** | 3.265 | 1.00 |
| Maine gobernador | 1 | 1.824 | 1.810 | 2.067 | — |

- **En Maine, k ≥ 2 también gana en el cronológico** (en LOYO: 3.260 contra 3.322).
- **A nivel nacional, en el cronológico las dos reglas empatan,** y en gobernadores k ≥ 2 queda apenas atrás. No hay base para cambiar GA, FL, NV ni PA: se queda solo en Maine.
- **Solo 1 de las 9 contiendas cronológicas de Maine es de gobernador.** La evidencia del estado no basta para un ajuste específico de gobernador; el sesgo se estima con todas las contiendas del estado de k ≥ 2.
- **La regla k ≥ 2 ya era inmune al error de Axis Research:** esa contienda de Maine 2024 tenía una sola encuestadora. Con o sin la fila, el pronóstico es +8.05 y 95.4 %.

## 4. Corrección del histórico 2024 (Axis Research, distrito 2 de Maine) en todos los estados
Se quitó la fila en las copias de Florida, Nevada y Pennsylvania (backtest y producción). Georgia, Arizona y California no usan ese archivo.

**Efecto aislado.** Misma captura de fuentes, misma semilla y 200,000 simulaciones; solo cambia el dato:

| Estado (corte de la captura) | P(D) antes → después | Margen antes → después | % D | % R | τ, s, ν | Sesgo aplicado |
|---|---|---|---|---|---|---|
| Florida (22-oct) | 5.00 → 5.09 % | −8.31 → −8.27 | 44.79 → 44.81 | 53.10 → 53.08 | 3.4, 7.6, 13.4 → 13.1 | 4.83 → 4.75 |
| Nevada (22-oct) | 41.86 → 41.93 % | −1.24 → −1.22 | 45.33 → 45.31 | 46.57 → 46.54 | 3.4, 7.6, 13.4 → 13.1 | 0.58 → 0.56 |
| Pennsylvania (23-oct) | 99.67 → 99.66 % | +18.84 → +18.84 | 58.35 → 58.35 | 39.51 → 39.51 | 3.55, 7.7, 17.9 → 17.5 | 1.049 → 1.045 |
| Maine, regla «todas» (24-oct) | 98.35 → 92.82 % | +10.35 → +6.94 | 51.79 → 50.07 | 41.44 → 43.13 | 3.5, 7.9, 26.9 → 3.55, 7.8, 25.6 | −0.86 → +4.03 |
| **Maine, regla k ≥ 2 (producción)** | 95.37 → 95.35 % | +8.05 → +8.05 | 50.64 → 50.62 | 42.59 → 42.58 | 3.5, 7.9, 26.9 → 3.55, 7.8, 25.6 | 2.42 → 2.43 |

- **En FL, NV y PA el efecto es de centésimas:** la fila solo entraba en la calibración nacional (ν y la varianza entre estados de la contracción del sesgo).
- **En Maine era decisivo** con la regla «todas»: volteaba el signo del sesgo. Con la regla k ≥ 2 de producción, no.

**Pronósticos publicados.** Corridas en vivo después de la corrección; incluyen también las encuestas y precios nuevos del día:

| Estado | Antes (último publicado) | Después (24-oct, en vivo) |
|---|---|---|
| Florida | 4.69 %, margen −8.24 (23-oct) | 4.86 %, −8.24 |
| Nevada | 42.27 %, −1.22 (23-oct) | 41.69 %, −1.35 (el sesgo aplicado sube a 0.81 porque cambia el horizonte: 11 días en lugar de 12) |
| Pennsylvania | 99.67 %, +18.84 (23-oct) | 99.69 %, +18.96 |
| Maine | 95.37 %, +8.06 (v1.0.0, 02:49 ET) | 95.38 %, +8.07 (v1.1.0) |

## 5. Mercado de márgenes
- La normal se ajusta a los 8 rangos D/R; el contrato «gana un independiente» queda fuera del eje D−R. Por eso **es condicional a que gane un partido principal**, y así se rotula en el reporte y en el escenario.
- P(D) de los contratos sí incluye al independiente en el denominador.
- Sigue como diagnóstico; no resume toda la incertidumbre.

## 6. Hallazgo adicional en la automatización (no estaba en las observaciones)
Al relanzar a la vez los flujos de FL, NV, PA y ME aparecieron dos fallas de la publicación automática.

1. **Corridas canceladas por compartir un grupo de concurrencia** (`pronostico-repo`).
   - GitHub solo admite una corrida pendiente por grupo y cancela la anterior: Nevada y Pennsylvania quedaron canceladas.
   - Con los horarios escalonados casi no pasaba, pero un retraso de GitHub podía saltarse una actualización.
   - **Arreglo:** un grupo por estado.
2. **`publicar.sh` fallaba al reintentar.**
   - Con corridas en paralelo, el push de Nevada fue rechazado y en el reintento falló `git stash pop` tras el reset.
   - **Arreglo:** sin stash. Los archivos del estado se copian aparte y se reponen sobre la última versión de main en cada intento.
   - Se probó con dos publicaciones simultáneas.

Fuentes: Secretaría de Estado de Maine (mayoría simple en la general de gobernador) · Kalshi `GOVPARTYME-26` · Polymarket `maine-governor-margin-of-victory-2026`.
