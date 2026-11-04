"""Adaptadores de fuentes de resultados. Cada uno devuelve un Conteo o None (la fuente responde pero aún no hay votos).

Fuentes oficiales comprobadas el 31-oct-2026 (archivos de 2026 ya publicados en cero, o el formato de 2022/2024):
  ncsbe            North Carolina  er.ncsbe.gov/enr/20261103/data/results_0.txt (JSON; precintos que reportan)
  florida_dos      Florida         flelectionfiles.floridados.gov/.../20261103_ElecResultsFL.txt (tab; precintos)
  california_sos   California      api.sos.ca.gov/returns/governor (JSON; «x% (a of b) precincts reporting»)
  pennsylvania_dos Pennsylvania    electionreturns.pa.gov/api/ElectionReturn (JSON doblemente codificado; distritos)
  georgia_ev       Georgia         results.sos.ga.gov (Enhanced Voting): la elección del 3-nov aparece en la lista de
                                   elecciones de la jurisdicción; luego export-<id>.json
  texas_sos        Texas           results.texas-election.com/static/data (la elección 2026 se descubre en las constantes)
  dcboe            Washington D.C. electionresults.dcboe.org/cityWide/getCityWide/<elección> (JSON)
  wikipedia        todos           tabla de resultados de la página de la contienda (sin % de avance)
El «avance» es la fracción de precintos/distritos que reportan, NO la del voto esperado: con precintos al 100 % todavía
faltan votos por correo y provisionales (en CA y AZ, muchos).
"""
from __future__ import annotations

import json
import logging
import math
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from io import StringIO

from .red import get_json, get_text, _get

log = logging.getLogger(__name__)


@dataclass
class Conteo:
    fuente: str
    votos_D: float
    votos_R: float
    votos_otros: float
    avance: float | None = None          # fracción de precintos/distritos que reportan (0–1); None si la fuente no la da
    avance_txt: str = ''
    actualizado: str | None = None       # hora que publica la fuente
    url: str = ''
    consultado: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec='seconds'))

    @property
    def total(self) -> float:
        return self.votos_D + self.votos_R + self.votos_otros

    def dict(self) -> dict:
        return {**asdict(self), 'total': self.total}


def _n(x) -> float:
    """Número de votos; vacío, «nan» o texto → 0 (Wikipedia deja las celdas de votos vacías antes de la elección)."""
    try:
        v = float(str(x).replace(',', '').replace('%', '').strip() or 0)
    except ValueError:
        return 0.0
    return v if math.isfinite(v) else 0.0


def _coincide(patron: str, nombre: str) -> bool:
    """El «apellido» de la configuración es una expresión regular (Nevada: «Aaron.*Ford», porque hay otra Ford)."""
    return re.search(patron, str(nombre), re.I) is not None


def _repartir(filas, carrera, clave_partido, clave_nombre, clave_votos) -> tuple[float, float, float]:
    """Suma votos: D y R por nombre (apellido como regex); si un candidato no aparece por nombre, por código de partido
    (solo si ese código lo tiene una sola fila). Todo lo demás (terceros, votos por escrito) va a «otros»."""
    lado = []
    for f in filas:
        nom = f.get(clave_nombre, '')
        lado.append('D' if _coincide(carrera['d']['apellido'], nom) else 'R' if _coincide(carrera['r']['apellido'], nom) else '')
    for k in ('D', 'R'):
        if k not in lado:
            cod = carrera[k.lower()]['partido'].upper()
            idx = [i for i, f in enumerate(filas) if str(f.get(clave_partido, '')).strip().upper() == cod and not lado[i]]
            if len(idx) == 1:
                lado[idx[0]] = k
    tot = {'D': 0.0, 'R': 0.0, '': 0.0}
    for f, k in zip(filas, lado):
        tot[k] += _n(f[clave_votos])
    return tot['D'], tot['R'], tot['']


# ------------------------------------------------------------------------------------------ North Carolina
def _sin_cache(url: str) -> str:
    """Los archivos estáticos (Florida, NCSBE) quedan en caché de CDN: la noche electoral Florida servía el archivo en
    cero desde caché mientras el original ya tenía 8 millones de votos. Un parámetro de tiempo evita la caché."""
    import time
    return url + ('&' if '?' in url else '?') + f'_t={int(time.time())}'


def ncsbe(carrera, f, cfg) -> Conteo | None:
    d = get_json(_sin_cache(f['url']), timeout=cfg['timeout_s'])
    filas = [x for x in d if str(x.get('cnm', '')).upper().startswith(f['contienda'].upper())]
    if not filas:
        raise ValueError(f"NCSBE: sin la contienda {f['contienda']}")
    vd, vr, vo = _repartir(filas, carrera, 'pty', 'bnm', 'vct')
    prt, ptl = _n(filas[0].get('prt')), _n(filas[0].get('ptl'))
    if vd + vr + vo <= 0:
        return None
    return Conteo('NCSBE (oficial)', vd, vr, vo, prt / ptl if ptl else None, f'{prt:.0f} de {ptl:.0f} precintos', None, f['url'])


# ------------------------------------------------------------------------------------------ Florida
def florida_dos(carrera, f, cfg) -> Conteo | None:
    txt = get_text(_sin_cache(f['url']), timeout=cfg['timeout_s'])
    import csv
    filas = [x for x in csv.DictReader(StringIO(txt), delimiter='\t') if (x.get('RaceCode') or '').strip() == f['carrera']]
    if not filas:
        raise ValueError(f"Florida: sin la carrera {f['carrera']}")
    for x in filas:
        x['nombre'] = ' '.join((x.get(k) or '') for k in ('CanNameFirst', 'CanNameMiddle', 'CanNameLast'))
    vd, vr, vo = _repartir(filas, carrera, 'PartyCode', 'nombre', 'CanVotes')
    condados = {}
    for x in filas:
        condados[x['CountyCode']] = (_n(x['PrecinctsReporting']), _n(x['Precincts']))
    rep, tot = sum(a for a, _ in condados.values()), sum(b for _, b in condados.values())
    if vd + vr + vo <= 0:
        return None
    return Conteo('Florida DOS (oficial)', vd, vr, vo, rep / tot if tot else None, f'{rep:.0f} de {tot:.0f} precintos', None, f['url'])


# ------------------------------------------------------------------------------------------ California
def california_sos(carrera, f, cfg) -> Conteo | None:
    d = get_json(f['url'], timeout=cfg['timeout_s'])
    filas = d.get('candidates') or []
    vd, vr, vo = _repartir(filas, carrera, 'Party', 'Name', 'Votes')
    m = re.search(r'\(([\d,]+) of ([\d,]+)\)', d.get('Reporting', ''))
    av = _n(m.group(1)) / _n(m.group(2)) if m and _n(m.group(2)) else None
    if vd + vr + vo <= 0:
        return None
    return Conteo('California SOS (oficial)', vd, vr, vo, av, d.get('Reporting', ''), d.get('ReportingTime'), f['url'])


# ------------------------------------------------------------------------------------------ Pennsylvania
PA = 'https://www.electionreturns.pa.gov/api/ElectionReturn'


def _pa(url, cfg):
    d = get_json(url, timeout=cfg['timeout_s'])
    return json.loads(d) if isinstance(d, str) else d


def pennsylvania_dos(carrera, f, cfg) -> Conteo | None:
    url = f'{PA}/GET?methodName=GetSummaryData&electionid=undefined&electiontype=undefined&isactive=1'
    d = _pa(url, cfg)
    filas = []
    for _, bloques in (d.get('Election') or {}).items():
        for b in bloques:
            for x in b.get('Statewide') or []:
                if str(x.get('OfficeName', '')).strip().lower() == f['oficina'].lower():
                    filas.append(x)
    if not filas:
        raise ValueError(f"Pennsylvania: sin la oficina {f['oficina']}")
    if str(filas[0].get('ElectionYear')) != '2026':
        raise ValueError(f"Pennsylvania: la elección activa es de {filas[0].get('ElectionYear')}")
    vd, vr, vo = _repartir(filas, carrera, 'PartyName', 'CandidateName', 'Votes')
    av, txt = None, ''
    try:
        t = _pa(f'{PA}/GetOfficeNames?countyName=&methodName=GetOfficeNames&electionid=undefined&electiontype=undefined&isactive=undefined', cfg)
        msg = json.loads(t['Table1'][0]['DashboardMessage'])
        txt = msg.get('DistrictMessage', '').strip()
        m = re.search(r'([\d,]+)\s+Out of\s+([\d,]+)', txt)
        av = _n(m.group(1)) / _n(m.group(2)) if m else None
    except Exception as exc:                                   # noqa: BLE001 - el avance es opcional
        log.info('Pennsylvania avance: %s', exc)
    if vd + vr + vo <= 0:
        return None
    return Conteo('Pennsylvania DOS (oficial)', vd, vr, vo, av, txt, None, url)


# ------------------------------------------------------------------------------------------ Georgia (Enhanced Voting)
GA = 'https://results.sos.ga.gov'


def georgia_ev(carrera, f, cfg) -> Conteo | None:
    j = get_json(f'{GA}/results/public/api/jurisdictions/Georgia', timeout=cfg['timeout_s'])
    el = [e for e in j.get('elections') or [] if e.get('electionDate') == cfg['dia_eleccion']]
    if not el:
        return None                                        # aún no publican la elección del 3-nov
    eid = el[0]['publicElectionId']
    url = f'{GA}/cdn/results/Georgia/export-{eid}.json'
    d = get_json(url, timeout=max(cfg['timeout_s'], 120))
    items = [b for b in (d.get('results') or {}).get('ballotItems') or [] if str(b.get('name', '')).strip().lower() == f['contienda'].lower()]
    if not items:
        raise ValueError(f"Georgia: sin la contienda {f['contienda']} en {eid}")
    it = items[0]
    vd, vr, vo = _repartir(it['ballotOptions'], carrera, 'politicalParty', 'name', 'voteCount')
    pr, pp = it.get('precinctsReporting'), it.get('precinctsParticipating')
    av = (_n(pr) / _n(pp)) if pr is not None and pp else None
    if vd + vr + vo <= 0:
        return None
    return Conteo('Georgia SOS (oficial)', vd, vr, vo, av, f'{pr} de {pp} precintos' if av is not None else '',
                  d.get('createdAt'), url)


# ------------------------------------------------------------------------------------------ Texas
TX = 'https://results.texas-election.com/static/data'


def texas_sos(carrera, f, cfg) -> Conteo | None:
    v = get_json(f'{TX}/Version.json', timeout=cfg['timeout_s'])['___versionNo']
    c = get_json(f'{TX}/ElectionConstants_{v}.json', timeout=cfg['timeout_s'])
    gen = ((c.get('electionInfo') or {}).get(f['anio']) or {}).get('G') or {}
    if not gen:
        return None                                        # aún no publican la general de 2026
    eid = next(iter(gen))
    ver = get_json(f'{TX}/election/{eid}/Version.json', timeout=cfg['timeout_s'])['___versionNo']
    os_ = get_json(f'{TX}/election/{eid}/{ver}/OfficeSummary.json', timeout=cfg['timeout_s'])
    of = [o for o in os_.get('OS') or [] if f['oficina'] in str(o.get('ON', '')).upper()]
    if not of:
        raise ValueError(f"Texas: sin la oficina {f['oficina']}")
    filas = [{'P': {'R': 'REP', 'D': 'DEM'}.get(x.get('P'), x.get('P')), 'N': x.get('N'), 'T': x.get('T')} for x in of[0]['C']]
    vd, vr, vo = _repartir(filas, carrera, 'P', 'N', 'T')
    h = get_json(f'{TX}/election/{eid}/{ver}/Home.json', timeout=cfg['timeout_s'])
    pr = h.get('PrecinctsReporting') or {}
    av = _n(pr.get('PR')) / _n(pr.get('PT')) if _n(pr.get('PT')) else None
    if vd + vr + vo <= 0:
        return None
    return Conteo('Texas SOS (oficial)', vd, vr, vo, av, f"{pr.get('PR')} de {pr.get('PT')} precintos", h.get('LastUpdatedTime'),
                  f'{TX}/election/{eid}/{ver}/OfficeSummary.json')


# ------------------------------------------------------------------------------------------ Washington D.C.
def dcboe(carrera, f, cfg) -> Conteo | None:
    url = f"https://electionresults.dcboe.org/cityWide/getCityWide/{f['eleccion']}"
    try:
        d = get_json(url, timeout=cfg['timeout_s'], reintentos=1)
    except Exception as exc:                                   # noqa: BLE001 - 404 hasta la noche electoral
        if '404' in str(exc):
            return None
        raise
    c = [x for x in d if f['contienda'] in str(x.get('OfficeName', '')).upper() and 'DEM ' not in str(x.get('OfficeName', ''))]
    if not c:
        raise ValueError(f"DCBOE: sin la contienda {f['contienda']}")
    filas = [{'n': x['Contestant'], 'v': x['Votes'], 'p': x.get('PartyCode', '')} for x in c[0]['ElectionData']
             if not re.search(r'OVER|UNDER', str(x['Contestant']))]
    vd, vr, vo = _repartir(filas, carrera, 'p', 'n', 'v')
    if vd + vr + vo <= 0:
        return None
    return Conteo('DCBOE (oficial, 1.ª ronda RCV)', vd, vr, vo, None, c[0].get('ResultText', ''), None, url)


# ------------------------------------------------------------------------------------------ Wikipedia (respaldo)
EXCLUIR = r'Total|Majority|Turnout|Registered|Over ?votes|Under ?votes|Blank|hold|gain|^Other$'


def wikipedia(carrera, f, cfg) -> Conteo | None:
    import pandas as pd
    d = get_json(cfg['wikipedia_api'], params={'action': 'parse', 'page': carrera['wikipedia'], 'prop': 'text', 'format': 'json',
                                                'formatversion': 2, 'redirects': 1}, timeout=cfg['timeout_s'])
    if 'error' in d:
        raise RuntimeError(d['error'].get('info'))
    try:
        tablas = pd.read_html(StringIO(d['parse']['text']))
    except ValueError:
        return None
    ap_d, ap_r = carrera['d']['apellido'].lower(), carrera['r']['apellido'].lower()
    mejor = None
    for t in tablas:
        t = t.copy()
        t.columns = [str(c[-1] if isinstance(c, tuple) else c) for c in t.columns]
        cc = [c for c in t.columns if c.startswith('Candidate')]
        if 'Votes' not in t.columns or not cc:
            continue
        cand = t[cc[0]].astype(str)
        if not (cand.str.lower().str.contains(ap_d, regex=False).any() and cand.str.lower().str.contains(ap_r, regex=False).any()):
            continue
        votos = (t['Votes'] if isinstance(t['Votes'], pd.Series) else t['Votes'].iloc[:, 0]).map(_n)
        ok = ~cand.str.contains(EXCLUIR, case=False)
        if 'Party' in ' '.join(t.columns):
            pc = [c for c in t.columns if c.startswith('Party')][-1]
            ok &= ~t[pc].astype(str).str.contains(EXCLUIR, case=False)
        filas = [{'n': n, 'v': v, 'p': ''} for n, v in zip(cand[ok], votos[ok])]
        mejor = filas                                       # la última tabla con ambos candidatos: la de la general
    url = f"https://en.wikipedia.org/wiki/{carrera['wikipedia']}"
    if mejor:
        vd, vr, vo = _repartir(mejor, carrera, 'p', 'n', 'v')
        if vd > 0 and vr > 0:
            return Conteo('Wikipedia (respaldo, sin % de avance)', vd, vr, vo, None, '', None, url)
    # Noche electoral: la tabla de resultados sigue vacía, pero el infobox («Popular vote», «Percentage») ya trae el
    # conteo parcial de los dos principales. Los «otros» se deducen del porcentaje: total = votos / porcentaje.
    for t in tablas:
        t = t.copy()
        filas = {str(r.iloc[0]).replace('\xa0', ' ').strip(): r for _, r in t.iterrows()}
        if 'Nominee' not in filas or 'Popular vote' not in filas:
            continue
        nom, vot = filas['Nominee'], filas['Popular vote']
        por = filas.get('Percentage')
        cols = [c for c in t.columns[1:] if str(nom[c]) != 'nan']
        lado = {}
        for c in cols:
            k = 'D' if _coincide(carrera['d']['apellido'], nom[c]) else 'R' if _coincide(carrera['r']['apellido'], nom[c]) else None
            if k:
                lado[k] = (_n(vot[c]), _n(por[c]) if por is not None else 0.0)
        if 'D' in lado and 'R' in lado and lado['D'][0] > 0 and lado['R'][0] > 0:
            vd, vr = lado['D'][0], lado['R'][0]
            tot = [v / (p_ / 100) for v, p_ in lado.values() if p_ > 0]
            vo = max(0.0, (sum(tot) / len(tot)) - vd - vr) if tot else 0.0
            av, txt = None, ''
            for t2 in tablas:                                  # fila «Reporting: 70% as of 9:58 PM EST» del infobox
                for _, r2 in t2.iterrows():
                    if str(r2.iloc[0]).strip().startswith('Reporting') and len(r2) > 1:
                        m = re.search(r'([\d.]+)\s*%\s*(as of.*)?', str(r2.iloc[1]))
                        if m:
                            av, txt = float(m.group(1)) / 100, f"{m.group(1)}% {m.group(2) or ''}".strip()
                            break
                if av is not None:
                    break
            return Conteo('Wikipedia, infobox (respaldo; avance = % reportado en Wikipedia)', vd, vr, vo, av, txt, None, url)
    return None


ADAPTADORES = {'ncsbe': ncsbe, 'florida_dos': florida_dos, 'california_sos': california_sos,
               'pennsylvania_dos': pennsylvania_dos, 'georgia_ev': georgia_ev, 'texas_sos': texas_sos, 'dcboe': dcboe,
               'wikipedia': wikipedia}
