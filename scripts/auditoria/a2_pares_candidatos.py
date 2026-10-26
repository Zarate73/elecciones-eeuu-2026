"""A2: pares candidatos misma firma con fin a ≤ 60 días (fin ≥ 1-ago), clasificados, y si sobreviven en la salida."""
import sys, itertools, pandas as pd
R = sys.argv[1]; filas = []
for est in ['arizona','california','florida','georgia','illinois','maine','nevada','new_york','pennsylvania','texas']:
    pre = 'encuestas_gob_' if est == 'georgia' else 'encuestas_'
    src = pd.concat([pd.read_csv(f'{R}/{est}/produccion/salidas/cache/{pre}{f}.csv').assign(src=f) for f in ('wikipedia','270towin')], ignore_index=True)
    for c in ('inicio','fin'): src[c] = pd.to_datetime(src[c])
    src = src[src.fin >= '2026-08-01'].drop_duplicates(['clave_538','inicio','fin','pop','D','R','src'])
    out = None
    if est != 'california':
        out = pd.read_csv(f'{R}/{est}/produccion/salidas/ultimo/encuestas_gobernador.csv', encoding='utf-8-sig')
        out['fin'] = pd.to_datetime(out.fin); out['inicio'] = pd.to_datetime(out.inicio); ck = 'clave' if 'clave' in out else 'clave_538'
    for k, g in src.groupby('clave_538'):
        for (_, a), (_, b) in itertools.combinations(g.iterrows(), 2):
            dfin = abs((a.fin - b.fin).days)
            if dfin > 60: continue
            mismas = abs(a.D - b.D) <= .51 and abs(a.R - b.R) <= .51
            pa, pb = a.inicio == a.fin, b.inicio == b.fin            # fecha puntual = publicación (270toWin)
            sep = max((a.inicio - b.fin).days, (b.inicio - a.fin).days)   # >0: periodos disjuntos
            if pa != pb:                                              # rango vs fecha puntual
                rg, pt = (b, a) if pa else (a, b)
                lag = (pt.fin - rg.fin).days                          # publicación − cierre
                tipo = 'rango+publicación ' + ('coherente' if 0 <= lag <= 14 else f'INCOHERENTE (lag {lag:+d})') + (' mismas cifras' if mismas else ' cifras distintas')
            elif not pa and not pb:
                tipo = 'dos rangos ' + ('solapados (LV/RV o misma)' if sep <= 0 else f'DISJUNTOS ({sep} d)') + (' mismas cifras' if mismas else ' cifras distintas')
            else:
                tipo = 'dos fechas puntuales' + (' mismas cifras' if mismas else ' cifras distintas')
            sobreviven = None
            if out is not None:
                o = out[out[ck] == k]
                sobreviven = sum(((o.fin == x.fin) & (o.inicio == x.inicio)).any() or (o.fin == x.fin).any() for x in (a, b))
            filas.append({'estado': est, 'firma': a.pollster, 'a': f'{a.inicio:%d%b}–{a.fin:%d%b} {a['pop']} {a.D:g}-{a.R:g} [{a.src[:4]}]',
                          'b': f'{b.inicio:%d%b}–{b.fin:%d%b} {b['pop']} {b.D:g}-{b.R:g} [{b.src[:4]}]', 'dfin': dfin, 'tipo': tipo, 'en_salida': sobreviven})
T = pd.DataFrame(filas); T.to_csv(sys.argv[2], index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 60); pd.set_option('display.max_rows', 500)
print(T.groupby(['tipo']).size().to_string()); print()
x = T[~T.tipo.str.contains('coherente mismas|solapados', regex=True) | T.tipo.str.contains('INCOHERENTE')]
print(x.to_string(index=False))
