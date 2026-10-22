/* Tablero de pronósticos EE.UU. 2026 · sin dependencias.
   Datos: tablero/datos/*.json (los escribe scripts/exportar_tablero.py en cada corrida automática).
   Se leen de la rama main en GitHub para estar siempre al día; si falla, de la copia publicada junto a la página. */
'use strict';

const RAW = 'https://raw.githubusercontent.com/Zarate73/elecciones-eeuu-2026/main/tablero/datos/';
const NS = 'http://www.w3.org/2000/svg';
const PENDIENTES = 11;
const tt = document.getElementById('tooltip');
let indice = null;
let ANCHO = 1100;              // ancho útil del contenido; las gráficas se dibujan a su tamaño real
const mitad = () => (ANCHO > 860 ? (ANCHO - 14) / 2 : ANCHO) - 42;
const completo = () => ANCHO - 42;
const cache = {};

/* ---------------------------------------------------------------- utilidades */
async function cargar(nombre) {
  for (const base of [RAW, 'datos/']) {
    try {
      const r = await fetch(base + nombre + (base === RAW ? '?t=' + Math.floor(Date.now() / 300000) : ''), { cache: 'no-cache' });
      if (r.ok) return await r.json();
    } catch (e) { /* siguiente origen */ }
  }
  throw new Error('No se pudo cargar ' + nombre);
}
const el = (tag, attrs = {}, ...hijos) => {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') n.className = v; else if (k === 'text') n.textContent = v; else n.setAttribute(k, v);
  }
  for (const h of hijos) if (h != null) n.append(h);
  return n;
};
const sv = (tag, attrs = {}, texto) => {
  const n = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  if (texto != null) n.textContent = texto;
  return n;
};
const pct = (p, dec = 0) => {
  if (p == null) return '—';
  if (p > 0.995) return '>99%';
  if (p < 0.005) return '<1%';
  return (100 * p).toFixed(dec) + '%';
};
const pp = (x, dec = 1) => (x == null ? '—' : (x > 0 ? '+' : x < 0 ? '−' : '') + Math.abs(x).toFixed(dec));
const num = (x, dec = 1) => (x == null ? '—' : x.toFixed(dec));
const entero = x => (x == null ? '—' : Math.round(x).toLocaleString('es-MX'));
const apellido = n => n.split(' ').slice(-1)[0];
const fecha = s => {
  if (!s) return '—';
  const d = new Date(s + 'T12:00:00');
  return d.toLocaleDateString('es-MX', { day: 'numeric', month: 'short' });
};
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();

function mostrarTT(ev, titulo, filas) {
  tt.replaceChildren();
  tt.append(el('div', { class: 'tt-t', text: titulo }));
  for (const f of filas) {
    const fila = el('div', { class: 'tt-f' });
    if (f.color) { const i = el('i'); i.style.background = f.color; fila.append(i); }
    fila.append(el('b', { text: f.valor }), el('span', { text: f.etiqueta }));
    tt.append(fila);
  }
  tt.hidden = false;
  const r = tt.getBoundingClientRect();
  let x = ev.clientX + 14, y = ev.clientY + 14;
  if (x + r.width > window.innerWidth - 8) x = ev.clientX - r.width - 14;
  if (y + r.height > window.innerHeight - 8) y = ev.clientY - r.height - 14;
  tt.style.left = x + 'px'; tt.style.top = y + 'px';
}
const ocultarTT = () => { tt.hidden = true; };

/* densidad t de Student escalada */
function lgamma(z) {
  const g = 7, c = [0.99999999999980993, 676.5203681218851, -1259.1392167224028, 771.32342877765313,
    -176.61502916214059, 12.507343278686905, -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7];
  if (z < 0.5) return Math.log(Math.PI / Math.sin(Math.PI * z)) - lgamma(1 - z);
  z -= 1; let x = c[0];
  for (let i = 1; i < g + 2; i++) x += c[i] / (z + i);
  const t = z + g + 0.5;
  return 0.5 * Math.log(2 * Math.PI) + (z + 0.5) * Math.log(t) - t + Math.log(x);
}
function tPdf(x, mu, sc, nu) {
  const z = (x - mu) / sc;
  return Math.exp(lgamma((nu + 1) / 2) - lgamma(nu / 2) - 0.5 * Math.log(nu * Math.PI) - ((nu + 1) / 2) * Math.log(1 + z * z / nu)) / sc;
}

/* ---------------------------------------------------------------- tarjetas de estados */
function tarjetas(activo) {
  const nav = document.getElementById('estados');
  nav.replaceChildren();
  nav.setAttribute('role', 'tablist');
  for (const e of indice.estados) {
    const b = el('button', { class: 'tarjeta-estado', role: 'tab', 'aria-selected': String(e.clave === activo), type: 'button' });
    const pd = e.P_D;
    const barra = el('div', { class: 'barra', 'aria-hidden': 'true' }, el('span'), el('span'));
    barra.children[0].style.flex = String(pd); barra.children[1].style.flex = String(1 - pd);
    b.append(el('div', { class: 'nombre', text: `${e.estado} · ${e.cargo}` }),
      el('div', { class: 'detalle', text: `${e.candidatos.D} vs ${e.candidatos.R}` }), barra,
      el('div', { class: 'probs' }, el('span', { text: `${apellido(e.candidatos.D)} ${pct(pd)}` }),
        el('span', { text: `${apellido(e.candidatos.R)} ${pct(1 - pd)}` })));
    b.addEventListener('click', () => { location.hash = e.clave; });
    nav.append(b);
  }
  const p = el('div', { class: 'tarjeta-estado pendiente' },
    el('div', { class: 'nombre', text: `${PENDIENTES} estados más` }),
    el('div', { class: 'detalle', text: 'En preparación. Se agregan con el mismo estándar de backtest y producción.' }));
  nav.append(p);
}

/* ---------------------------------------------------------------- gráficas */
function rangosVoto(d) {
  const p = d.pronostico;
  const filas = [
    { n: d.candidatos.D, v: p.pct_D, ic: p.pct_D_IC80, c: 'var(--dem)' },
    { n: d.candidatos.R, v: p.pct_R, ic: p.pct_R_IC80, c: 'var(--rep)' },
  ];
  if (p.pct_terceros != null) filas.push({ n: 'Terceros', v: p.pct_terceros, ic: p.pct_terceros_IC80, c: 'var(--otros)' });
  const lo = Math.max(0, Math.floor((Math.min(...filas.map(f => f.ic[0])) - 3) / 5) * 5);
  const hi = Math.min(100, Math.ceil((Math.max(...filas.map(f => f.ic[1])) + 3) / 5) * 5);
  const W = Math.round(mitad()), izq = 76, der = 52, alto = 34, H = filas.length * alto + 26;
  const x = v => izq + (v - lo) / (hi - lo) * (W - izq - der);
  const s = sv('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Porcentaje de voto con intervalo del 80%' });
  for (let t = lo; t <= hi; t += (hi - lo > 40 ? 10 : 5)) {
    s.append(sv('line', { x1: x(t), x2: x(t), y1: 4, y2: H - 20, class: 'rejilla-l' }));
    s.append(sv('text', { x: x(t), y: H - 6, 'text-anchor': 'middle' }, t + '%'));
  }
  if (lo <= 50 && hi >= 50) s.append(sv('line', { x1: x(50), x2: x(50), y1: 4, y2: H - 20, class: 'cero' }));
  filas.forEach((f, i) => {
    const y = 14 + i * alto;
    s.append(sv("text", { x: 0, y: y + 4, class: "t-2" }, apellido(f.n)));
    s.append(sv('line', { x1: x(f.ic[0]), x2: x(f.ic[1]), y1: y, y2: y, stroke: f.c, 'stroke-width': 6, 'stroke-linecap': 'round', opacity: 0.35 }));
    s.append(sv('circle', { cx: x(f.v), cy: y, r: 6, fill: f.c, stroke: 'var(--superficie)', 'stroke-width': 2 }));
    s.append(sv('text', { x: x(f.ic[1]) + 8, y: y + 4, class: 't-1' }, f.v.toFixed(1) + '%'));
    const hit = sv('rect', { x: izq, y: y - 14, width: W - izq - der, height: 28, fill: 'transparent' });
    hit.addEventListener('pointermove', ev => mostrarTT(ev, f.n, [
      { valor: f.v.toFixed(1) + '%', etiqueta: 'estimado' },
      { valor: `${f.ic[0].toFixed(1)}–${f.ic[1].toFixed(1)}%`, etiqueta: 'intervalo 80%' }]));
    hit.addEventListener('pointerleave', ocultarTT);
    s.append(hit);
  });
  return s;
}

function distribucion(d) {
  const p = d.pronostico;
  const nu = p.nu || 8, sc = p.sd * Math.sqrt((nu - 2) / nu), mu = p.margen;
  const lo = mu - 3.6 * p.sd, hi = mu + 3.6 * p.sd, n = 220;
  const xs = Array.from({ length: n + 1 }, (_, i) => lo + (hi - lo) * i / n);
  const ys = xs.map(v => tPdf(v, mu, sc, nu));
  const cum = [0]; for (let i = 1; i <= n; i++) cum.push(cum[i - 1] + (ys[i] + ys[i - 1]) / 2 * (xs[i] - xs[i - 1]));
  const tot = cum[n];
  const W = Math.round(mitad()), H = 230, izq = 10, der = 10, arr = 18, ab = 40;
  const X = v => izq + (v - lo) / (hi - lo) * (W - izq - der);
  const ymax = Math.max(...ys);
  const Y = v => H - ab - v / ymax * (H - ab - arr);
  const s = sv('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Distribución del margen' });
  const area = (cond, color) => {
    let dpath = '', abierto = false;
    xs.forEach((v, i) => {
      if (cond(v)) { dpath += (abierto ? 'L' : `M${X(v)},${Y(0)}L`) + `${X(v)},${Y(ys[i])}`; abierto = true; }
      else if (abierto) { dpath += `L${X(xs[i - 1])},${Y(0)}Z`; abierto = false; }
    });
    if (abierto) dpath += `L${X(xs[n])},${Y(0)}Z`;
    s.append(sv('path', { d: dpath, fill: color, opacity: 0.22 }));
  };
  area(v => v >= 0, 'var(--dem)'); area(v => v < 0, 'var(--rep)');
  s.append(sv('path', { d: xs.map((v, i) => `${i ? 'L' : 'M'}${X(v)},${Y(ys[i])}`).join(''), fill: 'none', stroke: 'var(--texto-2)', 'stroke-width': 1.5 }));
  s.append(sv('line', { x1: izq, x2: W - der, y1: Y(0), y2: Y(0), class: 'eje' }));
  const paso = (hi - lo) / (W / 60) > 5 ? 10 : 5;
  for (let t = Math.ceil(lo / paso) * paso; t <= hi; t += paso) {
    s.append(sv('line', { x1: X(t), x2: X(t), y1: Y(0), y2: Y(0) + 4, class: 'eje' }));
    s.append(sv('text', { x: X(t), y: Y(0) + 16, 'text-anchor': 'middle' }, t === 0 ? 'empate' : pp(t, 0)));
  }
  if (lo < 0 && hi > 0) s.append(sv('line', { x1: X(0), x2: X(0), y1: arr - 6, y2: Y(0), class: 'cero' }));
  // intervalo 80 % y media
  const [a, b] = p.margen_IC80;
  const yb = H - 10;
  s.append(sv('line', { x1: X(a), x2: X(b), y1: yb, y2: yb, stroke: 'var(--texto-2)', 'stroke-width': 2 }));
  s.append(sv('line', { x1: X(a), x2: X(a), y1: yb - 4, y2: yb + 4, stroke: 'var(--texto-2)', 'stroke-width': 2 }));
  s.append(sv('line', { x1: X(b), x2: X(b), y1: yb - 4, y2: yb + 4, stroke: 'var(--texto-2)', 'stroke-width': 2 }));
  s.append(sv('circle', { cx: X(mu), cy: yb, r: 4, fill: 'var(--texto)' }));
  s.append(sv('text', { x: X(mu), y: Y(tPdf(mu, mu, sc, nu)) - 6, 'text-anchor': 'middle', class: 't-1' }, `Margen ${pp(mu)} pp`));
  const ld = apellido(d.candidatos.D), lr = apellido(d.candidatos.R);
  if (hi > 0) s.append(sv('text', { x: W - der, y: arr, 'text-anchor': 'end', class: 't-2' }, `gana ${ld} →`));
  if (lo < 0) s.append(sv('text', { x: izq, y: arr, class: 't-2' }, `← gana ${lr}`));
  // crosshair
  const guia = sv('line', { y1: arr, y2: Y(0), stroke: 'var(--texto-3)', 'stroke-width': 1, visibility: 'hidden' });
  s.append(guia);
  const hit = sv('rect', { x: izq, y: 0, width: W - izq - der, height: H - ab + 10, fill: 'transparent' });
  hit.addEventListener('pointermove', ev => {
    const r = s.getBoundingClientRect();
    const v = lo + ((ev.clientX - r.left) / r.width * W - izq) / (W - izq - der) * (hi - lo);
    const i = Math.max(0, Math.min(n, Math.round((v - lo) / (hi - lo) * n)));
    guia.setAttribute('x1', X(xs[i])); guia.setAttribute('x2', X(xs[i])); guia.setAttribute('visibility', 'visible');
    const sobre = 1 - cum[i] / tot;
    const quien = xs[i] >= 0 ? ld : lr;
    mostrarTT(ev, `Margen ${pp(xs[i])} pp`, [
      { valor: pct(xs[i] >= 0 ? sobre : 1 - sobre, 1), etiqueta: xs[i] >= 0 ? `${ld} gana por más` : `${lr} gana por más` }]);
  });
  hit.addEventListener('pointerleave', () => { ocultarTT(); guia.setAttribute('visibility', 'hidden'); });
  s.append(hit);
  return s;
}

function comparacion(d) {
  const p = d.pronostico;
  const filas = [
    { n: 'Pronóstico final', v: p.P_D, c: 'var(--s-final)', fuerte: true },
    { n: 'Solo encuestas', v: p.P_D_encuestas, c: 'var(--s-encuestas)' },
  ];
  const col = { Kalshi: 'var(--s-kalshi)', Polymarket: 'var(--s-poly)' };
  for (const m of d.mercados) if (m.P_D != null) filas.push({ n: m.nombre, v: m.P_D, c: col[m.nombre] || 'var(--otros)' });
  if (d.adicional && d.adicional.titulo && d.adicional.titulo.startsWith('Polymarket') && d.adicional.P_D != null)
    filas.push({ n: 'Polymarket (rangos)', v: d.adicional.P_D, c: 'var(--s-poly)' });
  const W = Math.round(mitad()), izq = Math.min(132, W * 0.34), der = 46, alto = 30, H = filas.length * alto + 24;
  const x = v => izq + v * (W - izq - der);
  const s = sv('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': `Probabilidad de que gane ${d.candidatos.D} según cada fuente` });
  for (const t of [0, 0.25, 0.5, 0.75, 1]) {
    s.append(sv('line', { x1: x(t), x2: x(t), y1: 2, y2: H - 20, class: t === 0.5 ? 'cero' : 'rejilla-l' }));
    s.append(sv('text', { x: x(t), y: H - 6, 'text-anchor': 'middle' }, (100 * t) + '%'));
  }
  filas.forEach((f, i) => {
    const y = 13 + i * alto;
    s.append(sv('text', { x: 0, y: y + 4, class: f.fuerte ? 't-1' : 't-2' }, f.n));
    s.append(sv('line', { x1: x(0), x2: x(f.v), y1: y, y2: y, stroke: f.c, 'stroke-width': 2, opacity: 0.5 }));
    s.append(sv('circle', { cx: x(f.v), cy: y, r: f.fuerte ? 7 : 5.5, fill: f.c, stroke: 'var(--superficie)', 'stroke-width': 2 }));
    s.append(sv('text', { x: W, y: y + 4, 'text-anchor': 'end', class: f.fuerte ? 't-1' : 't-2' }, pct(f.v, 1)));
  });
  return s;
}

function lineas(d) {
  const h = d.historial.filter(r => r.P_D != null);
  const series = [
    { k: 'P_D', n: 'Final', c: 'var(--s-final)', w: 2.5 },
    { k: 'P_D_encuestas', n: 'Solo encuestas', c: 'var(--s-encuestas)', w: 2 },
    { k: 'P_kalshi', n: 'Kalshi', c: 'var(--s-kalshi)', w: 2 },
    { k: 'P_polymarket', n: 'Polymarket', c: 'var(--s-poly)', w: 2 },
  ].filter(s_ => h.some(r => r[s_.k] != null));
  const ley = el('div', { class: 'leyenda' });
  for (const s_ of series) { const i = el('i'); i.style.background = s_.c; ley.append(el('span', {}, i, s_.n)); }
  const W = Math.round(completo()), H = W < 600 ? 220 : 260, izq = 40, der = W < 600 ? 92 : 110, arr = 10, ab = 26;
  const t = h.map(r => new Date(r.corte + 'T12:00:00').getTime());
  const t0 = Math.min(...t) - (h.length === 1 ? 2 * 864e5 : 0), t1 = Math.max(...t) + (h.length === 1 ? 2 * 864e5 : 0);
  const X = v => izq + (t1 === t0 ? 0.5 : (v - t0) / (t1 - t0)) * (W - izq - der);
  const Y = v => arr + (1 - v) * (H - arr - ab);
  const s = sv('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Evolución de la probabilidad' });
  for (const v of [0, 0.25, 0.5, 0.75, 1]) {
    s.append(sv('line', { x1: izq, x2: W - der, y1: Y(v), y2: Y(v), class: v === 0.5 ? 'cero' : 'rejilla-l' }));
    s.append(sv('text', { x: izq - 6, y: Y(v) + 4, 'text-anchor': 'end' }, (100 * v) + '%'));
  }
  const pasos = Math.min(h.length, Math.max(2, Math.floor(W / 120)));
  for (let j = 0; j < pasos; j++) {
    const i = Math.round(j * (h.length - 1) / Math.max(pasos - 1, 1));
    s.append(sv('text', { x: X(t[i]), y: H - 6, 'text-anchor': 'middle' }, fecha(h[i].corte)));
  }
  const etiquetas = [];
  for (const s_ of series) {
    const pts = h.map((r, i) => [t[i], r[s_.k]]).filter(q => q[1] != null);
    if (pts.length > 1) s.append(sv('path', { d: pts.map((q, i) => `${i ? 'L' : 'M'}${X(q[0])},${Y(q[1])}`).join(''), fill: 'none', stroke: s_.c, 'stroke-width': s_.w, 'stroke-linejoin': 'round' }));
    for (const q of pts) s.append(sv('circle', { cx: X(q[0]), cy: Y(q[1]), r: pts.length > 20 ? 0 : 3.5, fill: s_.c, stroke: 'var(--superficie)', 'stroke-width': 1.5 }));
    const u = pts[pts.length - 1];
    etiquetas.push({ y: Y(u[1]), x: X(u[0]), txt: `${s_.n} ${pct(u[1])}` });
  }
  etiquetas.sort((a, b) => a.y - b.y);
  for (let i = 1; i < etiquetas.length; i++) if (etiquetas[i].y - etiquetas[i - 1].y < 13) etiquetas[i].y = etiquetas[i - 1].y + 13;
  for (const e of etiquetas) s.append(sv('text', { x: e.x + 8, y: e.y + 4, class: 't-2' }, e.txt));
  const guia = sv('line', { y1: arr, y2: H - ab, stroke: 'var(--texto-3)', visibility: 'hidden' });
  s.append(guia);
  const hit = sv('rect', { x: izq, y: 0, width: W - izq - der, height: H - ab, fill: 'transparent' });
  hit.addEventListener('pointermove', ev => {
    const r = s.getBoundingClientRect();
    const px = (ev.clientX - r.left) / r.width * W;
    let i = 0, best = Infinity;
    t.forEach((v, j) => { const dd = Math.abs(X(v) - px); if (dd < best) { best = dd; i = j; } });
    guia.setAttribute('x1', X(t[i])); guia.setAttribute('x2', X(t[i])); guia.setAttribute('visibility', 'visible');
    mostrarTT(ev, `Corte ${fecha(h[i].corte)}`, series.filter(s_ => h[i][s_.k] != null)
      .map(s_ => ({ color: s_.c, valor: pct(h[i][s_.k], 1), etiqueta: s_.n }))
      .concat(h[i].margen != null ? [{ valor: pp(h[i].margen) + ' pp', etiqueta: 'margen' }] : []));
  });
  hit.addEventListener('pointerleave', () => { ocultarTT(); guia.setAttribute('visibility', 'hidden'); });
  s.append(hit);
  return el('div', {}, ley, s);
}

function encuestas(d) {
  const e = d.encuestas.filter(r => r.fin && r.margen != null);
  const W = Math.round(completo()), H = W < 600 ? 230 : 270, izq = 40, der = 20, arr = 10, ab = 26;
  const t = e.map(r => new Date(r.fin + 'T12:00:00').getTime());
  const t0 = Math.min(...t) - 3 * 864e5, t1 = Math.max(...t, new Date(d.corte + 'T12:00:00').getTime()) + 3 * 864e5;
  const ms = e.map(r => r.margen).concat([d.pronostico.margen, 0]);
  const lo = Math.floor((Math.min(...ms) - 3) / 5) * 5, hi = Math.ceil((Math.max(...ms) + 3) / 5) * 5;
  const X = v => izq + (v - t0) / (t1 - t0) * (W - izq - der);
  const Y = v => arr + (hi - v) / (hi - lo) * (H - arr - ab);
  const s = sv('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Encuestas: margen por fecha de término' });
  const paso = hi - lo > 40 ? 10 : 5;
  for (let v = lo; v <= hi; v += paso) {
    s.append(sv('line', { x1: izq, x2: W - der, y1: Y(v), y2: Y(v), class: v === 0 ? 'cero' : 'rejilla-l' }));
    s.append(sv('text', { x: izq - 6, y: Y(v) + 4, 'text-anchor': 'end' }, pp(v, 0)));
  }
  const meses = [];
  for (let m = new Date(t0); m.getTime() <= t1; m.setDate(m.getDate() + 1)) if (m.getDate() === 1 || (W > 600 && m.getDate() === 15)) meses.push(new Date(m));
  for (const m of meses) s.append(sv('text', { x: X(m.getTime()), y: H - 6, 'text-anchor': 'middle' }, m.toLocaleDateString('es-MX', { day: 'numeric', month: 'short' })));
  const yP = Y(d.pronostico.margen);
  s.append(sv('line', { x1: izq, x2: W - der, y1: yP, y2: yP, stroke: 'var(--texto)', 'stroke-width': 1.5, 'stroke-dasharray': '6 4' }));
  s.append(sv('text', { x: izq + 6, y: yP - 6, class: 't-1' }, `Pronóstico ${pp(d.pronostico.margen)}`));
  const xc = X(new Date(d.corte + 'T12:00:00').getTime());
  s.append(sv('line', { x1: xc, x2: xc, y1: arr, y2: H - ab, stroke: 'var(--texto-3)', 'stroke-width': 1 }));
  s.append(sv('text', { x: xc - 4, y: arr + 10, 'text-anchor': 'end' }, 'hoy'));
  e.forEach((r, i) => {
    const c = r.margen >= 0 ? 'var(--dem)' : 'var(--rep)';
    const dentro = r.en_ventana !== false;
    s.append(sv('circle', { cx: X(t[i]), cy: Y(r.margen), r: dentro ? 5.5 : 4.5, fill: dentro ? c : 'var(--superficie)', stroke: dentro ? 'var(--superficie)' : c, 'stroke-width': dentro ? 2 : 1.5, opacity: dentro ? 1 : 0.8 }));
    const hit = sv('circle', { cx: X(t[i]), cy: Y(r.margen), r: 12, fill: 'transparent' });
    hit.addEventListener('pointermove', ev => mostrarTT(ev, `${r.encuestadora} · ${fecha(r.fin)}`, [
      { color: c, valor: pp(r.margen) + ' pp', etiqueta: 'margen D−R' },
      { valor: `${num(r.D, 0)}–${num(r.R, 0)}`, etiqueta: `${apellido(d.candidatos.D)}–${apellido(d.candidatos.R)}` },
      { valor: dentro ? 'sí' : 'no', etiqueta: 'en el promedio actual' }].concat(r.peso != null ? [{ valor: pct(r.peso, 1), etiqueta: 'peso' }] : [])));
    hit.addEventListener('pointerleave', ocultarTT);
    s.append(hit);
  });
  const ley = el('div', { class: 'leyenda' });
  const pr = (fill, borde, txt) => { const i = el('i', { class: 'punto-l' }); i.style.background = fill; i.style.border = `1.5px solid ${borde}`; return el('span', {}, i, txt); };
  ley.append(pr(css('--dem'), css('--dem'), `${apellido(d.candidatos.D)} adelante`), pr(css('--rep'), css('--rep'), `${apellido(d.candidatos.R)} adelante`),
    pr('transparent', css('--texto-3'), 'fuera del promedio actual'));
  // tabla
  const tabla = el('table');
  const cab = el('tr'); for (const h of ['Terminó', 'Encuestadora', apellido(d.candidatos.D), apellido(d.candidatos.R), 'Margen', 'Peso', 'Fuente'])
    cab.append(el('th', { class: ['Terminó', 'Encuestadora', 'Fuente'].includes(h) ? '' : 'num', text: h }));
  tabla.append(el('thead', {}, cab));
  const cuerpo = el('tbody');
  for (const r of d.encuestas) {
    const tr = el('tr', { class: r.en_ventana === false ? 'fuera' : '' });
    for (const [v, c] of [[fecha(r.fin), ''], [r.encuestadora, ''], [num(r.D, 1), 'num'], [num(r.R, 1), 'num'], [pp(r.margen), 'num'], [r.peso != null ? pct(r.peso, 1) : (r.en_ventana ? '✓' : ''), 'num'], [r.origen || '', '']])
      tr.append(el('td', { class: c, text: v }));
    cuerpo.append(tr);
  }
  tabla.append(cuerpo);
  const envoltura = el('div', { class: 'tabla-envoltura', hidden: '' }, tabla);
  const boton = el('button', { class: 'boton-tabla', type: 'button', text: 'Ver tabla' });
  boton.addEventListener('click', () => { envoltura.hidden = !envoltura.hidden; boton.textContent = envoltura.hidden ? 'Ver tabla' : 'Ocultar tabla'; });
  return { boton, contenido: el('div', {}, ley, s, envoltura) };
}

function escenarios(d) {
  const e = d.escenarios.filter(r => r.P_D != null);
  if (!e.length) return null;
  const W = Math.round(mitad()), izq = Math.min(300, W * 0.55), der = 40, alto = 24, H = e.length * alto + 22;
  const ps = e.map(r => r.P_D);
  const lo = Math.max(0, Math.floor((Math.min(...ps) - 0.05) * 10) / 10), hi = Math.min(1, Math.ceil((Math.max(...ps) + 0.03) * 10) / 10);
  const x = v => izq + (v - lo) / (hi - lo) * (W - izq - der);
  const maxc = Math.floor(izq / 5.6);
  const s = sv('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Escenarios de sensibilidad' });
  for (const t of [lo, (lo + hi) / 2, hi]) {
    s.append(sv('line', { x1: x(t), x2: x(t), y1: 2, y2: H - 18, class: 'rejilla-l' }));
    s.append(sv('text', { x: x(t), y: H - 4, 'text-anchor': 'middle' }, Math.round(100 * t) + '%'));
  }
  e.forEach((r, i) => {
    const y = 11 + i * alto, final = i === 0;
    const nombre = r.escenario.length > maxc ? r.escenario.slice(0, maxc - 1) + '…' : r.escenario;
    s.append(sv('text', { x: 0, y: y + 4, class: final ? 't-1' : 't-2' }, nombre));
    s.append(sv('circle', { cx: x(r.P_D), cy: y, r: final ? 6 : 4.5, fill: final ? 'var(--s-final)' : 'var(--texto-3)' }));
    s.append(sv('text', { x: W, y: y + 4, 'text-anchor': 'end', class: final ? 't-1' : 't-2' }, pct(r.P_D)));
    const hit = sv('rect', { x: 0, y: y - 11, width: W, height: alto, fill: 'transparent' });
    hit.addEventListener('pointermove', ev => mostrarTT(ev, r.escenario, [
      { valor: pct(r.P_D, 1), etiqueta: `P(${apellido(d.candidatos.D)})` }, { valor: pp(r.margen) + ' pp', etiqueta: 'margen' }]));
    hit.addEventListener('pointerleave', ocultarTT);
    s.append(hit);
  });
  return s;
}

/* ---------------------------------------------------------------- vista de un estado */
function panel(titulo, nota, ...contenido) {
  return el('section', { class: 'panel' }, el('h2', { text: titulo }), nota ? el('p', { class: 'nota', text: nota }) : null, ...contenido);
}

function vista(d) {
  const p = d.pronostico, D = d.candidatos.D, R = d.candidatos.R;
  const raiz = el('div');
  // hero
  const barra = el('div', { class: 'barra-prob', role: 'img', 'aria-label': `${D} ${pct(p.P_D)}, ${R} ${pct(1 - p.P_D)}` }, el('span'), el('span'));
  barra.children[0].style.flex = String(p.P_D); barra.children[1].style.flex = String(1 - p.P_D);
  const pD = el('div', { class: 'punto' }); pD.style.background = 'var(--dem)';
  const pR = el('div', { class: 'punto' }); pR.style.background = 'var(--rep)';
  const hechos = el('div', { class: 'hechos' },
    el('span', {}, 'Margen ', el('b', { text: `${pp(p.margen)} pp` }), ` (80 %: ${pp(p.margen_IC80[0])} a ${pp(p.margen_IC80[1])})`),
    el('span', {}, 'Solo encuestas ', el('b', { text: pct(p.P_D_encuestas) })),
    el('span', {}, 'Peso de mercados ', el('b', { text: num(p.peso_mercados, 2) })),
    ...p.extra.map(x => el('span', {}, x.etiqueta + ' ', el('b', { text: pct(x.valor, 1) }))));
  const hero = panel(`${d.estado} · ${d.cargo}`, null,
    el('div', { class: 'etiqueta-modelo', text: `Modelo ${d.modelo} · corte ${fecha(d.corte)} · faltan ${d.dias_a_eleccion} días` }),
    el('div', { class: 'probabilidades' },
      el('div', { class: 'prob' }, el('div', { class: 'cand' }, pD, `${D} (D)`), el('div', { class: 'valor', text: pct(p.P_D) })),
      el('div', { class: 'prob r' }, el('div', { class: 'cand' }, `${R} (R)`, pR), el('div', { class: 'valor', text: pct(1 - p.P_D) }))),
    barra, el('p', { class: 'nota', style: 'margin-top:8px', text: 'Probabilidad de ganar' }), hechos);
  const voto = panel('Porcentaje de voto', 'Estimado e intervalo del 80 %', rangosVoto(d));
  raiz.append(el('div', { class: 'rejilla r-hero' }, hero, voto));
  // avisos
  const u = d.ultima_encuesta;
  if (u) {
    const viejo = u.dias_desde_fin > 7;
    raiz.append(el('div', { class: 'aviso ' + (viejo ? 'atencion' : 'bien') },
      el('span', { class: 'icono', 'aria-hidden': 'true', text: viejo ? '!' : '✓' }),
      el('p', {}, el('b', { text: viejo ? 'Encuestas viejas. ' : 'Encuestas recientes. ' }),
        `La más reciente es de ${u.encuestadora} y terminó el ${fecha(u.fin)} (${u.dias_desde_fin === 1 ? '1 día' : u.dias_desde_fin + ' días'} antes del corte).` +
        (viejo ? ' Las fuentes se consultan en vivo, pero el promedio no puede ser más reciente que la última encuesta; el modelo amplía su incertidumbre por la antigüedad.' : ''))));
  }
  // distribución + comparación
  const notaMerc = p.mercado_en_distribucion
    ? 'Margen D−R simulado. La zona azul es la probabilidad de que gane el demócrata, coherente con la probabilidad publicada.'
    : 'Margen D−R de las encuestas. Aquí los mercados ajustan solo la probabilidad publicada, no esta distribución.';
  raiz.append(el('div', { class: 'rejilla r-2' },
    panel('Distribución del margen', notaMerc, distribucion(d)),
    panel(`Probabilidad de que gane ${apellido(D)}`, 'Según cada fuente. El final mezcla encuestas (70 %) y mercados (30 %) en escala logit.', comparacion(d))));
  // evolución
  raiz.append(el('div', { class: 'rejilla' }, panel('Evolución', 'Última corrida de cada día.', lineas(d))));
  // encuestas
  const enc = encuestas(d);
  const pe = panel('Encuestas', `Margen D−R de cada encuesta desde la nominación. Rellenas: las que entran al promedio actual (${d.n_encuestas_ventana || '—'} encuestadoras).`, enc.contenido);
  pe.querySelector('h2').append(enc.boton);
  raiz.append(el('div', { class: 'rejilla' }, pe));
  // escenarios + voto anticipado / adicional
  const fila = [];
  const esc = escenarios(d);
  if (esc) fila.push(panel('Escenarios de sensibilidad', 'Cómo cambia la probabilidad con supuestos alternativos. No modifican el pronóstico.', esc));
  const lado = [];
  if (d.anticipado) {
    const m = el('div', { class: 'metricas' });
    for (const x of d.anticipado.metricas) {
      const v = x.formato === 'entero' ? entero(x.valor) : x.formato === 'entero_signo' ? (x.valor > 0 ? '+' : '') + entero(x.valor)
        : x.formato === 'pct' ? num(x.valor, 1) + '%' : pp(x.valor) + ' pp';
      m.append(el('div', { class: 'metrica' }, el('div', { class: 'm-v', text: v }), el('div', { class: 'm-e', text: x.etiqueta })));
    }
    lado.push(panel(`Voto anticipado (${d.anticipado.fuente})`, `Diagnóstico: no entra al pronóstico. Datos al ${fecha(d.anticipado.fecha)}.`, m));
  }
  if (d.adicional && !d.adicional.titulo.startsWith('Polymarket')) {
    const a = d.adicional;
    const m = el('div', { class: 'metricas' },
      el('div', { class: 'metrica' }, el('div', { class: 'm-v', text: pct(a.P_D) }), el('div', { class: 'm-e', text: 'P(demócrata)' })),
      el('div', { class: 'metrica' }, el('div', { class: 'm-v', text: pp(a.margen) + ' pp' }), el('div', { class: 'm-e', text: 'margen' })));
    lado.push(panel(a.titulo, a.nota, m));
  }
  if (lado.length) fila.push(el('div', { style: 'display:grid;gap:14px;align-content:start' }, ...lado));
  if (fila.length) raiz.append(el('div', { class: 'rejilla ' + (fila.length > 1 ? 'r-2' : '') }, ...fila));
  // fuentes
  const f = el('div', { class: 'fuentes' });
  for (const x of d.fuentes) f.append(el('span', { class: 'fuente', title: x.estado },
    el('span', { class: x.en_vivo ? 'ok' : 'no', text: x.en_vivo ? '✓' : '!' }), x.nombre.replaceAll('_', ' ')));
  const avisos = d.avisos.length ? el('p', { class: 'nota', style: 'margin-top:10px', text: 'Avisos: ' + d.avisos.join(' · ') }) : null;
  raiz.append(el('div', { class: 'rejilla' }, panel('Fuentes de esta corrida', '✓ en vivo o archivo verificado · ! se usó la última copia guardada', f, avisos)));
  const enlace = el('p', { class: 'nota' }, 'Detalle, metodología y backtest: ',
    el('a', { href: `https://github.com/Zarate73/elecciones-eeuu-2026/tree/main/${d.carpeta}`, text: `${d.carpeta}/ en GitHub` }));
  raiz.append(enlace);
  return raiz;
}

async function mostrar(clave) {
  const main = document.getElementById('contenido');
  main.style.opacity = '0.5';
  ANCHO = Math.min(main.clientWidth || 1100, 1148);
  try {
    cache[clave] = cache[clave] || await cargar(clave + '.json');
    main.replaceChildren(vista(cache[clave]));
  } catch (e) {
    main.replaceChildren(el('p', { class: 'cargando', text: 'No se pudieron cargar los datos de este estado.' }));
  }
  main.style.opacity = '1';
  tarjetas(clave);
}

async function iniciar() {
  try {
    indice = await cargar('indice.json');
  } catch (e) {
    document.getElementById('contenido').replaceChildren(el('p', { class: 'cargando', text: 'No se pudieron cargar los datos.' }));
    return;
  }
  document.getElementById('n-implementados').textContent = indice.estados.length;
  const g = new Date(indice.generado);
  document.getElementById('actualizado').textContent = 'Datos al ' + g.toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' });
  const elegir = () => {
    const h = location.hash.slice(1);
    mostrar(indice.estados.some(e => e.clave === h) ? h : indice.estados[0].clave);
  };
  window.addEventListener('hashchange', elegir);
  let espera;
  window.addEventListener('resize', () => { clearTimeout(espera); espera = setTimeout(() => { const h = location.hash.slice(1) || indice.estados[0].clave; if (cache[h]) mostrar(h); }, 200); });
  elegir();
}

/* tema: respeta el del sistema; el botón lo fija y se recuerda en este navegador */
(function tema() {
  const raiz = document.documentElement;
  try { const t = localStorage.getItem('tema'); if (t) raiz.dataset.theme = t; } catch (e) { /* sin almacenamiento */ }
  document.getElementById('tema').addEventListener('click', () => {
    const oscuro = raiz.dataset.theme ? raiz.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
    raiz.dataset.theme = oscuro ? 'light' : 'dark';
    try { localStorage.setItem('tema', raiz.dataset.theme); } catch (e) { /* sin almacenamiento */ }
    const h = location.hash.slice(1); if (cache[h]) mostrar(h);
  });
})();

iniciar();
