# Revisión externa del modelo de Texas (25-oct-2026)

Cambios en `tx_pronostico` v1.1.0. Pruebas: `produccion/tests/test_produccion.py` (24 pasan, 1 omitida en CI: la del Excel).

## Resumen
| Observación | Veredicto | Acción |
|---|---|---|
| Se perdía la segunda encuesta de ActiVote (17–21 oct) al combinar | **Correcta** | La identidad de una encuesta pasa a ser firma + periodo de campo |
| Guardar las cifras originales de ActiVote (47.5–52.5, no 48–53) | **Correcta**; el margen no cambia (−5 en ambos casos) | `data/correcciones_cifras.csv` |
| Verasight/VoteHub: el 23-oct de 270toWin es fecha de publicación, no de campo | **Correcta**; ya se deduplicaba | Se formaliza en la regla; se conserva el periodo de campo (1–20 oct) |
| Usar periodo de campo e identificador de estudio, no solo firma y cercanía de fechas | **Correcta** en lo primero | Periodo de campo implementado. Ninguna fuente publica un identificador de estudio |
| Advertencia de pandas en `encuestas.py` (rellenar float64 con texto) | **Correcta** | `nota_version` se convierte a object antes de rellenar; las pruebas corren sin FutureWarning |
| Zona horaria: America/Chicago en `texas.toml` y en el flujo | **Correcta** | Fecha del corte, README y commits del flujo en hora del centro |

## 1. ActiVote
- **Causa.** La regla anterior trataba como la misma encuesta dos de la misma firma cuyas fechas de fin estuvieran a ≤ 7 días. Las dos de ActiVote terminan el 14 y el 21 de octubre (7 días), así que la segunda se fundía con la primera. Era un error de combinación: Wikipedia sí traía las dos.
- **Regla nueva** (`combinar`):
  - misma firma y periodos de campo que se solapan o se tocan → misma encuesta (versiones LV/RV, o la misma en dos fuentes);
  - misma firma y periodos distintos, ambos con rango → **encuestas distintas**;
  - una fecha puntual (270toWin: publicación) a ≤ 3 días del periodo de otra, o a ≤ 7 con las mismas cifras → misma encuesta; se conserva el periodo de campo;
  - mismas cifras entre fuentes distintas a ≤ 60 días → misma encuesta con la fecha mal capturada.
- **Identificador de estudio:** Wikipedia, 270toWin y el Excel no lo traen, así que el periodo de campo es la mejor llave disponible.
- **Cifras:** ActiVote reparte a los indecisos, así que D + R = 100. El 48 + 53 = 101 de Wikipedia solo es compatible con 47.5 + 52.5. Se corrige desde `data/correcciones_cifras.csv`. El margen es −5 en ambos casos; cambian solo los porcentajes guardados.

**Efecto** (misma captura del 25-oct, misma semilla, 200,000 simulaciones):

| | Antes (v1.0.0) | Después (v1.1.0) |
|---|---|---|
| Encuestas combinadas | 50 | 51 |
| Encuestas en la ventana / firmas | 9 / 9 | 10 / 9 |
| Promedio corregido D−R | −3.113 | **−3.226** (−0.113, igual al cálculo de la revisión) |
| Margen final | −4.55 | −4.63 |
| P(Hinojosa), solo encuestas | 10.0 % | 9.5 % |
| P(Hinojosa), final | 14.6 % | **14.2 %** |
| Encuesta más reciente | Verasight/VoteHub (20-oct) | ActiVote (21-oct) |

## 2. ¿Pasa en otros estados?
- La regla de ≤ 7 días viene de los paquetes de Arizona, Florida, Nevada, Pennsylvania y Maine y, con otra forma de código, también de Georgia y California (≤ 7 días o mismas cifras a ≤ 21 días).
- Se buscaron, en las cachés actuales de GA, CA, AZ, FL, NV, PA y ME, pares de la misma firma que terminan a ≤ 7 días con periodos de campo que no se solapan. **No hay ninguno:** hoy ningún otro pronóstico pierde encuestas por esta causa.
- El riesgo sigue latente en esos paquetes. Llevar la regla nueva a esos estados no cambiaría sus pronósticos actuales.

## 3. Zona horaria
- `zona_horaria = "America/Chicago"`: casi todo Texas usa la hora del centro. Fija la fecha del corte y la antigüedad de los precios de mercado.
- El README y los mensajes de commit del flujo usan CT.
- El horario del flujo (06:13 y 18:13 CT) no cambia.
