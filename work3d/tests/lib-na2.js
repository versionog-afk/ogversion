// Shared helpers for the NA2 page tests: opening the page, waiting for it to settle, anchors, dummy info values.
const { chromium } = require('playwright');
const PORT = process.env.PORT || 8361;
const BASE = 'http://127.0.0.1:' + PORT + '/merch';
const VIEWS = {
  '360x640': { width: 360, height: 640, coarse: true },
  '390x664': { width: 390, height: 664, coarse: true },
  '390x844': { width: 390, height: 844, coarse: true },
  '430x932': { width: 430, height: 932, coarse: true },
  '768x1024': { width: 768, height: 1024, coarse: true },
  '844x390': { width: 844, height: 390, coarse: true },
  '1024x768': { width: 1024, height: 768, coarse: false },
  '1440x900': { width: 1440, height: 900, coarse: false },
  '1920x1080': { width: 1920, height: 1080, coarse: false }
};

// a page at one viewport; query is appended to ?3d=1 (or pass mode '0' for the plain page)
async function open(browser, view, query = '', mode = '1', extra = {}) {
  const V = typeof view === 'string' ? VIEWS[view] : view;
  const ctx = await browser.newContext(Object.assign({ viewport: { width: V.width, height: V.height }, deviceScaleFactor: 1, hasTouch: V.coarse, isMobile: V.coarse }, extra));
  const p = await ctx.newPage();
  const log = { errors: [], bad: [], external: [], requests: [] };
  p.on('pageerror', e => log.errors.push('pageerror ' + e.message));
  p.on('console', m => { if (m.type() === 'error') log.errors.push('console ' + m.text()); });
  p.on('request', r => { const u = r.url(); log.requests.push(u); if (!u.startsWith('http://127.0.0.1:' + PORT + '/') && !u.startsWith('data:') && !u.startsWith('blob:')) log.external.push(u); });
  p.on('response', r => { if (r.status() >= 400) log.bad.push(r.status() + ' ' + r.url()); });
  p.on('requestfailed', r => log.bad.push('failed ' + r.url()));
  if (mode !== null) await p.goto(BASE + '?3d=' + mode + query, { waitUntil: 'load' });
  return { ctx, p, log };
}

// 3D page: the scene is built (or the page fell back)
const ready = p => p.waitForFunction(() => window.__m && (window.__m.ready || window.__m.fallback), null, { timeout: 60000 });
// … and the arrival is over: the figure rests on its front, the swatches may show
const arrived = p => p.waitForFunction(() => document.documentElement.classList.contains('rdy') && window.__m.detent === 0, null, { timeout: 60000 });
// wait until the render loop has stopped (nothing moves any more)
async function settle(p, ms = 15000) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) { await p.waitForTimeout(250); if (!(await p.evaluate(() => window.__m.running))) break; }
  await p.waitForTimeout(250);
}
// the timeline's anchors, in screens
const anchors = p => p.evaluate(() => { const D = window.__m.dbg, o = {}; for (const k in D.tl.A) o[k] = +(D.tl.A[k] / D.stage.S).toFixed(4); return o; });
// real scrolling to a position given in screens; waits until the applied scroll has caught up
async function scrollToS(p, S) {
  await p.evaluate(S => window.scrollTo(0, Math.round(S * window.__m.dbg.stage.S)), S);
  await p.waitForFunction(S => Math.abs(window.__m.s - Math.round(S * window.__m.dbg.stage.S) / window.__m.dbg.stage.S) < 0.002, S, { timeout: 30000 });
  await settle(p);
}
const state = p => p.evaluate(() => { const m = window.__m, D = m.dbg; return { fb: m.fallback, tier: m.tier, dpr: m.dpr, calls: m.calls, tris: m.tris, yaw: +m.yaw.toFixed(1), detent: m.detent, s: +m.s.toFixed(3), d: +m.d.toFixed(3), az: +m.az.toFixed(1), L: +m.L.toFixed(2), u: +m.u.toFixed(2), color: m.color, line: +D.tl.line.toFixed(2), rail: +D.tl.rail.toFixed(2), sw: D.tl.swOn, cls: document.documentElement.className, scrollW: document.documentElement.scrollWidth }; });

/* Dummy values for the info block. The page ships it empty; tests put obvious placeholders in to see the
   layout. kind: '1' one line each, '2' two lines, '5' five lines, 'long' eight lines with one long one. */
const FILL = {
  1: { name: '—', material: ['—'], price: ['—'], shipping: ['—'] },
  2: { name: '— —', material: ['— — —', '— —'], price: ['—'], shipping: ['— — —', '— —'] },
  5: { name: '— — —', material: ['— — —', '— — — — —', '— —', '— — — —', '— — —'], price: ['— —'], shipping: ['— — — —', '— —', '— — — — —', '— —', '— — —'] },
  long: { name: '— — — —', material: ['— — — — — — — — — — —', '— — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — —', '— — — — — — —', '— — — — — — — — — — — — — — — — — — — — — — — — —', '— — — — — —', '— — — — — — — — —', '— — — — — — — — — — — — —', '— — — — — —'], price: ['— — —'], shipping: ['— — — — — — — — — — — — — — — — — — —', '— — — — — — — —', '— — — — — — — — — — — —'] }
};
function fill(p, kind, only) {
  return p.evaluate(([F, only]) => {
    const lines = (el, list) => { el.replaceChildren(...list.map(t => Object.assign(document.createElement('p'), { textContent: t }))); };
    document.querySelectorAll('[data-info]').forEach(el => {
      const key = el.getAttribute('data-info'), k = key.split('.').pop();
      if (only && !only.includes(key)) { el.replaceChildren(); return; }
      if (k === 'name') el.textContent = F.name; else lines(el, F[k]);
    });
    window.dispatchEvent(new Event('resize'));          // the 3D page measures its blocks again
  }, [FILL[kind], only || null]);
}

module.exports = { chromium, PORT, BASE, VIEWS, open, ready, arrived, settle, anchors, scrollToS, state, fill, FILL };
