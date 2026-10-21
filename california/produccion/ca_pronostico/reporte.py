"""Escritura de salidas: carpeta por corrida, copia en salidas/ultimo, historial y gráficas."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def escribir_corrida(cfg, carpeta: Path, r: dict) -> None:
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / 'reporte.json').write_text(json.dumps(r['reporte'], ensure_ascii=False, indent=2,
                                                     default=_json_default), encoding='utf-8')
    r['tabla_modelos'].to_csv(carpeta / 'comparacion_modelos.csv', index=False, encoding='utf-8-sig')
    r['tabla_porcentajes'].to_csv(carpeta / 'pronostico_porcentajes.csv', index=False, encoding='utf-8-sig')
    r['tabla_encuestas'].to_csv(carpeta / 'encuestas_pesos.csv', index=False, encoding='utf-8-sig')
    (carpeta / 'resumen.txt').write_text(r['resumen_texto'], encoding='utf-8')
    if cfg.ejecucion.graficas:
        graficas(cfg, carpeta, r)


def publicar_ultimo(cfg, carpeta: Path) -> None:
    ultimo = cfg.dir_salidas / 'ultimo'
    tmp = cfg.dir_salidas / '_ultimo_tmp'
    if tmp.exists():
        shutil.rmtree(tmp)
    shutil.copytree(carpeta, tmp)
    if ultimo.exists():
        shutil.rmtree(ultimo)
    tmp.rename(ultimo)


def agregar_historial(cfg, fila: dict) -> None:
    p = cfg.dir_salidas / 'historial_pronosticos.csv'
    df = pd.DataFrame([fila])
    if p.exists():
        df = pd.concat([pd.read_csv(p, keep_default_na=False), df.astype(object)], ignore_index=True)
    df.to_csv(p, index=False, encoding='utf-8-sig')


def podar_corridas(cfg) -> None:
    d = cfg.dir_salidas / 'corridas'
    if not d.exists():
        return
    corridas = sorted(p for p in d.iterdir() if p.is_dir())
    for p in corridas[:-int(cfg.ejecucion.conservar_corridas)]:
        shutil.rmtree(p, ignore_errors=True)


def graficas(cfg, carpeta: Path, r: dict) -> None:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    e = cfg.eleccion
    corte = r['reporte']['fecha_corte']

    # 1) distribuciones
    sims = r['simulaciones']
    arr = np.concatenate(list(sims.values()))
    bins = np.linspace(*np.quantile(arr, [.001, .999]), 120)
    fig, ax = plt.subplots(figsize=(11, 5))
    for nombre, v in sims.items():
        h, _ = np.histogram(v, bins=bins, density=True)
        es5 = 'M5' in nombre
        ax.plot((bins[1:] + bins[:-1]) / 2, h, lw=2.4 if es5 else 1.1, ls='-' if es5 else '--', label=nombre)
    ax.axvline(0, color='gray', ls=':')
    ax.set(title=f'{e.estado} · {e.cargo} · distribución del margen | corte {corte}',
           xlabel=f'Margen {e.candidato_d} − {e.candidato_r} (pp)', ylabel='Densidad')
    ax.legend(fontsize=9); ax.grid(alpha=.15)
    plt.tight_layout(); plt.savefig(carpeta / 'distribucion_margen.png', dpi=140); plt.close(fig)

    # 2) porcentajes M5
    t = r['tabla_porcentajes']
    t = t[t.modelo == t.modelo.iloc[0]]
    fig, ax = plt.subplots(figsize=(8.5, 3.2))
    for i, (_, f) in enumerate(t.iterrows()):
        c = ['#2e6db4', '#c0392b'][i]
        ax.plot([f.ic95_inf, f.ic95_sup], [i, i], color=c, lw=2, alpha=.35)
        ax.plot([f.ic80_inf, f.ic80_sup], [i, i], color=c, lw=7, alpha=.6)
        ax.plot(f.pronostico_pct, i, 'o', color='white', mec=c, ms=11, mew=2.5)
        ax.text(f.pronostico_pct, i + .28, f'{f.pronostico_pct:.1f}%', ha='center', fontsize=11, color=c)
    ax.axvline(50, color='gray', ls=':')
    ax.set(yticks=[0, 1], yticklabels=t.candidato, ylim=(-.6, 1.7), xlabel='% del voto válido',
           title=f'Pronóstico M5 · mediana, IC 80% e IC 95% | corte {corte}')
    ax.grid(axis='x', alpha=.2)
    plt.tight_layout(); plt.savefig(carpeta / 'pronostico_porcentajes.png', dpi=140); plt.close(fig)

    # 3) componentes de varianza
    comp = r['reporte']['m5']['componentes_varianza_pp2']
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    ax.barh(list(comp), list(comp.values()), color='#4a6fa5')
    ax.set(title=f"M5 · varianza del margen (σ = {r['reporte']['m5']['sigma_pp']:.2f} pp)", xlabel='pp²')
    plt.tight_layout(); plt.savefig(carpeta / 'componentes_varianza.png', dpi=140); plt.close(fig)
