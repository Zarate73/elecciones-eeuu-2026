import sys, pandas as pd
A, D = sys.argv[1], sys.argv[2]
for est in ['arizona','florida','georgia','illinois','maine','nevada','new_york','pennsylvania','texas']:
    for f in (['encuestas_gobernador.csv'] + (['encuestas_senado.csv'] if est == 'georgia' else [])):
        a = pd.read_csv(f'{A}/{est}/produccion/salidas/ultimo/{f}', encoding='utf-8-sig'); d = pd.read_csv(f'{D}/{est}/produccion/salidas/ultimo/{f}', encoding='utf-8-sig')
        k = 'clave' if 'clave' in a else 'clave_538'
        key = lambda x: set(zip(x[k], x.inicio.astype(str), x.fin.astype(str), x.D.round(1), x.R.round(1)))
        sa, sd = key(a), key(d)
        if sa != sd:
            print(f'== {est} {f}: antes {len(a)} · después {len(d)}')
            for x in sorted(sa - sd): print('   − ', x)
            for x in sorted(sd - sa): print('   + ', x)
