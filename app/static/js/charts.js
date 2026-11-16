/* Minimal SVG line chart (reused from the original ASTRA VITAL edition). No external libraries. */
(function () {
  const COLORS = ['#36d6e7', '#7aa7ff', '#b48cff', '#3ccf91', '#f2b440', '#ff8a5b'];
  function esc(s) { return String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }
  function draw(el) {
    let series; try { series = JSON.parse(el.dataset.series); } catch (e) { return; }
    const band = el.dataset.band ? el.dataset.band.split(',').map(Number) : null;
    const W = 640, H = +(el.dataset.h || 200), P = { l: 40, r: 12, t: 12, b: 24 };
    const pts = series.flatMap(s => s.points.map(p => ({ t: Date.parse(p[0] + 'Z'), v: +p[1] })));
    if (!pts.length) { el.innerHTML = '<div class="empty">No data yet</div>'; return; }
    let t0 = Math.min(...pts.map(p => p.t)), t1 = Math.max(...pts.map(p => p.t)); if (t0 === t1) { t0 -= 864e5; t1 += 864e5; }
    let v0 = Math.min(...pts.map(p => p.v).concat(band || [])), v1 = Math.max(...pts.map(p => p.v).concat(band || []));
    const pad = (v1 - v0) * 0.12 || 1; v0 -= pad; v1 += pad;
    const x = t => P.l + (t - t0) / (t1 - t0) * (W - P.l - P.r), y = v => H - P.b - (v - v0) / (v1 - v0) * (H - P.t - P.b);
    let g = '';
    if (band) g += `<rect x="${P.l}" y="${y(band[1])}" width="${W - P.l - P.r}" height="${Math.max(1, y(band[0]) - y(band[1]))}" fill="rgba(60,207,145,.08)" stroke="rgba(60,207,145,.35)" stroke-dasharray="3 3"/>`;
    for (let i = 0; i <= 4; i++) { const v = v0 + (v1 - v0) * i / 4; g += `<line x1="${P.l}" x2="${W - P.r}" y1="${y(v)}" y2="${y(v)}" stroke="#1a2740"/><text x="${P.l - 6}" y="${y(v) + 3}" text-anchor="end">${v.toFixed(v1 - v0 < 8 ? 1 : 0)}</text>`; }
    [t0, (t0 + t1) / 2, t1].forEach((t, i) => { g += `<text x="${x(t)}" y="${H - 6}" text-anchor="${['start', 'middle', 'end'][i]}">${new Date(t).toISOString().slice(5, 10)}</text>`; });
    series.forEach((s, i) => {
      const c = s.color || COLORS[i % COLORS.length]; const P2 = s.points.map(p => ({ t: Date.parse(p[0] + 'Z'), v: +p[1] }));
      if (!P2.length) return;
      g += `<path d="${P2.map((p, k) => (k ? 'L' : 'M') + x(p.t).toFixed(1) + ',' + y(p.v).toFixed(1)).join(' ')}" fill="none" stroke="${c}" stroke-width="2"/>`;
      P2.forEach(p => { const out = band && (p.v < band[0] || p.v > band[1]); g += `<circle cx="${x(p.t).toFixed(1)}" cy="${y(p.v).toFixed(1)}" r="${out ? 4 : 2.5}" fill="${out ? '#f2b440' : c}"><title>${esc(s.label)} ${p.v} — ${new Date(p.t).toISOString().slice(0, 16)}</title></circle>`; });
    });
    el.innerHTML = `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(el.dataset.label || 'chart')}">${g}</svg>` +
      (series.length > 1 ? `<div class="legend">${series.map((s, i) => `<span><i style="background:${s.color || COLORS[i % COLORS.length]}"></i>${esc(s.label)}</span>`).join('')}</div>` : '');
  }
  document.querySelectorAll('[data-series]').forEach(draw);
  const menu = document.getElementById('menu'); if (menu) menu.onclick = () => document.getElementById('side').classList.toggle('open');
  document.querySelectorAll('form[data-confirm]').forEach(f => f.addEventListener('submit', e => { if (!confirm(f.dataset.confirm)) e.preventDefault(); }));
})();
