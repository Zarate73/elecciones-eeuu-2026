"""Sensibilidad T1 de Maine: calibración con días_538 − L (L = 0, 3, 4); misma fecha de corte, cachés y semilla."""
import sys, glob, importlib
from pathlib import Path
import numpy as np, pandas as pd
D = Path(sys.argv[1]); sys.path.insert(0, str(D))
C = importlib.import_module('me_pronostico.config'); H = importlib.import_module('me_pronostico.historico')
PL = importlib.import_module('me_pronostico.pipeline')
prep0 = H.preparar; filas = []
for L in (0, 3, 4):
    H.preparar = lambda raw, cfg, L=L: (lambda d: d.assign(days=np.where(d.year < 2024, d.days - L, d.days)))(prep0(raw, cfg))
    cfg = C.cargar_config(glob.glob(str(D / 'config/*.toml'))[0], offline=True, corte='2026-10-25')
    for f in cfg.dir_cache.glob('calibracion_*'): f.unlink()
    r = PL.ejecutar(cfg, escribir_salidas=False)
    g, c = r['modelo']['final'], r['calibracion']
    filas.append({'L_dias': L, 'n_contiendas': c['n_contiendas'], 'tau': c['tau'], 's': c['s'], 'nu': c['nu'],
                  'sesgo_estatal_aplicado_pp': g.get('sesgo_estatal_aplicado'), 'margen_encuestas_pp': g.get('margen_encuestas'),
                  'sd_pp': g['sd'], 'margen_final_pp': g['margen'], 'P_D': g['P_D'], 'P_D_encuestas': g.get('P_D_encuestas')})
T = pd.DataFrame(filas); T.to_csv(sys.argv[2], index=False); print(T.round(3).to_string(index=False))
