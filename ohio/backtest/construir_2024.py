"""Encuestas finales de 2024 (últimos 21 días, como FiveThirtyEight raw-polls) para las contiendas con mercado y
resultado capturadas en la rama diagnostico-mercados (Wikipedia). Agrega Florida Presidente y Senado 2024.

Uso: python construir_2024.py <carpeta_crudo_diagnostico_mercados>
Salida: data/encuestas_2024_wiki.csv (una versión por encuesta: LV > RV > A, mayor n).
AZ Pres/Sen y GA Pres 2024 no se incluyen (ya están en az2024_encuestas_finales.csv y ga_pres2024_polls.csv).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE.parent.parent / 'arizona' / 'produccion'))
from az_pronostico import encuestas_web as W  # noqa: E402

ELECCION = pd.Timestamp('2024-11-05')
NOMBRES = {'AZ': 'Arizona', 'GA': 'Georgia', 'MI': 'Michigan', 'NV': 'Nevada', 'NC': 'North_Carolina',
           'PA': 'Pennsylvania', 'WI': 'Wisconsin', 'FL': 'Florida', 'TX': 'Texas', 'OH': 'Ohio', 'MN': 'Minnesota',
           'NH': 'New_Hampshire', 'VA': 'Virginia', 'IA': 'Iowa', 'NM': 'New_Mexico', 'ME': 'Maine', 'CO': 'Colorado',
           'NY': 'New_York', 'NJ': 'New_Jersey', 'MO': 'Missouri', 'MT': 'Montana', 'SC': 'South_Carolina',
           'MD': 'Maryland', 'WA': 'Washington', 'IN': 'Indiana'}
YA = {'Pres-AZ', 'Pres-GA', 'Sen-AZ'}


def pagina(cid: str) -> str:
    cargo, st = cid.split('-')
    if cargo == 'Pres':
        return f'2024_United_States_presidential_election_in_{NOMBRES[st]}'
    if cargo == 'Sen':
        return f'2024_United_States_Senate_election_in_{NOMBRES[st]}'
    return f'2024_{NOMBRES[st]}_gubernatorial_election'


def main(crudo: str) -> pd.DataFrame:
    c = pd.read_csv(BASE.parent.parent / 'arizona' / 'backtest' / 'data' / 'mercados_2024' / 'contiendas_2024.csv')
    c = c[c.D_real.notna() & ~c.id.isin(YA)]
    filas = []
    for r in c.itertuples():
        f = Path(crudo) / 'wiki' / f'{pagina(r.id)}.json'
        if not f.exists():
            continue
        html = re.sub(r'(rowspan|colspan)="\s*(\d+)[^"]*"', r'\1="\2"', json.loads(f.read_text())['parse']['text'])
        p = W.elegir_versiones(W.parse_tabla_wikipedia(html, r.d, r.r, 2024))
        if p.empty:
            continue
        p['fin'] = pd.to_datetime(p.fin)
        p = p[(p.fin <= ELECCION) & ((ELECCION - p.fin).dt.days <= 21)]
        tipo = {'Pres': 'Pres-G', 'Sen': 'Sen-G', 'Gob': 'Gov-G'}[r.cargo]
        for x in p.itertuples():
            lado = re.findall(r'\((D|R)\)', str(x.pollster))
            filas.append({'race': f'2024_{tipo}_{r.estado}', 'year': 2024, 'location': r.estado, 'type_simple': tipo,
                          'pollster': x.pollster, 'partisan': lado[0] if len(set(lado)) == 1 else '',
                          'polldate': x.fin.date(), 'electiondate': ELECCION.date(), 'n': x.n, 'pop': x.pop,
                          'D': x.D, 'R': x.R, 'otros': x.otros if pd.notna(x.otros) else 0.0, 'indecisos': x.indecisos,
                          'cand1_actual': r.D_real, 'cand2_actual': r.R_real})
    out = pd.DataFrame(filas)
    out.to_csv(BASE / 'data' / 'encuestas_2024_wiki.csv', index=False)
    return out


if __name__ == '__main__':
    o = main(sys.argv[1])
    print(o.groupby('race').size().to_string())
    print(len(o), 'encuestas ·', o.race.nunique(), 'contiendas')
