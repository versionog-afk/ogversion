// one stop: node shot1.js <w> <h> <coarse 0|1> <out-name> <query> [waitMs]
// e.g. node shot1.js 390 664 1 t-hero "" ; node shot1.js 1440 900 0 t-sk "&s=sk@0.95"
const { chromium } = require('playwright');
const PORT = process.env.PORT || 8361;
(async () => {
  const [w, h, coarse, name, query = '', wait = '0'] = process.argv.slice(2);
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: +w, height: +h }, deviceScaleFactor: 1, hasTouch: coarse === '1', isMobile: coarse === '1' });
  const p = await ctx.newPage();
  p.on('pageerror', e => console.log('pageerror: ' + e.message));
  p.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') console.log('console ' + m.type() + ': ' + m.text()); });
  p.on('response', r => { if (r.status() >= 400) console.log('HTTP ' + r.status() + ' ' + r.url()); });
  const t0 = Date.now();
  await p.goto('http://127.0.0.1:' + PORT + '/merch?3d=1' + query, { waitUntil: 'load' });
  await p.waitForFunction(() => window.__m && (window.__m.ready || window.__m.fallback), { timeout: 180000 });
  console.log('ready after', Date.now() - t0, 'ms', await p.evaluate(() => JSON.stringify({ ready: window.__m.ready, fb: window.__m.fallback })));
  if (!/[?&]s=/.test(query)) await p.waitForFunction(() => document.documentElement.classList.contains('rdy') && window.__m.detent !== null, { timeout: 180000 }).catch(() => console.log('no rdy'));
  const t1 = Date.now(); while (Date.now() - t1 < 30000) { await p.waitForTimeout(400); if (!(await p.evaluate(() => window.__m.running))) break; }
  await p.waitForTimeout(+wait + 150);
  await p.screenshot({ path: __dirname + '/shots-na2/' + name + '.png' });
  console.log(name, await p.evaluate(() => { const m = window.__m; return JSON.stringify({ tier: m.tier, dpr: m.dpr, calls: m.calls, tris: m.tris, yaw: +m.yaw.toFixed(1), detent: m.detent, s: +m.s.toFixed(3), d: +m.d.toFixed(3), az: +m.az.toFixed(1), L: +m.L.toFixed(2), u: +m.u.toFixed(2), cls: document.documentElement.className, sw: document.documentElement.scrollWidth, lights: m.lights }); }));
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
