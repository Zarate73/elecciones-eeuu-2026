# California · Backtest M1–M4 + Kalshi (corte 19-oct-2026)

Código y datos: [`../backtest/`](../backtest/) (`python backtest_california.py`). Modelo resultante: [`../modelo_m5/`](../modelo_m5/) y [`../produccion/`](../produccion/).

## Hallazgos
1. **La σ del modelo original estaba subestimada.** Error real − encuestas (margen D−R, agregado mejorado, T−7) en 6 contiendas estatales: GOB2018 +6.6, REV2021 +6.5, GOB2022 −4.9, PRES2024 −5.1, SEN2024 −6.8, PROP2025 +9.0. RMSE 6.6 (T−7) y 6.5 (T−14, n = 4). Con σ = 4.5 quedaba fuera el 50 % de los casos del intervalo del 80 %. La σ empírica LOO gana en CRPS a M1, M3 y M4 (3.91 contra 4.22 / 4.14 / 4.12).
2. **Patrón de signo.** Con presidente republicano (2018, 2025) las encuestas subestimaron al demócrata entre 7 y 9 pp. Con n = 2 es una hipótesis, no una corrección.
3. **M3 y M4 solo ensanchan la varianza.** Su ganancia en CRPS viene de eso, y una σ empírica lo hace mejor. M4 no es evaluable: la serie de sentimiento empieza el 3-jun-2026.
4. **M2 (proxy contra el registro) falla fuera de muestra.** En la primaria las devoluciones tempranas venían sesgadas a R (37 % el 17-may) y el ajuste empujaba hacia Hilton, en la dirección equivocada. Además, el 57 % de las devoluciones de la general 2026 son de mayores de 65 años.
5. **Primaria 2026.** Las encuestas finales ponían a Hilton por encima o igual que Becerra (21.8 contra 21.0). Resultado: Becerra 28.0, Hilton 24.6, Steyer 22.8. En 2018, 2024 y 2026 el líder de cada partido en las encuestas superó su promedio entre 4 y 7 pp.
6. **Conteo (espejismo rojo).** Con el 55 % contado (3-jun): Hilton 27.6, Becerra 25.5. En el voto tardío: Becerra 31.4, Hilton 20.9. Kalshi bajó «Hilton avanza» de 0.88 a 0.54 en dos días y luego cerró en 0.999.
7. **Kalshi en la general.** Becerra 0.954 normalizado (18-oct). Con margen +17.4 eso implica σ ≈ 10.3; con σ = 6.5 el modelo da 0.996. El 4–5 ¢ de Hilton es consistente con el sesgo favorito–longshot.

## Civiq: API pública
Endpoints JSON sin autenticación en `https://abev.civiq.vote/api/` (`historical-elections`, `ballot-returns`, `crosstabs`, `geography-breakdown`). Margen D−R de las devoluciones a T−15: 2022G +18.8, 2024G +18.3, 2026G +19.9. Con 4 elecciones, el Δ frente a las demás elecciones al mismo día correlaciona +0.72 con el error de las encuestas. Es solo diagnóstico (`w_m2 = 0`).

## Producción (21-oct-2026)
- Las encuestas se leen **en vivo** de Wikipedia y 270toWin (mismos parsers que Georgia) y se combinan con la base verificada a mano, sin duplicados.
- La familia de encuestadora se normaliza («Manhattan Institute (R)» = «Manhattan Institute») para deduplicar y conservar la marca partidista.
- **Pendiente de validar:** ActiVote (24-sep a 16-oct, 400 LV, pregunta sin indecisos) recibe el mayor peso porque M5 pondera por fecha y no por tamaño de muestra. Antes de añadir peso por n hay que probarlo en el backtest.
