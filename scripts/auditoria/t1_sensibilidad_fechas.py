"""Sensibilidad de la calibración de producción a la fecha de disponibilidad (T1): días_538 − L."""
import sys, json, shutil, importlib, glob, tempfile
from pathlib import Path
import numpy as np
est, pkg, work = sys.argv[1], sys.argv[2], Path(sys.argv[3])
dst = work / est
if not dst.exists():
    shutil.copytree(Path(sys.argv[4]) / est / 'produccion', dst)
sys.path.insert(0, str(dst))
cfgm = importlib.import_module(f'{pkg}.config'); H = importlib.import_module(f'{pkg}.historico')
toml = glob.glob(str(dst / 'config' / '*.toml'))[0]
rep = json.load(open(dst / 'salidas/ultimo/reporte.json', encoding='utf-8-sig'))
k = rep['gobernador'].get('k'); h = rep['calibracion']['horizonte_dias']
prep0 = H.preparar
for L in (0, 2, 3, 4):
    def prep(raw, cfg, L=L):
        d = prep0(raw, cfg); d['days'] = np.where(d.year < 2024, d.days - L, d.days); return d
    H.preparar = prep
    cfg = cfgm.cargar_config(toml, offline=True)
    for f in cfg.dir_cache.glob('calibracion_*'): f.unlink()
    p = H.calibrar(cfg, h)
    sd = (p['tau']**2 + p['s']**2 / max(k, 1))**0.5
    print(f"{est} L={L}: n={p['n_contiendas']} τ={p['tau']:.2f} s={p['s']:.2f} ν={p['nu']:.1f} k={k} σ(k)={sd:.2f} sesgo={p.get('sesgo_contraido', float('nan')):+.2f}", flush=True)
