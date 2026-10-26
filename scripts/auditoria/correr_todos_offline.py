"""Corre los 10 pipelines sin red (mismas cachés, calibración y semilla) y resume métricas por estado."""
import sys, json, subprocess, pandas as pd
from pathlib import Path
T = Path(sys.argv[1]); salida = sys.argv[2]
E = {'arizona': ('az', '2026-10-25'), 'california': ('ca', '2026-10-25'), 'florida': ('fl', '2026-10-25'),
     'georgia': ('ga', '2026-10-26'), 'illinois': ('il', '2026-10-25'), 'maine': ('me', '2026-10-25'),
     'nevada': ('nv', '2026-10-25'), 'new_york': ('ny', '2026-10-26'), 'pennsylvania': ('pa', '2026-10-25'),
     'texas': ('tx', '2026-10-25')}
filas = []
for est, (s, corte) in E.items():
    d = T / est / 'produccion'
    r = subprocess.run([sys.executable, '-m', f'{s}_pronostico', 'correr', '--offline', '--corte', corte, '--sin-graficas'],
                       cwd=d, capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        filas.append({'estado': est, 'error': r.stderr[-400:]}); print(est, 'ERROR', r.stderr[-400:]); continue
    rep = json.load(open(d / 'salidas/ultimo/reporte.json', encoding='utf-8-sig'))
    if est == 'california':
        p = rep['pronostico']; enc = pd.read_csv(d / 'salidas/ultimo/encuestas_pesos.csv', encoding='utf-8-sig')
        filas.append({'estado': est, 'carrera': 'gob', 'filas_combinadas': len(enc), 'en_ventana': int(enc.Incluida.sum()),
                      'k': rep['encuestas'].get('n_efectivo'), 'margen_encuestas': rep['encuestas']['margen_m5_pp'],
                      'sd': rep['m5']['sigma_pp'], 'margen_final': p['margen_pp'], 'P_D': p['p_d_gana_final']})
        continue
    carreras = [('gob', rep['gobernador'], 'encuestas_gobernador.csv')]
    if est == 'georgia' and rep.get('senado'):
        carreras.append(('sen', rep['senado'], 'encuestas_senado.csv'))
    for c, g, f in carreras:
        enc = pd.read_csv(d / 'salidas/ultimo' / f, encoding='utf-8-sig')
        filas.append({'estado': est, 'carrera': c, 'filas_combinadas': len(enc),
                      'en_ventana': int(enc.en_ventana.sum()) if 'en_ventana' in enc else None, 'k': g.get('k'),
                      'margen_encuestas': g.get('margen_encuestas', g.get('margen_corregido_encuestas', g.get('mu_encuestas'))),
                      'sd': g.get('sd'), 'margen_final': g.get('margen'), 'P_D': g.get('P_D')})
X = pd.DataFrame(filas); X.to_csv(salida, index=False); print(X.round(4).to_string(index=False))
