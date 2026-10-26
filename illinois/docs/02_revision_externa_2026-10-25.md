# Revisión externa del modelo de Illinois (25-oct-2026)

Cambios en `il_pronostico` v1.1.0. Pruebas: `produccion/tests/test_produccion.py` (21 pasan, 1 omitida en CI: la del Excel).

## Resumen
| Observación | Veredicto | Acción |
|---|---|---|
| ActiVote usa cifras redondeadas (59–41; la publicación dice 58.7–41.3) | **Correcta** | `data/correcciones_cifras.csv` y prueba que lo verifica |
| Dependencia de dos encuestas; ActiVote se pondera por el fin de un campo de 21 días | **Correcta**, y más importante de lo que parecía | Escenario con fechas del punto medio. El histórico de FiveThirtyEight fecha por el punto medio: **inconsistencia de calibración que afecta a todos los estados** (sección 2) |
| Sensibilidad del sesgo a contiendas individuales (leave-one-contest-out) | **Correcta** | Calibración nueva: sesgo recalculado sin cada contienda del estado; los dos extremos son escenarios |
| Terceros dependen de una sola encuesta | **Correcta** (sin error de método) | Documentado; los escenarios de reducción ya existían |
| Mezcla con mercados: −2.1 pp en el margen, frente a +20.2 del mercado de rangos | **Correcta** | Se mantiene w = 0.30; queda pendiente validar por separado probabilidad y margen |
| PPP: LV o RV, y «(D)» como firma frente a patrocinio | **Correcta** | Se mantiene LV. PPP ya no cuenta como patrocinio partidista (`firmas_sin_patrocinio_partidista`) |

**Efecto en el pronóstico** (misma captura del 25-oct, misma semilla):

| | v1.0.0 | v1.1.0 |
|---|---|---|
| Promedio corregido | +18.661 | **+18.239** (−0.42, igual al cálculo de la revisión) |
| Margen final | +17.64 | +17.32 |
| P(Pritzker) | 99.5 % | 99.4 % |

## 1. ActiVote
- La revisión verificó en activote.net 58.7–41.3, 400 LV, campo del 2 al 22 de octubre. Desde aquí la página no es accesible, pero 59–41 es exactamente el redondeo de 58.7–41.3, y ActiVote reparte a los indecisos (D + R = 100).
- Pesa 70.3 % del promedio. El cambio aislado (−0.42) coincide con la nueva corrida.

## 2. Fecha de la encuesta: fin o punto medio del campo
- **Hallazgo.** En `raw-polls.csv` de FiveThirtyEight, `polldate` es la **fecha mediana del campo** ("Median field date of the poll", diccionario del conjunto). Esa base aporta el 95 % de las contiendas de la calibración (903 de 945, 1998–2022) y del backtest de la ventana.
- **Producción usa la fecha de fin** para todo:
  - qué encuestas entran a la ventana de 21 días;
  - el peso por antigüedad (vida media de 14 días);
  - la deriva cuando las encuestas son más viejas que el horizonte calibrado.
- **Consecuencia:** cada encuesta se trata como unos días más reciente que en la calibración, la mitad de su campo. En encuestas típicas de 3–5 días son 1–2 días. En ActiVote (21 días) son 10.
- **Las filas de 2024** (Wikipedia, Arizona, Georgia) usan el fin. Son las 42 contiendas restantes.
- **Escenario nuevo en Illinois:** «Fechas por el punto medio del campo».
  - ActiVote pasa al 12-oct y PPP al 30-sep/1-oct; la ventana se amplía desde el 21-sep con las dos encuestas.
  - El peso de PPP sube y la deriva pasa de 3 a 13 días.
  - Margen sin mercados +19.56 (contra +19.42); con mercados +17.36 (contra +17.32). P(Pritzker) 99.4 % en ambos casos.
  - **En Illinois el efecto es mínimo.**
- **Decisión:** no se cambia la regla publicada solo en Illinois. Es una regla de todos los estados y cambiarla movería sus pronósticos.
- **Recomendación:** fechar por el punto medio en todos los estados, que es lo consistente con la calibración, y medir el movimiento de cada pronóstico antes de adoptarlo.

## 3. Sesgo estatal sin cada contienda (leave-one-contest-out)
Recalibración completa (incluida la contracción) quitando cada una de las 19 contiendas de Illinois:

| Contienda que se quita | Sesgo bruto | Corrección al margen |
|---|---|---|
| Ninguna (producción) | −1.60 | **+1.20** |
| Presidente 2020 (la de más influencia) | −0.82 | +0.59 |
| Senado 2022 | −1.34 | +0.97 |
| Senado 2008 | −1.32 | +1.07 |
| Gobernador 2022 | −2.17 | +1.59 |

- **Rango: +0.59 a +1.59 pp.** El signo no cambia con ninguna contienda.
- Margen sin mercados: 18.84 a 19.83. P(Pritzker) con mercados: 99.4–99.5 %.
- **Ninguna contienda individual cambia el pronóstico de forma material.** Los dos extremos quedan como escenarios («Sesgo sin la contienda …»).
- No se excluyen observaciones atípicas.

## 4. Terceros
- T = 0.798 + 0.729 · 6 = 5.18 %.
- El 6 % viene solo de PPP: ActiVote es un careo de dos candidatos y cuenta como «no reportado», no como 0.
- La incertidumbre real de los terceros es mayor que la residual histórica (σ ≈ 1.7). Los escenarios de reducción (3.4 % y 2.1 %) la cubren y no cambian al ganador.

## 5. Mercados
- Con probabilidades cercanas a 1, trasladar la mezcla de probabilidades al margen no es único:

| Lectura | Margen |
|---|---|
| Sin mercados | +19.4 |
| Mezcla con precios de ganador (publicada) | +17.3 |
| Rangos de Polymarket | +20.2 |

- Se mantiene w = 0.30, validado para la probabilidad en 40 contiendas de 2024, incluidas las de mercados extremos.
- Queda pendiente, para todos los estados, validar por separado el uso de mercados para la probabilidad y para el margen.

## 6. PPP
- **Cifras:** 54–34, Corbett 6, indecisos 6, n = 569, corroboradas por Chicago News Weekly.
- **Población:** Wikipedia la da como LV; 270toWin, como RV; la nota de prensa dice «569 votantes». Se mantiene LV con la fuente anotada (Wikipedia). Para resolverlo haría falta la ficha metodológica de PPP.
- **Firma partidista ≠ patrocinio partidista.** El «(D)» de Wikipedia marca la inclinación de la firma. El efecto de casa de PPP ya la captura: +0.85 pp, estimado con su historial.
  - El backtest de las variantes partidistas (P1–P3) usa la columna `partisan` de FiveThirtyEight, que marca el **patrocinio**.
  - Por consistencia, `firmas_sin_patrocinio_partidista = ["publicpolicypo"]` excluye a PPP de los ajustes y escenarios partidistas.
  - No cambia el pronóstico; solo deja de existir el escenario «sin encuestas partidistas», que no aplica.

## 7. Segunda revisión: disponibilidad de las encuestas en el backtest
### 7.1 Riesgo de fuga temporal — **correcto; cuantificado**
- **El riesgo.** El backtest toma las encuestas con días_mediana ≥ H. Una encuesta cuya mediana cae antes del corte puede terminar o publicarse después, y no habría estado disponible.
- **No se puede medir directamente:** el histórico no trae fechas de cierre ni de publicación.
- **Prueba** (`backtest/revision_disponibilidad_illinois.py`): regla conservadora «disponible si mediana + L ≤ corte», con L = 0 (actual), 2, 4 y 7 días; misma ventana superior de 21 días. Se repiten el LOYO y el cronológico y se comparan las contiendas presentes con todas las L.

| L (días) | Contiendas | CRPS G, LOYO (comunes, n = 653) | G − H8, LOYO | CRPS G, cronológico (comunes, n = 525) | G − H8, cronológico | σ media (LOYO, comunes) |
|---|---|---|---|---|---|---|
| 0 (actual) | 945 | 2.987 | −0.084 | 2.784 | −0.183 | 5.63 |
| 2 | 901 | 3.109 | −0.077 | 2.894 | −0.186 | 5.81 |
| 4 | 819 | 3.244 | −0.052 | 3.035 | −0.146 | 6.00 |
| 7 | 653 | 3.478 | −0.050 | 3.296 | −0.090 | 6.38 |

- **Las decisiones del modelo no cambian con ningún L:**
  - el sesgo contraído gana a «sin sesgo» a nivel nacional en LOYO y en el cronológico;
  - el reparto proporcional de indecisos (H2) es siempre el peor;
  - en Illinois «sin sesgo» sigue algo mejor en las contiendas comunes, igual que con L = 0, y la decisión se sigue tomando con la evidencia nacional.
- **Los niveles sí cambian.** Con más retraso hay menos encuestas y más viejas, y el CRPS sube. La prueba no separa cuánto es fuga eliminada y cuánto es información perdida, pero da una cota.
- **Producción usa la fecha de fin ≤ corte**, que equivale a L ≈ la mitad del campo (1–2 días en una encuesta típica). Lo comparable es L ≈ 2. Ahí la σ recalibrada es ~3 % mayor (5.63 → 5.81) y la cobertura del 80 % se mantiene en 0.79–0.80.
- **Conclusión:** los CRPS de L = 0 son algo optimistas en nivel, pero el orden de los modelos no depende de la fuga. La σ de producción podría estar ~2–3 % corta. En Illinois no cambia nada material: P(Pritzker) ≥ 99 % con cualquier σ razonable.
- **Recomendación** (decisión transversal, no solo de IL), junto con la de fechar por el punto medio (sección 2):
  - calibrar con una disponibilidad L = 2 (horizonte de calibración h + 2);
  - medir el movimiento de cada estado antes de adoptarlo.

### 7.2 Ventanas históricas frente a producción — **correcto**
- Una ventana de 21 días por mediana y otra de 21 días por fin no contienen las mismas encuestas.
- Es la misma inconsistencia de la sección 2 y se resuelve con la misma decisión transversal: fechar producción por el punto medio y calibrar con disponibilidad L.

### 7.3 Prueba de escala: validación anidada — **correcto; no cambia la conclusión**
- La capa de escala (actual = a + b·μ) se ajustó sobre predicciones LOYO de los años de entrenamiento. Esas predicciones se generaron con modelos que sí vieron el año de prueba, así que hay dependencia entre folds.
- **El sesgo de esa dependencia favorece a la variante con escala:** ajusta mejor de lo que debería. Aun así perdió (P = 0.25 nacional, 0.13 en ventajas ≥ 15 pp), con b = 1.00.
- Una validación anidada solo podría empeorarla. Se mantiene el descarte. El método queda anotado para cualquier capa de corrección futura.
