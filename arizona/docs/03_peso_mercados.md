# Peso de los mercados: estimación por máxima verosimilitud (21-oct-2026)

Código: [`../backtest/peso_mercados.py`](../backtest/peso_mercados.py). Datos procesados: `../backtest/data/mercados_2024/`. Resultados: `../backtest/salida/peso_mercados_*.csv`.

## Pregunta
El pronóstico mezcla la probabilidad de las encuestas con la de los mercados (Kalshi y Polymarket):

```
P_w = logit⁻¹((1 − w)·logit P_encuestas + w·logit P_mercado)
```

El margen se desplaza para que P(margen > 0) = P_w. El peso w = 0.30 se fijó sin validar. ¿Qué w dicen los datos?

## Datos
- **Arizona sola:** solo hay 2 contiendas resueltas con mercados (Presidente y Senado 2024). El perfil de verosimilitud es plano: el IC95 de w va de 0 a 1. **Con Arizona sola, w no se puede estimar.**
- **Ampliación:** 40 contiendas de 2024 con encuestas de al menos 2 encuestadoras y precio de mercado 13 días antes de la elección (23-oct-2024):
  - 20 de Presidente por estado;
  - 14 de Senado;
  - 6 de gobernador.
- **Fuentes:**
  - Kalshi: velas diarias; las de gobernador empezaron el 30-oct y por eso faltan.
  - Polymarket: precio diario del mercado «Democrat».
  - Wikipedia: encuestas y resultado oficial.
- **2022 no está disponible:** Polymarket no guarda historial de precios de esos mercados y Kalshi no tenía mercados por estado. Se intentó con tres parámetros distintos y con el registro de operaciones.
- **Modelo de encuestas:** el de producción de Arizona (V11 sin sesgo estatal). Los efectos de casa y τ, s, ν (calibrados a 13 días) salen solo de 1998–2022, así que 2024 queda completamente fuera de muestra.
- **Corrección del 21-oct (revisión externa):** la primera versión calibraba τ, s y ν con el histórico de producción, que incluye 3 contiendas de 2024 (Presidente AZ y GA, Senado AZ) que también están entre las 40 evaluadas. Era fuga de información. Corregido, los parámetros cambian muy poco (τ 3.05 → 3.10, ν 12.7 → 12.4) y las conclusiones no cambian: w de máxima verosimilitud 0.65 (IC95 0.25–1.00), 0.25 con sesgo común libre (IC95 0–0.65).

## Resultados (verosimilitud del margen real)

| Muestra | n | w de máxima verosimilitud | IC95 (razón de verosimilitud) | ΔLL con w = 0.30 | ΔLL con w = 0 |
|---|---|---|---|---|---|
| Todas | 40 | 0.65 | 0.25–1.00 | −1.27 | **−4.53** |
| Presidente | 20 | 1.00 | 0.30–1.00 | −1.88 | −3.32 |
| Senado y gobernador | 20 | 0.50 | 0.05–0.95 | −0.30 | −2.12 |
| **Todas, con sesgo común libre** | 40 | **0.25** | **0.00–0.65** | **−0.03** | −0.58 |

El log score del ganador (que solo usa quién ganó) no discrimina: el IC95 va de 0 a 1.

## Interpretación
1. **Los mercados aportan.** Peso 0 queda fuera del IC95 en la muestra completa: los mercados sí suman información a las encuestas.
2. **Pero en 2024 casi todo lo que aportaron fue el error común del año.** Las encuestas sobreestimaron a los demócratas en casi todos los estados (sesgo medio +3.5 pp) y los mercados lo anticipaban en parte (+1.9 pp). Al dejar libre un sesgo común del año, lo que el mercado aporta contienda por contienda da w = 0.25 (IC95 0–0.65).
3. **No conviene adoptar w = 0.65.** Ese valor está ajustado al error específico de 2024. En un año en que el error de las encuestas vaya en otra dirección, o en que los mercados se equivoquen en la misma dirección (2022, la «ola roja» que no llegó), un peso alto empeoraría el pronóstico. Elegirlo con un solo año sería sobreajustar.
4. **w = 0.30 queda dentro de ambos intervalos.** Frente al óptimo sin año común, su verosimilitud es prácticamente igual (ΔLL −0.03).

## Decisión
**Se mantiene w = 0.30** en Arizona y, por coherencia, en Georgia y California. Ya no es un supuesto sin evidencia: es compatible con los datos y conservador frente al único año disponible. Se revisará después del 3-nov-2026 con esta elección como segundo año.
