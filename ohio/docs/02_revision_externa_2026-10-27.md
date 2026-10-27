# Revisión externa del modelo de Ohio (27-oct-2026)

Cambios en `oh_pronostico` v1.1.0. Pruebas: `produccion/tests/test_produccion.py` (47 pasan; en CI se omite 1, la del Excel). El pronóstico diario no cambia.

| Obs. | Veredicto | Acción |
|---|---|---|
| OH-01 fechas de FiveThirtyEight (mediana) frente a producción (cierre) | Correcta, ya medida en Illinois: las decisiones no cambian y la σ sube 2 % con 2 días de retraso | Tarea transversal después del 3-nov |
| OH-02 LOYO usa años posteriores | Correcta como descripción. El cronológico de OH ya estima efectos de casa, sesgo y σ solo con años anteriores (1.802 vs 2.464); LOYO anidado: 3.3039 → 3.3059 | Walk-forward común después del 3-nov |
| OH-03 k frente a k efectivo | Sin evidencia de subcobertura: 2.954 vs 2.955 (P = 0.61), Cob80 igual | Se queda k; el escenario sigue publicado |
| **OH-04 descripción de la deriva** | **Correcta: era un problema de redacción** | **Corregida** (§1) |
| **OH-05 fuga al reconstruir cortes pasados** | **Confirmada en reconstrucciones** (no en la corrida diaria) | **Resuelta** (§2) |
| OH-06 mezcla con mercados sin validar en el backtest | Correcta, ya conocida | w = 0.30 congelado; snapshots fechados |
| OH-07 concentración en RedBox (33 %) | Descripción correcta; pesa por n = 2,998 y por ser la más reciente | El escenario sin RedBox sigue publicado |

## 1. OH-04: deriva
- **El código:** `var_deriva = 0.25² · d`. Es un paseo aleatorio: la varianza crece linealmente con los días y la desviación estándar adicional crece con √d. Con 3 días suma 0.43 pp en cuadratura, no 0.75.
- **La redacción:** «0.25 pp/día» sugería una deriva lineal de la sd. Ahora dice «0.25 pp por √día» en los README, la configuración y el docstring.
- **Escenario «deriva al doble»:** se renombró a «σ_d = 0.50 pp por √día». La aritmética ya era correcta: cuatro veces la varianza de la deriva.

## 2. OH-05: reconstrucción de cortes pasados
- **Problema reproducido.** Con un corte anterior a hoy (`--corte 2026-10-21`), las fuentes descargadas hoy traían información posterior:
  - el filtro `fin ≤ corte` dejaba entrar a Verasight (campo hasta el 20-oct), que 270toWin registra como publicada el 22-oct;
  - los mercados eran los de hoy (82–83 %), no los del 21-oct (78 %);
  - civicAPI daba el acumulado de hoy.
- **Corrección.** `Config.es_reconstruccion` (corte < hoy en la zona del estado) activa tres reglas:
  - **Encuestas:**
    - cada una lleva `publicacion`, `tipo_fecha` y `disponible_desde`;
    - la publicación sale de 270toWin, que fecha por publicación y se empareja con `identidad.relacion` tomando la más cercana, o de la columna `publicacion` del archivo complementario;
    - sin fecha conocida, cierre + 3 días (`retraso_publicacion_dias`; en Ohio 270toWin publica 0–8 días después del cierre, mediana 2–3);
    - entra solo si `disponible_desde ≤ corte`; nunca entra una con campo posterior al corte;
    - las excluidas quedan en `reporte.json` y en los avisos.
  - **Mercados:** precio al cierre del día del corte. Kalshi usa la vela diaria (`/series/{serie}/markets/{ticker}/candlesticks`); Polymarket, `clob.polymarket.com/prices-history`, para el ganador y para cada rango. No se escribe en la caché de consultas en vivo.
  - **civicAPI:** solo snapshots guardados con fecha ≤ corte; si no hay, «no aplica» y no cuenta como fuente degradada.
- **La corrida diaria no cambia:** lo que trae una fuente en vivo ya está publicado. Con la captura del 26-oct da P(Acton) 0.551, igual que antes.
- **Ejemplo (corte 21-oct, corrida del 26-oct):**
  - ventana: GS/New River, Marist, Beacon/Shaw y ActiVote; quedan fuera RedBox (campo hasta el 23-oct) y Verasight (publicada el 22-oct);
  - Kalshi 0.78 y Polymarket 0.78/0.23 al cierre del 21-oct;
  - P(Acton) 53.2 %, solo encuestas 41.4 %.
- **Pruebas nuevas:**
  - reconstrucción solo si corte < hoy;
  - publicación tomada de 270toWin;
  - exclusión de lo no publicado;
  - **encuesta futura artificial** inyectada en la fuente: con campo posterior al corte nunca entra; con campo cerrado pero sin publicar, queda fuera en la reconstrucción y entra en la corrida diaria;
  - precios al cierre del corte, sin escribir en la caché;
  - voto anticipado sin snapshot.

**Pendiente (fuera de Ohio):** llevar la regla de reconstrucción a los otros diez paquetes.
