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
