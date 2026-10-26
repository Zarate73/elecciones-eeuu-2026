# Scripts de la auditoría transversal (26-oct-2026)

Reproducen las cifras de `audit/` y de `docs/auditoria_2026-10-26.md`. Ninguno modifica el repositorio: trabajan sobre copias.

| Script | Uso | Salida |
|---|---|---|
| `correr_todos_offline.py` | `python correr_todos_offline.py <raíz de una copia del repo> <métricas.csv>` | corre los 10 pipelines con `--offline` (mismas cachés, calibración y semilla) |
| `diff_encuestas.py` | `python diff_encuestas.py <copia antes> <copia después>` | encuestas que cambian entre dos corridas |
| `a2_pares_candidatos.py` | `python -I a2_pares_candidatos.py <raíz> <pares.csv>` | pares de la misma firma con fin a ≤ 60 días, clasificados (`audit/dedup_candidate_pairs.csv`) |
| `t1_sensibilidad_fechas.py` | `python t1_sensibilidad_fechas.py <estado> <sigla>_pronostico <dir de trabajo> <raíz>` | τ, s, ν, σ(k) y sesgo con días_538 − L, L = 0, 2, 3, 4 |
| `maine_sensibilidad_temporal.py` | `python maine_sensibilidad_temporal.py <copia de maine/produccion> <salida.csv>` | `audit/maine_temporal_sensitivity.csv` |
| `t2_loyo_anidado.py` | desde una copia de `illinois/backtest`: `python t2_loyo_anidado.py <esa carpeta>` | LOYO actual vs. anidado (efectos de casa sin el año externo) |
| `t7_bootstrap_por_anio.py` | igual que el anterior | ΔCRPS, ΔMAE, ΔBrier con bootstrap por año (4,000 réplicas, semilla 7) |
