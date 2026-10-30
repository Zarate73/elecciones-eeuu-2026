# California 2026 · Gobernador

Elección general del 3 de noviembre de 2026 entre **Xavier Becerra (D)** y **Steve Hilton (R)**, los dos primeros de la primaria *top-two* del 2 de junio.

<!-- PRONOSTICO:INICIO -->
**Pronóstico al 2026-10-30** (4 días a la elección) · actualizado automáticamente 2026-10-30 11:04 PT · fuentes en vivo 7/7

| Gobernador | % de voto (IC80) | Probabilidad de ganar |
|---|---|---|
| Xavier **Becerra** (D) | **61.5%** (57.8–65.1) | **99.4%** |
| Steve **Hilton** (R) | **38.5%** (34.9–42.2) | **0.6%** |

Margen D−R +22.9 pp (σ 6.4) · solo modelo: P(Becerra) 99.7% · Kalshi 96.9% (peso 0.30) · 19 encuestas (17 wikipedia, 2 base) · promedio M5 +23.0

**Encuesta más reciente:** Berkeley IGS, terminó el 2026-10-25 (**5 días** antes del corte). Las fuentes se consultan en vivo, pero el promedio solo puede ser tan reciente como la última encuesta publicada.

**Voto anticipado (Civiq, diagnóstico):** boletas devueltas D−R +22.4 a T−5 contra 2022 General +21.4, 2024 General +18.8 al mismo día.

![Pronóstico](produccion/salidas/ultimo/pronostico_porcentajes.png)

![Evolución](produccion/salidas/evolucion.png)

Detalle: [`resumen.txt`](produccion/salidas/ultimo/resumen.txt) · [encuestas y pesos](produccion/salidas/ultimo/encuestas_pesos.csv) · [M5 frente a M1–M4](produccion/salidas/ultimo/comparacion_modelos.csv) · [historial](produccion/salidas/historial_pronosticos.csv)
<!-- PRONOSTICO:FIN -->

GitHub Actions actualiza el bloque anterior dos veces al día ([flujo](../.github/workflows/pronostico_california.yml)).

## Modelo M5 (híbrido)
M5 toma de cada versión anterior (M1–M4) solo lo que el backtest respalda:

| Pieza | Cómo entra | Por qué |
|---|---|---|
| Promedio de encuestas | vida media de 30 días; cada encuestadora cuenta ~1 vez (peso / √n); encuestas de campaña o partidistas a 0.5 | M1 corregido |
| σ | sistemática calibrada con el error histórico de las encuestas en California (2018–2025, RMSE ≈ 6.4 pp) + muestreo + deriva hasta la elección; colas t (ν = 5) | σ = 4.5 fija dejaba fuera la mitad de los casos al 80 % |
| Kalshi | mezcla logit, peso 0.30; ajusta solo la probabilidad publicada (margen, intervalos y % de voto son los del modelo) | no validado con historia; en Georgia y Arizona, en cambio, la distribución se desplaza hacia el mercado |
| Participación (Civiq) | diagnóstico, peso 0 | falló fuera de muestra en la primaria |
| Sentimiento (GDELT) | diagnóstico, k = 1 | sin serie histórica para validarlo |

## Qué valida y qué no valida el backtest

*Auditoría transversal del 26-oct-2026 (T6). Detalle en [`docs/auditoria_2026-10-26.md`](../docs/auditoria_2026-10-26.md).*

- M5 es una familia distinta del V11. La σ sistemática se calibra con el error histórico de las encuestas en California (2018–2025, RMSE ≈ 6.4 pp). Con tan pocas elecciones, la calibración de colas y la cobertura no se pueden validar con precisión.
- Kalshi (peso 0.30) ajusta **solo la probabilidad publicada**. El margen, los intervalos y el % de voto son los del modelo, así que P(D) final y la distribución del margen no tienen por qué coincidir. En el V11 de los otros estados, en cambio, el mercado desplaza la distribución. No compare las dos familias en una misma tabla sin esta advertencia.
- Identidad de encuestas: módulo común `ca_pronostico/identidad.py` (firma + periodo de campo), igual que en los otros nueve estados.
- Encuestas aisladas: `data/encuestas_excluidas.csv` lista filas de las fuentes web que no son de la general (hoy: Berkeley IGS 29-may 25–21 de 270toWin, la primaria del 2-jun). Se separan antes de combinar y quedan en `salidas/encuestas_excluidas.csv`.

## Carpetas
| Carpeta | Contenido |
|---|---|
| [`produccion/`](produccion/) | Paquete `ca_pronostico`: encuestas en vivo (Wikipedia, 270toWin) sobre una base verificada, Civiq, Kalshi y GDELT; CLI, 19 pruebas sin red y tarea programada de Windows. Ver su README. |
| [`modelo_m5/`](modelo_m5/) | Notebook M5 ejecutado (corte 19-oct-2026), datos y salidas |
| [`backtest/`](backtest/) | Backtest M1–M4 + Kalshi: σ empírica, primarias 2018/2024/2026, conteo de la primaria y mercados |
| [`docs/`](docs/) | Hallazgos del backtest y decisiones del modelo |

No se publica la serie de sentimiento propia (`entrega_sentimiento/`): en producción es opcional y solo de diagnóstico.
