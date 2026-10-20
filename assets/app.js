(function () {
  'use strict';
  var html = document.documentElement;
  var date = html.getAttribute('data-date') || 'latest';

  // ---------- language ----------
  var lang = 'en';
  try { lang = localStorage.getItem('ieum-lang') || 'en'; } catch (e) {}
  function setLang(l) {
    lang = l; html.setAttribute('data-lang', l); html.setAttribute('lang', l === 'kr' ? 'ko' : 'en');
    try { localStorage.setItem('ieum-lang', l); } catch (e) {}
    document.querySelectorAll('.lang button').forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-lang') === l)); });
    render();
  }
  document.querySelectorAll('.lang button').forEach(function (b) { b.addEventListener('click', function () { setLang(b.getAttribute('data-lang')); }); });
  html.setAttribute('data-lang', lang);
  document.querySelectorAll('.lang button').forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-lang') === lang)); });

  // ---------- helpers ----------
  var T = function (v) { if (v == null) return ''; if (typeof v === 'string') return v; return v[lang] != null ? v[lang] : (v.en || ''); };
  var el = function (tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  var fmt = function (v, d) { return (typeof v === 'number' && isFinite(v)) ? v.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d }) : '—'; };
  var clear = function (node) { while (node.firstChild) node.removeChild(node.firstChild); };
  var getJSON = function (url) { return fetch(url, { cache: 'no-store' }).then(function (r) { if (!r.ok) throw new Error(url + ' ' + r.status); return r.json(); }); };

  var data = null, content = null, archive = [];

  // ---------- nails ----------
  function nailCalc(points, unit) {
    var p = (points || []).filter(function (x) { return typeof x.value === 'number' && isFinite(x.value); });
    if (p.length < 21) return null;
    var back = Math.min(60, p.length - 1);
    var a = p[p.length - 1], b = p[p.length - 1 - back], d = a.value - b.value, pct = d / b.value * 100;
    var chg = unit === '%' ? (d >= 0 ? '+' : '') + Math.round(d * 100) + ' bp' : (pct >= 0 ? '+' : '') + pct.toFixed(1) + '%';
    return { latest: a.value, asof: a.date, prior: b.value, prior_date: b.date, change: chg, firing: d > 0 };
  }
  function spark(box, points) {
    box.querySelectorAll('svg').forEach(function (s) { s.remove(); });
    var tip = box.querySelector('.tip');
    var pts = (points || []).slice(-60).filter(function (x) { return typeof x.value === 'number'; });
    var W = box.clientWidth || 300, H = 70, m = 6;
    if (pts.length < 2) return;
    var min = Infinity, max = -Infinity; pts.forEach(function (x) { if (x.value < min) min = x.value; if (x.value > max) max = x.value; });
    if (max === min) { max += 1; min -= 1; }
    var X = function (i) { return m + i * (W - 2 * m) / (pts.length - 1); };
    var Y = function (v) { return H - m - (v - min) * (H - 2 * m) / (max - min); };
    var ns = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(ns, 'svg'); svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H); svg.setAttribute('width', '100%'); svg.setAttribute('height', H);
    var d = pts.map(function (x, i) { return (i ? 'L' : 'M') + X(i).toFixed(1) + ',' + Y(x.value).toFixed(1); }).join('');
    var path = document.createElementNS(ns, 'path'); path.setAttribute('d', d); path.setAttribute('fill', 'none'); path.setAttribute('stroke', '#20808D'); path.setAttribute('stroke-width', '2'); path.setAttribute('stroke-linecap', 'round'); path.setAttribute('stroke-linejoin', 'round');
    svg.appendChild(path);
    var last = document.createElementNS(ns, 'circle'); last.setAttribute('r', '3'); last.setAttribute('fill', '#20808D'); last.setAttribute('cx', X(pts.length - 1)); last.setAttribute('cy', Y(pts[pts.length - 1].value)); svg.appendChild(last);
    var dot = document.createElementNS(ns, 'circle'); dot.setAttribute('r', '3.5'); dot.setAttribute('fill', '#F2A900'); dot.style.display = 'none'; svg.appendChild(dot);
    svg.addEventListener('mousemove', function (ev) {
      var r = svg.getBoundingClientRect(); var mx = (ev.clientX - r.left) * W / r.width;
      var i = Math.max(0, Math.min(pts.length - 1, Math.round((mx - m) / (W - 2 * m) * (pts.length - 1))));
      var p = pts[i]; dot.style.display = ''; dot.setAttribute('cx', X(i)); dot.setAttribute('cy', Y(p.value));
      clear(tip); tip.appendChild(el('span', 'd', p.date)); tip.appendChild(el('b', null, fmt(p.value, 2))); tip.style.display = 'block';
      var left = X(i) * r.width / W + 8; if (left + tip.offsetWidth > r.width) left = X(i) * r.width / W - tip.offsetWidth - 8;
      tip.style.left = left + 'px'; tip.style.top = Math.max(0, Y(p.value) - 30) + 'px';
    });
    svg.addEventListener('mouseleave', function () { dot.style.display = 'none'; tip.style.display = 'none'; });
    box.insertBefore(svg, tip);
  }
  var NAILS = [['ust10y', '%'], ['usdkrw', 'x'], ['brent', 'x']];
  var READ = {
    0: { en: 'No nail in — the regime is set by liquidity and technicals, not by the gauge.', kr: '점등 없음 — 레짐은 유동성·기술적 신호가 결정.' },
    1: { en: 'One nail in — noted, nothing fires.', kr: '하나 점등 — 기록만, 룰 발동 없음.' },
    2: { en: 'Two of three — hostile tilt: no new maximum-conviction entries, keep exposure low.', kr: '셋 중 둘 점등 — 적대적 기울기: 신규 고확신 진입 금지, 노출 축소 유지.' },
    3: { en: 'All three — historically the signal to cut exposure hard and hold cash.', kr: '셋 모두 점등 — 역사적으로 노출을 크게 줄이고 현금을 쥐어야 할 신호.' }
  };
  function nailsCount() {
    if (!data) return null;
    var n = 0, k = 0;
    NAILS.forEach(function (x) { var s = data.series && data.series[x[0]]; var c = s && nailCalc(s.points, x[1]); if (c) { k++; if (c.firing) n++; } });
    return k === 3 ? n : null;
  }

  // ---------- render ----------
  function render() {
    // Brief
    if (content) {
      document.getElementById('asof').textContent = T(content.as_of);
      document.getElementById('headline').textContent = T(content.headline);
      var rg = document.getElementById('regime'); clear(rg);
      [content.regime, content.biotech_gate].forEach(function (it, i) {
        if (!it || i === 1) return;
        var row = el('div', 'row'); row.appendChild(el('div', 'k', T(it.label)));
        var v = el('div', 'v', T(it.value)); v.appendChild(el('div', 'note', T(it.note))); row.appendChild(v); rg.appendChild(row);
      });
      var ps = document.getElementById('posture'); clear(ps);
      (content.posture || []).forEach(function (p) {
        var row = el('div', 'row'); row.appendChild(el('div', 'k', T(p.market)));
        var v = el('div', 'v', T(p.stance)); v.appendChild(el('div', 'note', T(p.note))); row.appendChild(v); ps.appendChild(row);
      });
      var rd = document.getElementById('read'); rd.querySelector('p').textContent = T(content.read);
      var g = document.getElementById('gate'); clear(g);
      if (content.biotech_gate) { var row = el('div', 'row'); row.appendChild(el('div', 'k', T(content.biotech_gate.label))); var v = el('div', 'v', T(content.biotech_gate.value)); v.appendChild(el('div', 'note', T(content.biotech_gate.note))); row.appendChild(v); g.appendChild(row); }
      // watchlist
      var wt = document.querySelector('#watch-table tbody'); clear(wt);
      (content.watchlist || []).forEach(function (w) {
        var tr = el('tr'); tr.appendChild(el('td', 'key', lang === 'kr' && w.name_kr ? w.name_kr : w.name)); tr.appendChild(el('td', null, T(w.archetype))); tr.appendChild(el('td', null, T(w.driver))); tr.appendChild(el('td', 'num', w.last || '—')); tr.appendChild(el('td', 'hide-sm', T(w.tag))); tr.appendChild(el('td', null, w.level || '—')); tr.appendChild(el('td', null, T(w.status))); wt.appendChild(tr);
      });
      // calendar
      var ct = document.querySelector('#cal-table tbody'); clear(ct);
      (content.catalysts || []).forEach(function (c) {
        var tr = el('tr'); tr.appendChild(el('td', 'key', c.date)); tr.appendChild(el('td', null, T(c.event))); tr.appendChild(el('td', null, T(c.scope))); tr.appendChild(el('td', null, T(c.why)));
        var td = el('td'); td.appendChild(el('span', 'prio ' + (c.priority || ''), c.priority || '')); tr.appendChild(td); ct.appendChild(tr);
      });
      var src = document.getElementById('sources'); clear(src);
      if (content.sources && content.sources.length) { src.appendChild(document.createTextNode((lang === 'kr' ? '출처: ' : 'Sources: '))); content.sources.forEach(function (s, i) { if (i) src.appendChild(document.createTextNode(' · ')); var a = el('a', null, s.label); a.href = s.url; a.target = '_blank'; a.rel = 'noopener'; src.appendChild(a); }); }
    }
    // Nails
    if (data) {
      NAILS.forEach(function (x) {
        var id = x[0], unit = x[1], card = document.getElementById('nail-' + id), s = data.series && data.series[id], c = s && nailCalc(s.points, unit);
        card.querySelector('.asof-s').textContent = c ? c.asof : '—';
        card.querySelector('.big').textContent = c ? (unit === '%' ? c.latest.toFixed(2) + '%' : (id === 'brent' ? '$' : '') + fmt(c.latest, 2)) : '—';
        var dl = card.querySelector('.delta'); clear(dl);
        if (c) { dl.appendChild(el('span', c.firing ? 'dn' : 'up', c.change)); dl.appendChild(document.createTextNode(' ' + (lang === 'kr' ? c.prior_date + ' 대비' : 'vs ' + c.prior_date))); } else dl.textContent = '—';
        var pill = card.querySelector('.pill'); pill.className = 'pill ' + (c ? (c.firing ? 'on' : 'off') : ''); pill.textContent = c ? (c.firing ? (lang === 'kr' ? '점등' : 'IN') : (lang === 'kr' ? '소등' : 'quiet')) : '—';
        spark(card.querySelector('.spark'), s && s.points);
      });
      var n = nailsCount();
      document.getElementById('nails-count').textContent = n == null ? '—' : (lang === 'kr' ? n + ' / 3 점등' : n + ' of 3 nails in');
      document.getElementById('nails-read').textContent = n == null ? '' : T(READ[n]);
      // pulse
      var pt = document.querySelector('#pulse-table tbody'); clear(pt);
      var q = data.quotes || [];
      document.getElementById('pulse-empty').hidden = q.length > 0;
      q.forEach(function (r) {
        var tr = el('tr'); tr.appendChild(el('td', 'key', r.symbol)); tr.appendChild(el('td', null, r.name)); tr.appendChild(el('td', 'num', fmt(r.price, 2)));
        tr.appendChild(el('td', 'num ' + (r.change_pct >= 0 ? 'up' : 'dn'), (r.change_pct >= 0 ? '+' : '') + fmt(r.change_pct, 2) + '%')); tr.appendChild(el('td', 'num hide-sm', fmt(r.prev_close, 2))); tr.appendChild(el('td', null, r.day || '')); pt.appendChild(tr);
      });
    }
    // archive
    var at = document.querySelector('#archive-table tbody'); clear(at);
    archive.forEach(function (a) {
      var tr = el('tr'); var td = el('td', 'key'); var link = el('a', null, a.date); link.href = '/' + a.date + '/'; td.appendChild(link); tr.appendChild(td);
      tr.appendChild(el('td', null, T(a.headline))); tr.appendChild(el('td', 'hide-sm', T(a.regime))); tr.appendChild(el('td', 'num hide-sm', a.nails == null ? '—' : a.nails + '/3')); at.appendChild(tr);
    });
  }

  // ---------- load ----------
  var base = date === 'latest' ? 'latest' : date;
  Promise.all([
    getJSON('/data/' + base + '.json').catch(function () { return null; }),
    getJSON('/content/' + base + '.json').catch(function () { return null; }),
    getJSON('/archive/index.json').catch(function () { return []; })
  ]).then(function (r) { data = r[0]; content = r[1]; archive = r[2] || []; render(); });
  window.addEventListener('resize', function () { if (data) NAILS.forEach(function (x) { var s = data.series && data.series[x[0]]; spark(document.getElementById('nail-' + x[0]).querySelector('.spark'), s && s.points); }); });
})();
