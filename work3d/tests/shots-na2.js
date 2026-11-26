// Storyboard screenshots of the NA2 page. node shots-na2.js [viewport ...] [--only stop,stop]   → shots-na2/<viewport>-<stop>.png
const { chromium } = require('playwright');
const PORT = process.env.PORT || 8361;
const OUT = __dirname + '/shots-na2/';
const VIEWS = {
  '390x664': { width: 390, height: 664, coarse: true },
  '844x390': { width: 844, height: 390, coarse: true },
  '1440x900': { width: 1440, height: 900, coarse: false }
};
// stop name → ?s= value, or a function of the anchors (in screens) read from the page
const STOPS = [
  ['s0.5', () => '0.5'],
  ['priekis', () => 'priekis@0.85'],
  ['ap-side', A => String(A.apSide)],
  ['ap-back', A => String(A.apBack)],
  ['nugara', () => 'nugara@0.9'],
  ['sk0.62', () => 'sk@0.62'],
  ['sk0.95', () => 'sk@0.95'],
  ['tiek', () => 'tiek@0.8'],
  ['stovas0.6', () => 'stovas@0.6'],
  ['stovas-item', A => String((A.stRail1 + A.stPhotos) / 2 + 0.001)],
  ['stovas-rail', A => String(A.stPhotos + 0.5)]
];
(async () => {
  const args = process.argv.slice(2);
  const oi = args.indexOf('--only');
  const only = oi >= 0 ? args[oi + 1].split(',') : null;
  const want = args.filter((a, i) => !a.startsWith('--') && (oi < 0 || i !== oi + 1));
  const b = await chromium.launch();
  const report = {};
  for (const name of Object.keys(VIEWS)) {
    if (want.length && !want.includes(name)) continue;
    const V = VIEWS[name];
    const open = async query => {
      const ctx = await b.newContext({ viewport: { width: V.width, height: V.height }, deviceScaleFactor: 1, hasTouch: V.coarse, isMobile: V.coarse });
      const p = await ctx.newPage();
      p.on('pageerror', e => console.log(name, 'pageerror: ' + e.message));
      p.on('console', m => { if (m.type() === 'error') console.log(name, 'console error: ' + m.text()); });
      await p.goto('http://127.0.0.1:' + PORT + '/merch?3d=1' + query, { waitUntil: 'load' });
      await p.waitForFunction(() => window.__m && (window.__m.ready || window.__m.fallback), { timeout: 180000 });
      return { ctx, p };
    };
    const info = p => p.evaluate(() => { const m = window.__m; return { fb: m.fallback, tier: m.tier, dpr: m.dpr, calls: m.calls, tris: m.tris, yaw: +m.yaw.toFixed(1), detent: m.detent, s: +m.s.toFixed(3), d: +m.d.toFixed(3), az: +m.az.toFixed(1), L: +m.L.toFixed(2), u: +m.u.toFixed(2), line: +m.dbg.tl.line.toFixed(2), rail: +m.dbg.tl.rail.toFixed(2), cls: document.documentElement.className, sw: document.documentElement.scrollWidth }; });
    const settle = async (p, ms) => { const t0 = Date.now(); while (Date.now() - t0 < ms) { await p.waitForTimeout(300); if (!(await p.evaluate(() => window.__m.running))) break; } await p.waitForTimeout(150); };
    const shot = async (p, label) => { await p.screenshot({ path: OUT + name + '-' + label + '.png' }); report[name + '-' + label] = await info(p); };

    // hero after the real arrival settles; anchors for the later stops
    let { ctx, p } = await open('');
    await p.waitForFunction(() => document.documentElement.classList.contains('rdy') && window.__m.detent === 0, { timeout: 180000 });
    await settle(p, 20000);
    const A = await p.evaluate(() => { const D = window.__m.dbg, o = {}; for (const k in D.tl.A) o[k] = +(D.tl.A[k] / D.stage.S).toFixed(4); return o; });
    report[name + '-anchors'] = A;
    if (!only || only.includes('hero')) await shot(p, 'hero');
    if (!only || only.includes('yaw180')) {
      await p.click('#bb');
      await p.waitForFunction(() => window.__m.detent === 180, { timeout: 120000 });
      await settle(p, 20000);
      await shot(p, 'yaw180');
    }
    if (!only || only.includes('yaw90')) {
      await p.focus('#rot');
      await p.keyboard.press('Home');
      for (let i = 0; i < 6; i++) await p.keyboard.press('ArrowRight');
      await p.waitForFunction(() => Math.abs(window.__m.yaw - 90) < 0.5 && !window.__m.dbg.spin.core.busy, { timeout: 120000 });
      await settle(p, 20000);
      await shot(p, 'yaw90');
    }
    await ctx.close();

    for (const [label, f] of STOPS) {
      if (only && !only.includes(label)) continue;
      ({ ctx, p } = await open('&s=' + encodeURIComponent(f(A))));
      await settle(p, 15000);
      await shot(p, label);
      await ctx.close();
    }
  }
  await b.close();
  for (const k in report) console.log(k, JSON.stringify(report[k]));
})().catch(e => { console.error(e); process.exit(1); });
