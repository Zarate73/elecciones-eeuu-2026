# Georgia · Investigación + backtest + selección de modelo (corte 19-oct-2026, T−15; actualizado 20-oct)

Código y datos: `georgia/backtest/` (`backtest_georgia.py` → `analisis_complementario.py` → `analisis_indecisos_kalshi.py` → `aplicar_2026.py`).

## Datos
- FiveThirtyEight `pollster-ratings/2023/raw-polls.csv` (GitHub): encuestas de los últimos 21 días de 980 contiendas Gob/Sen/Pres de 1998 a 2022 en todos los estados, 24 de ellas en GA (incluye segundas vueltas 2008, 2021 y 2022).
- Encuestas de GA Presidente 2024 (37, Wikipedia) y resultado certificado.
- 2026: 14 encuestas, incluida la propia G-Ratings del 24–29 sep (Jackson 47.5, Bottoms 45.3).
- **Kalshi `GOVPARTYGA-26`** (D = Bottoms, R = Jackson): velas diarias del 17-jun al 20-oct-2026, ~USD 950k de volumen. Además, `PRESPARTYGA-24` histórico. API pública `trade-api/v2`; `/historical/markets/...` para mercados cerrados.
- Validación leave-one-year-out (LOYO). Cerca del 20% de la varianza del error es común al año.

## Contendientes (verificado 20-oct)
- En la boleta solo están **Bottoms (D) y Jackson (R)**. Chase Oliver (L) se registró en marzo, pero la petición de firmas fracasó (WABE, 10-jul).
- El SOS certificó 7 write-ins para Gobernador (15-sep). Write-ins históricos: 81 votos (2018) y 25 (2022), ≈0.002%. **P(segunda vuelta) ≈ 0.1%**.

## Hallazgos sobre el electorado y las fuentes
1. **Error histórico de las encuestas en GA** (promedio a T−15, D−R): 2014 +4.9/+6.7, 2016 +4.0/0.0, 2018 +0.6, 2020 +1.2/+2.9, 2022 +1.1/−2.2, 2024 +0.3. Tienden a sobrestimar a D, cada vez menos.
2. **Senado en la misma boleta**: Ossoff va unos 9 pp más demócrata que la gubernatura. 2022 tuvo un split parecido y las encuestas lo captaron.
3. **Indecisos**: 50/50 dentro del modelo ganador. Fuera del modelo, el óptimo crudo es 0.59 a R, pero ese efecto ya lo captura el sesgo estatal.
4. **Sentimiento: no entra al modelo** (sin serie histórica para GA; en California M3/M4 solo ensancharon la varianza).

## Backtest a T−15 (CRPS, menor es mejor)
| Modelo | Nacional (701) | GA generales (21) | Cob80 / Cob95 nacional |
|---|---|---|---|
| V9: encuestas + σ con piso de 2 pp | 3.73 | 2.85 | 54% / 72% |
| Encuestas + σ empírica | 3.53 | 2.81 | 80% / 94% |
| + efectos de casa | 3.52 | 2.91 | 80% / 95% |
| + fundamentales (β≈0.09) | 3.48 | 2.73 | 79% / 94% |
| **+ casa + sesgo GA (solo pasado, vida media 4 años) ★** | **3.455** | 2.78 | 81% / 95% |

Bootstrap por año: frente a V9, P(mejor) = 0.999; frente a encuestas + σ empírica, P(mejor) = 0.90.

**Indecisos dentro de ★:**
| Regla | CRPS nacional | CRPS GA |
|---|---|---|
| 50/50 | 3.455 | 2.783 |
| s ajustado LOYO (0.545 a R) | 3.489 | 2.844 |
| s = 0.436 (V9) | 3.545 | 2.837 |

## Kalshi
- 20-oct: P(Bottoms) normalizada = 0.49; trayectoria 0.43 (jun) → 0.62 (ago) → 0.45 (8–14 oct) → 0.49.
- Sin validación posible (mercado desde 2025; GA-2024 n=1). Uso: mezcla logit w=0.30, igual que California M5.

## Siguientes pasos
- Usar el σ(k) empírico como estándar para los 14 estados.
- Validar el peso de Kalshi con los mercados estatales de 2024.
