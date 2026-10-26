# Revisión externa del modelo de Nueva York (26-oct-2026)

Cambios en `ny_pronostico` v1.1.0. Pruebas: `produccion/tests/test_produccion.py` (30 pasan; en CI se omite 1, la del Excel).

## Resumen
| Observación | Veredicto | Acción |
|---|---|---|
| Falta OnMessage (R) 12–14 oct (1,000 LV, 50.3–45.9, pagada por la campaña de Saritha Komatireddy) y entraría en la ventana | **Correcta.** No está en Wikipedia ni en 270toWin; Ballotpedia y OnPoint sí la registran | Se agrega desde `data/encuestas_complementarias_ny.csv`. Entra a la ventana como encuesta de patrocinio R |
| No debe fusionarse con la OnMessage 1–6 oct (50–46) | **Correcta, y el código las fundía** | La deduplicación las trataba como la misma encuesta (ver §2); corregido |
| Falta Pollfinity 8–12 oct (499 RV), fuera de la ventana por un día | **Correcta** | Se agrega a las complementarias; entra en los escenarios de ventana ampliada |
| Quinnipiac: 2 % no sabe + 2 % rechazó, no 2 % de terceros | **Correcta** (también en septiembre: 2 + 1) | `correcciones_cifras.csv` ahora corrige también `otros` e `indecisos`; no cambia el margen |
| Con k = 3, la σ baja por el término s²/k: hay que repetir la simulación completa | **Correcta** | Se repitió el pronóstico completo; la σ pasa de 6.55 a 5.74 |
| ActiVote (1–23 oct) se pondera por su fecha de cierre | Correcto como descripción | Es la regla de producción en todos los estados; el escenario «fechas por el punto medio del campo» la evalúa |

## 1. Encuestas complementarias
- **`data/encuestas_complementarias_ny.csv`:** encuestas verificadas en la publicación original que no traen Wikipedia, 270toWin ni el Excel. Tiene las mismas columnas que la base verificada, más la URL de la fuente y una nota. El Excel no se modifica.
- **OnMessage Inc. (R), 12–14 oct:** 1,000 LV, Hochul 50.3 – Blakeman 45.9, «no sabe» 3.8. Publicada el 20-oct. La pagó la campaña de Komatireddy (R), así que lleva la marca «(R)» y cuenta como partidista en los escenarios. En el promedio usa el efecto de casa histórico de OnMessage (−2.63): margen corregido +7.03.
- **Pollfinity Research, 8–12 oct:** 499 RV, 47 – 44 (otros 3, indecisos 6) en la boleta completa; 48 – 47 cara a cara. Publicada el 13-oct. Sin patrocinador; Pollfinity es propiedad de Lars Mapstead. Se usa la boleta completa, la cifra principal que publica la firma.
- **Si Wikipedia las agrega después:** se reconocen por el periodo de campo como la misma encuesta y se conservan los decimales.

## 2. Error en la deduplicación
- **Qué pasaba.** Las dos OnMessage tienen n = 1,000 LV y cifras casi iguales (50–46 contra 50.3–45.9). Dos reglas de `combinar` las fundían, aunque los periodos no se tocan:
  - «mismas cifras entre fuentes distintas a ≤ 60 días = fecha mal capturada»;
  - «mismo n ≥ 300 y mismas cifras a ≤ 30 días», creada para el «YouGov» que 270toWin rotula distinto.

  Al fundirse se perdía la encuesta del 12–14 oct y la del 1–6 oct heredaba sus decimales.
- **Corrección.** Esas dos reglas ya no aplican cuando una de las encuestas viene del archivo complementario: sus fechas están verificadas en la publicación original. Las demás reglas no cambian, así que Wikipedia, 270toWin y el Excel se combinan como antes.
- **Otros estados.** Sus paquetes tienen las mismas reglas, pero no tienen archivo complementario. El riesgo de fundir dos encuestas de la misma firma con cifras y n iguales sigue latente, igual que el de la regla de 7 días antes de la revisión de Texas.

## 3. Quinnipiac
- **Octubre:** Wikipedia publica 55 – 41 con «otros 2 · indecisos 2»; el cuestionario dice 2 % no sabe y 2 % rechazó. Queda otros 0, sin preferencia 4.
- **Septiembre:** 58 – 39 con 2 % no sabe y 1 % rechazó. Queda otros 0, sin preferencia 3.
- **Efecto:** D y R no cambian. Nueva York fija los votos por escrito en 0.15 % y reparte a los indecisos 50/50, así que el margen tampoco cambia (comprobado: promedio +15.535 antes y después de esta corrección sola).

## 4. Efecto en el pronóstico
Misma captura (corte 25-oct), misma semilla, 200,000 simulaciones:

| | v1.0.1 | v1.1.0 |
|---|---|---|
| Encuestas combinadas | 23 | 25 |
| En la ventana | Quinnipiac 58.4 % · ActiVote 41.6 % | Quinnipiac 41.0 % · OnMessage 29.7 % · ActiVote 29.3 % |
| Promedio corregido D−R | +15.54 | **+13.01** (−2.52, igual al cálculo de la revisión) |
| Sesgo estatal | −1.95 | −1.95 |
| Mercados | −0.84 | −0.50 |
| Margen final (σ) | +12.75 (6.55) | **+10.57 (5.74)** |
| IC80 del margen | +4.5 a +21.0 | +3.3 a +17.8 |
| Hochul / Blakeman | 56.3 / 43.5 | 55.2 / 44.6 |
| P(Hochul), solo encuestas | 98.0 % | 97.2 % |
| P(Hochul), final | 97.3 % | **96.7 %** |

- **σ:** baja porque k pasa de 2 a 3 (término s²/k). Con k efectivo 2.9 sale 5.80 (escenario «Incertidumbre con k efectivo»).
- **El margen baja más que la probabilidad:** la σ menor compensa el menor margen. En los mercados, el tirón logit hacia ~95 % pesa menos.
- **Escenarios de influencia:**
  - sin OnMessage: +13.6, P 98.0 %;
  - sin ActiVote: +8.8, P 91.4 %;
  - sin Quinnipiac: +10.8, P 95.1 %.

  La ventana sigue concentrada en tres encuestas, una de ellas partidista.
- **Sin encuestas de patrocinio partidista:** +13.6, P 98.0 %. Es el escenario que excluye a OnMessage por regla, no a mano.
