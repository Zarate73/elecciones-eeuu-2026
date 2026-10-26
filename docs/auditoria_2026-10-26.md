# Auditoría transversal · Fase 1 · Correcciones aplicadas (26-oct-2026)

Línea base congelada: commit `8399d6c` (manifiesto de huellas en `audit/baseline_8399d6c_manifest.csv`).
Alcance: los diez modelos con producción (AZ, CA, FL, GA, IL, ME, NV, NY, PA, TX). Elección: 3-nov-2026.

## Decisión

Se mantienen τ, s, ν, el peso de mercados `w = 0.30`, las reglas de sesgo estatal y los pronósticos publicados.
Antes de la elección se corrige un solo punto del código: la **identidad de las encuestas** (T3). T4, T7 y T1 (Maine) se documentan. T2, T5, T6 y la investigación estadística quedan para después del 3-nov.

| Código | Hallazgo | Evidencia | Acción |
|---|---|---|---|
| T3 | Fusión de olas distintas (≤ 7 días; mismas cifras ≤ 60 días) | 0 fusiones erróneas en las salidas del 25/26-oct; riesgo real con trackings de la última semana | **Corregido**: `identidad.py` común + 17 pruebas sintéticas por paquete |
| T4 | 945 contiendas ≠ backtest del pronóstico con mercados | `w` estudiado con 40 contiendas de 2024 | Sección «Qué valida y qué no valida» en cada README |
| T7 | Significancia del sesgo estatal | Bootstrap por año: ΔCRPS −0.134, IC95 [−0.320, +0.051]; ΔBrier +0.0009 [−0.004, +0.006] | Afirmaciones corregidas en los README; regla sin cambios |
| T1 | Mediana de campo (538) vs. cierre (producción) | σ no se ensancha (−0.1 a −0.3 pp); Maine: corrección estatal −3.67 → −2.53 pp | Tabla de sensibilidad L = 3/4 en `maine/README.md` |
| T2 | Efectos de casa del año externo en LOYO | Usan desviaciones entre encuestas, no resultados; CRPS 3.3039 → 3.3059 | Después del 3-nov |
| T5 | Bases heterogéneas | H = 8/9 es correcto (sigue el corte); AZ (906) y GA (915) no cargan `encuestas_2024_wiki.csv` | Después del 3-nov |
| T6 | California M5 | Kalshi ajusta solo la probabilidad, por diseño | Pista separada después del 3-nov |

## T3 · Identidad de encuestas

**Antes.** Había tres familias de reglas. AZ, FL, NV, PA y ME fundían la misma firma con fin a ≤ 7 días, o con mismas cifras a ≤ 60 días, también dentro de una misma fuente. GA y CA aplicaban ≤ 7 días, o mismas cifras a ≤ 21 días. TX, IL y NY ya usaban el periodo de campo, pero conservaban «mismas cifras ≤ 60 días» y «firmas distintas con mismas cifras y mismo n ≤ 30 días».

**Ahora.** Un solo módulo, `<sigla>_pronostico/identidad.py`, idéntico en los diez paquetes; la prueba `test_modulo_identico_en_los_diez_paquetes` verifica su huella md5.
- Dos periodos de campo **disjuntos** = dos estudios, siempre (ActiVote TX, OnMessage NY, Beacon/Shaw TX, Emerson TX ago/oct, Texas Southern).
- Periodos **solapados** = el mismo estudio (LV/RV, o la misma encuesta en dos fuentes), salvo dentro de una misma fuente con márgenes a más de 3 pp, que se trata como ambiguo y se conservan las dos.
- **Fecha puntual** (270toWin publica por fecha de publicación) = el mismo estudio si cae entre el inicio de campo y 14 días después del cierre y las cifras son compatibles (mismas cifras, margen a ≤ 3 pp o mismo n). En las fuentes del 25/26-oct (fin ≥ 1-ago) hay 62 parejas de este tipo: 60 tienen margen a ≤ 3 pp; las otras 2 (YouGov TX y FL) son la encuesta del patrocinador (CBS, Univision), con la que sí se funden.
- **Fecha mal capturada**: rango + fecha puntual a ≤ 60 días solo con mismas cifras **y** mismo n. El único caso es Arizona State/BSP: campo 18-ago–4-sep, fechada el 19-oct en 270toWin. Sin esta regla, Arizona habría tomado esa encuesta como nueva y su σ habría subido de 5.3 a 6.6 pp.
- **Firmas distintas**: solo la etiqueta genérica «YouGov» de 270toWin frente al patrocinador. Mismas cifras y mismo n entre dos firmas reales no bastan (GQR y GrayHouse, AZ: 49–45, n = 600).
- Se elige la candidata **más cercana**, no la primera. Los periodos invertidos por error de captura se corrigen (Grassroots NV: «8 jul–6 jul»). Una fila verificada sin población no cede sus cifras a la versión redondeada (HighGround AZ).
- Cada fusión, cada separación con mismas cifras y cada caso ambiguo quedan en el log y en `audit/dedup_decisions.csv`.
- La validación posterior detecta duplicados por (firma, inicio, fin), no por (firma, fin). Así, dos estudios distintos con la misma fecha de cierre ya no detienen la corrida.
- Georgia: un ajuste manual de `data/ajustes_encuestas.csv` se aplica a **una** sola fila, la más cercana con calendario compatible. Antes se aplicaba a todas las de la firma a ±7 días.

**Antes/después** (mismas cachés, calibración y semilla; `audit/before_after_state_metrics.csv`). k, margen, σ y P(D) son **idénticos** en las once carreras. Las únicas diferencias son decimales de la base verificada en encuestas que están fuera de la ventana (Quantus AZ 49.1–43.2, St. Pete FL, Emerson NV) y una fila de la primaria de California (Berkeley IGS) que queda separada como ambigua y no entra al modelo.

**Pruebas.** Las pruebas existentes más 17 sintéticas pasan en los diez paquetes: AZ 33, CA 36, FL 39, GA 34, IL 38, ME 38, NV 37, NY 47, PA 34, TX 41.

## T1 · Maine

Ver la tabla en `maine/README.md` («Sensibilidad de Maine a la fecha de disponibilidad»). El pronóstico oficial es L = 0. Con L = 3–4, la corrección estatal baja ~1.1 pp y P(D) sube unos 2 puntos.

## Después del 3-nov (bloque B)

1. LOYO anidado y walk-forward común; prueba automatizada de que no entra información posterior al corte.
2. Homologar el histórico 2024 en AZ y GA; reportar sobre contiendas comunes.
3. Bootstrap por año en todos los reportes; separar métricas de margen (CRPS, MAE) y de ganador (Brier, log score); cobertura 80/95 por año, cargo y k.
4. Mercados: guardar snapshots fechados; comparar w = 0 y w = 0.30 fijados antes del corte; no reoptimizar con un solo año.
5. California M5: pista separada; coherencia entre P(D) con Kalshi y la distribución del margen.
6. Fundamentos: solo si mejoran fuera de muestra contra el V11 congelado.
7. Evaluar los diez pronósticos congelados contra los resultados oficiales de 2026 como validación prospectiva, sin reoptimizar con esos resultados.
