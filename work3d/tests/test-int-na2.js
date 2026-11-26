// Interaction checks for the NA2 page (SPEC 3 as changed by SPEC-NA2 E, and 7.2). node test-int-na2.js
const { chromium } = require('playwright');
const URL = 'http://127.0.0.1:' + (process.env.PORT || 8361) + '/merch?3d=1';
const results = [];
const ok = (name, pass, note) => { results.push({ name, pass: !!pass, note: note === undefined ? '' : String(note) }); console.log((pass ? 'PASS ' : 'FAIL ') + name + (note !== undefined ? '  — ' + note : '')); };
const M = p => p.evaluate(() => { const m = window.__m; return { yaw: m.yaw, detent: m.detent, s: m.s, d: m.d, L: m.L, y: scrollY, busy: m.dbg.spin.core.busy, mode: m.dbg.spin.core.mode, near: m.dbg.tl.near, nearOn: m.dbg.tl.nearOn, cls: document.documentElement.className }; });
const ready = async p => {
  await p.waitForFunction(() => window.__m && (window.__m.ready || window.__m.fallback), { timeout: 180000 });
  await p.waitForFunction(() => document.documentElement.classList.contains('rdy') && window.__m.detent === 0, { timeout: 180000 });
};
const rest = (p, t = 120000) => p.waitForFunction(() => !window.__m.dbg.spin.core.busy, { timeout: t });
const frames = (p, n = 6) => p.evaluate(n => new Promise(r => { let i = 0; (function f() { if (++i > n) r(); else requestAnimationFrame(f); })(); }), n);

(async () => {
  const b = await chromium.launch();
  const errors = [];

  /* ---------- mouse (desktop, fine pointer) ---------- */
  {
    const ctx = await b.newContext({ viewport: { width: 1024, height: 768 }, deviceScaleFactor: 1 });
    const p = await ctx.newPage();
    p.on('pageerror', e => errors.push('pageerror ' + e.message));
    p.on('console', m => { if (m.type() === 'error') errors.push('console ' + m.text()); });
    await p.goto(URL + '&q=1', { waitUntil: 'load' });
    await ready(p);
    const cx = 700, cy = 380;   // on the figure, away from controls

    // slow 200 px drag
    let a = await M(p);
    await p.mouse.move(cx - 100, cy); await p.mouse.down();
    for (let i = 1; i <= 20; i++) { await p.mouse.move(cx - 100 + i * 10, cy); await p.waitForTimeout(30); }
    await frames(p, 3);
    let mid = await M(p);
    ok('mouse drag 200 px changes yaw', Math.abs(((mid.yaw - a.yaw + 540) % 360) - 180) > 40, 'yaw ' + a.yaw.toFixed(1) + ' → ' + mid.yaw.toFixed(1) + ' (0.40°/px → 80°), class "' + mid.cls + '"');
    ok('cursor state: html has class drag while dragging', /\bdrag\b/.test(mid.cls));
    await p.waitForTimeout(200); await p.mouse.up();
    await rest(p);
    let c = await M(p);
    ok('slow release rests (no detent pull far from one)', c.mode === 'rest', 'yaw ' + c.yaw.toFixed(1) + ' detent ' + c.detent);

    // fast flick
    await p.mouse.move(cx - 150, cy); await p.mouse.down();
    await p.mouse.move(cx + 150, cy, { steps: 6 });
    await p.mouse.up();
    await frames(p, 2);
    const fl = await M(p);
    await rest(p);
    c = await M(p);
    ok('fast flick settles on a detent', c.detent === 0 || c.detent === 180, 'mode after release "' + fl.mode + '", settled yaw ' + c.yaw.toFixed(2) + ' detent ' + c.detent);
    const pressed = await p.evaluate(() => [bf.getAttribute('aria-pressed'), bb.getAttribute('aria-pressed'), live.textContent]);
    ok('aria-pressed mirrors the settled detent', (c.detent === 0 && pressed[0] === 'true' && pressed[1] === 'false') || (c.detent === 180 && pressed[1] === 'true' && pressed[0] === 'false'), pressed.join(' | '));

    // buttons
    await p.click('#bb'); await rest(p); c = await M(p);
    ok('"Nugara" sends the figure to 180°', c.detent === 180, 'yaw ' + c.yaw.toFixed(2) + ', live "' + await p.evaluate(() => live.textContent) + '"');
    await p.click('#bf'); await rest(p); c = await M(p);
    ok('"Priekis" sends the figure to 0°', c.detent === 0, 'yaw ' + c.yaw.toFixed(2) + ', live "' + await p.evaluate(() => live.textContent) + '"');

    // Iš arti: camera eases to PRINT without scrolling; second press releases
    const d0 = c.d;
    await p.click('#bz');
    await p.waitForFunction(() => window.__m.dbg.tl.near === 1, { timeout: 60000 });
    c = await M(p);
    const dChest = await p.evaluate(() => window.__m.dbg.tl.dChest);
    ok('"Iš arti" at the front eases the camera to CHEST without scrolling', Math.abs(c.d - dChest) < 0.01 && c.y === 0 && (await p.evaluate(() => bz.getAttribute('aria-pressed'))) === 'true', 'd ' + d0.toFixed(2) + ' → ' + c.d.toFixed(2) + ' (CHEST ' + dChest.toFixed(2) + '), scrollY ' + c.y);
    await frames(p, 4);
    await p.screenshot({ path: __dirname + '/shots-na2/1024x768-near-front.png' });
    await p.keyboard.press('Escape');
    await p.waitForFunction(() => window.__m.dbg.tl.near === 0, { timeout: 60000 });
    c = await M(p);
    ok('Esc releases "Iš arti"', Math.abs(c.d - d0) < 0.01 && (await p.evaluate(() => bz.getAttribute('aria-pressed'))) === 'false', 'd ' + c.d.toFixed(2));
    await p.click('#bz'); await p.waitForFunction(() => window.__m.dbg.tl.near === 1, { timeout: 60000 });
    await p.click('#bz'); await p.waitForFunction(() => window.__m.dbg.tl.near === 0, { timeout: 60000 });
    ok('second press releases "Iš arti"', true);
    await p.click('#bz'); await p.waitForFunction(() => window.__m.dbg.tl.near === 1, { timeout: 60000 });
    // in close-up a drag is limited to about ±35° and springs back to the front
    await p.mouse.move(cx - 150, cy); await p.mouse.down();
    for (let i = 1; i <= 15; i++) { await p.mouse.move(cx - 150 + i * 20, cy); await p.waitForTimeout(20); }
    await frames(p, 3);
    c = await M(p);
    const off = ((c.yaw + 180) % 360) - 180;
    ok('close-up drag is limited (±35° then ×0.35)', Math.abs(off) > 35 && Math.abs(off) < 70, 'dragged 300 px = 120° of hand travel → yaw ' + off.toFixed(1) + '°');
    await p.mouse.up(); await rest(p); c = await M(p);
    ok('close-up release springs back to the front', c.detent === 0, 'yaw ' + c.yaw.toFixed(2));
    // Iš arti with the figure turned round: the camera goes to the map (BACK pose for the rotated figure, az 0)
    await p.keyboard.press('Escape');
    await p.waitForFunction(() => window.__m.dbg.tl.near === 0, { timeout: 60000 });
    await p.click('#bb'); await rest(p);
    await p.click('#bz');
    await p.waitForFunction(() => window.__m.dbg.tl.near === 1, { timeout: 60000 });
    await rest(p); await frames(p, 4);
    const nb = await p.evaluate(() => { const D = window.__m.dbg, w = D.world, t = D.tl.pose.t, c = w.PB.getCenter(w.C.clone()); return { d: window.__m.d, dBack: Math.exp(D.tl.P.back.ln), az: window.__m.az, yaw: window.__m.yaw, detent: window.__m.detent, tx: t.x - (2 * w.axis.x - c.x), tz: t.z - (2 * w.axis.z - c.z), back: D.tl.nearBack, centre: D.spin.centre, close: D.spin.close }; });
    ok('"Iš arti" at the back eases the camera to the map (az 0, figure stays turned)', Math.abs(nb.d - nb.dBack) < 0.01 && Math.abs(nb.az) < 0.01 && nb.detent === 180 && Math.abs(nb.tx) < 1e-3 && Math.abs(nb.tz) < 1e-3 && nb.back && nb.close && nb.centre === 180, JSON.stringify(nb));
    await p.screenshot({ path: __dirname + '/shots-na2/1024x768-near-back.png' });
    await p.mouse.move(cx - 150, cy); await p.mouse.down();
    for (let i = 1; i <= 15; i++) { await p.mouse.move(cx - 150 + i * 20, cy); await p.waitForTimeout(20); }
    await frames(p, 3);
    c = await M(p);
    ok('close-up at the back: drag is limited round 180°', Math.abs(c.yaw - 180) > 35 && Math.abs(c.yaw - 180) < 70, 'yaw ' + c.yaw.toFixed(1));
    await p.mouse.up(); await rest(p); c = await M(p);
    ok('close-up at the back: release springs back to 180°', c.detent === 180, 'yaw ' + c.yaw.toFixed(2));
    await p.click('#bf'); await rest(p); c = await M(p);
    ok('"Priekis" releases "Iš arti" and turns the figure to the front', c.detent === 0 && !c.nearOn, 'yaw ' + c.yaw.toFixed(2) + ' nearOn ' + c.nearOn);
    await p.waitForFunction(() => window.__m.dbg.tl.near === 0, { timeout: 60000 });
    await p.click('#bz'); await p.waitForFunction(() => window.__m.dbg.tl.near === 1, { timeout: 60000 });
    await p.mouse.wheel(0, 0.4 * 768);
    await p.waitForFunction(() => !window.__m.dbg.tl.nearOn, { timeout: 60000 }).then(() => ok('0.35 S of scrolling releases "Iš arti"', true), () => ok('0.35 S of scrolling releases "Iš arti"', false));
    await p.mouse.wheel(0, -0.4 * 768);
    await p.waitForFunction(() => scrollY === 0 && !window.__m.running, { timeout: 60000 });

    // range input: arrows, Home, End
    await p.focus('#rot');
    await p.keyboard.press('ArrowRight'); await p.keyboard.press('ArrowRight');
    await rest(p); c = await M(p);
    const rv = await p.evaluate(() => [rot.value, rot.getAttribute('aria-valuetext'), hint.textContent, document.documentElement.classList.contains('kf')]);
    ok('range input: two ArrowRight turn the figure to 30°', Math.abs(c.yaw - 30) < 0.5, 'yaw ' + c.yaw.toFixed(2) + ' value/valuetext/hint/ring ' + rv.join(' | '));
    await p.keyboard.press('End'); await rest(p); c = await M(p);
    ok('range input: End → 345°', Math.abs(c.yaw - 345) < 0.5, 'yaw ' + c.yaw.toFixed(2));
    await p.keyboard.press('Home'); await rest(p); c = await M(p);
    ok('range input: Home → 0° (Priekis)', c.detent === 0 && (await p.evaluate(() => rot.getAttribute('aria-valuetext'))) === 'Priekis', 'yaw ' + c.yaw.toFixed(2));
    for (let i = 0; i < 12; i++) await p.keyboard.press('ArrowRight');
    await rest(p); c = await M(p);
    ok('range input: 180° reads "Nugara" and presses the button', c.detent === 180 && (await p.evaluate(() => rot.getAttribute('aria-valuetext') + '|' + bb.getAttribute('aria-pressed'))) === 'Nugara|true', 'yaw ' + c.yaw.toFixed(2));
    await p.keyboard.press('Home'); await rest(p);
    await p.evaluate(() => document.activeElement.blur());
    ok('outside the range input the hint is not the keyboard one', (await p.evaluate(() => hint.textContent)) !== '← → Suk.', await p.evaluate(() => JSON.stringify(hint.textContent)));

    await p.evaluate(() => { document.activeElement.blur(); window.scrollTo(0, 0); });

    // wheel from top to bottom is never blocked, and the script never moves the page
    const total = await p.evaluate(() => document.documentElement.scrollHeight - innerHeight);
    let last = 0, stuck = 0, steps = 0, maxStuck = 0;
    while (last < total - 2 && steps < 400) {
      await p.mouse.wheel(0, 240); steps++;
      await p.waitForTimeout(40);
      const y = await p.evaluate(() => scrollY);
      if (y <= last) { stuck++; maxStuck = Math.max(maxStuck, stuck); if (stuck > 25) break; } else stuck = 0;
      if (y < last - 1) { ok('scroll never goes backwards', false, last + ' → ' + y); break; }
      last = Math.max(last, y);
    }
    ok('wheel scrolls from top to bottom without being blocked', last >= total - 2, 'reached ' + last + ' of ' + total + ' in ' + steps + ' wheel steps');
    await p.waitForTimeout(1500);
    const f0 = await p.evaluate(() => window.__m.frames);
    await p.waitForTimeout(2000);
    const f1 = await p.evaluate(() => [window.__m.frames, window.__m.running, window.__m.dbg.tl.asleep]);
    ok('scrolled past the rack: no rAF callbacks for 2 s', f1[0] === f0 && !f1[1], 'frames ' + f0 + ' → ' + f1[0] + ', asleep ' + f1[2]);

    // jump to #albumas and back: dip, no fly-through
    await p.evaluate(() => window.scrollTo(0, 0));
    await p.waitForFunction(() => !window.__m.running && window.__m.s === 0, { timeout: 60000 });
    await p.click('a[href="#albumas"]');
    await p.waitForTimeout(300);
    let j = await p.evaluate(() => ({ y: scrollY, s: window.__m.s * window.__m.dbg.stage.S, op: gl.style.opacity, asleep: window.__m.dbg.tl.asleep }));
    ok('jump to #albumas: applied scroll snaps, canvas dips', Math.abs(j.y - j.s) < 2 && j.y > 1000, 'scrollY ' + j.y + ' applied ' + Math.round(j.s) + ' canvas opacity ' + j.op);
    await p.evaluate(() => window.scrollTo(0, 0));
    await p.waitForFunction(() => window.__m.s === 0 && getComputedStyle(gl).opacity === '1', { timeout: 60000 }).then(() => ok('jump back to the top: canvas returns', true), () => ok('jump back to the top: canvas returns', false));

    // lightbox from the grid: opens, traps focus, Esc closes, focus returns, renderer sleeps while open
    const visible = () => p.evaluate(() => [].filter.call(document.querySelectorAll('button[data-src]'), b => b.getClientRects().length).map(b => b.getAttribute('data-src')));
    const all = await visible();
    ok('3D mode: the lightbox set is the two plate photos and the nine grid photos', all.length === 11 && all[0] === '/merch/v/ph/print-1600.jpg' && all[1] === '/merch/v/ph/back-1600.jpg' && all[2] === '/merch/p/01.jpg', all.join(' '));
    const two = n => (n < 10 ? '0' : '') + n;
    const btn = p.locator('.g .z').nth(3);
    await btn.scrollIntoViewIfNeeded();
    await btn.click();
    await p.waitForSelector('#v[open]');
    const lb = await p.evaluate(() => ({ n: vn.textContent, focus: document.activeElement.id, src: document.querySelector('#v img').getAttribute('src'), bg: document.querySelector('#v img').style.backgroundImage, lock: document.documentElement.classList.contains('lock') }));
    ok('lightbox opens on the clicked grid photo', lb.n.startsWith('06 / 11') && lb.focus === 'vc' && lb.src === '/merch/p/04.jpg' && lb.lock, JSON.stringify(lb));
    ok('lightbox placeholder is the 1024 px file', /\/merch\/v\/g\/04\.jpg/.test(lb.bg), lb.bg);
    const fz = await p.evaluate(() => [window.__m.frames, window.__m.running]); await p.waitForTimeout(1000);
    ok('renderer sleeps while the lightbox is open', (await p.evaluate(() => window.__m.frames)) === fz[0] && !fz[1], 'frames ' + fz[0]);
    const seq = [];
    for (let i = 0; i < 4; i++) { await p.keyboard.press('Tab'); seq.push(await p.evaluate(() => document.activeElement.id)); }
    ok('lightbox traps focus', seq.every(id => ['vc', 'vp', 'vx'].includes(id)), seq.join(' > '));
    await p.keyboard.press('ArrowRight');
    ok('lightbox arrows step', /^07 \/ 11/.test(await p.evaluate(() => vn.textContent)));
    await p.keyboard.press('Escape');
    await p.waitForFunction(() => !document.getElementById('v').hasAttribute('open') && !document.documentElement.classList.contains('lock'));
    const back = await p.evaluate(() => document.activeElement === document.querySelectorAll('.g .z')[3]);
    ok('lightbox returns focus to the opener', back);
    const viaHook = await p.evaluate(() => { const bs = document.querySelectorAll('.g .z'); window.__lb.open(bs[1], bs[7]); return vn.textContent.slice(0, 7); });
    await p.keyboard.press('Escape');
    await p.waitForFunction(() => !document.getElementById('v').hasAttribute('open') && !document.documentElement.classList.contains('lock'));
    ok('window.__lb.open(button, returnFocusEl) works', viaHook === '04 / 11' && await p.evaluate(() => document.activeElement === document.querySelectorAll('.g .z')[7]), viaHook);

    // the two new photo buttons inside the plates
    for (const [sel, src, nth, small] of [['#priekis .ph--print .z', '/merch/v/ph/print-1600.jpg', '01 / 11', 'print-800.jpg'], ['#nugara .ph .z', '/merch/v/ph/back-1600.jpg', '02 / 11', 'back-800.jpg']]) {
      const ph = p.locator(sel);
      await ph.scrollIntoViewIfNeeded();
      await p.waitForFunction(sel => { const i = document.querySelector(sel + ' img'); return i.complete && i.naturalWidth > 0; }, sel, { timeout: 30000 });
      await ph.click();
      await p.waitForSelector('#v[open]');
      const o = await p.evaluate(() => ({ n: vn.textContent.slice(0, 7), focus: document.activeElement.id, src: document.querySelector('#v img').getAttribute('src'), alt: document.querySelector('#v img').alt, bg: document.querySelector('#v img').style.backgroundImage }));
      const seq2 = [];
      for (let i = 0; i < 4; i++) { await p.keyboard.press('Tab'); seq2.push(await p.evaluate(() => document.activeElement.id)); }
      await p.waitForFunction(() => { const i = document.querySelector('#v img'); return i.complete && i.naturalWidth > 0; }, null, { timeout: 30000 });
      if (/print/.test(src)) await p.screenshot({ path: __dirname + '/shots-na2/lightbox-print-1024x768.png' });
      await p.keyboard.press('Escape');
      await p.waitForFunction(() => !document.getElementById('v').hasAttribute('open') && !document.documentElement.classList.contains('lock'));
      const ret = await p.evaluate(sel => document.activeElement === document.querySelector(sel), sel);
      ok('photo button ' + sel + ' opens the lightbox, traps focus and gets it back', o.n === nth && o.focus === 'vc' && o.src === src && o.alt.length > 20 && o.bg.includes(small) && seq2.every(id => ['vc', 'vp', 'vx'].includes(id)) && ret, JSON.stringify(o) + ' tab ' + seq2.join('>') + ' returned ' + ret);
    }

    // tab order through the whole page
    await p.evaluate(() => { window.scrollTo(0, 0); document.activeElement.blur(); });
    await p.waitForFunction(() => scrollY === 0 && !window.__m.running, { timeout: 60000 });
    const order = [];
    for (let i = 0; i < 26; i++) {
      await p.keyboard.press('Tab');
      order.push(await p.evaluate(() => { const a = document.activeElement; if (!a || a === document.body) return 'body'; const src = a.getAttribute('data-src'); return a.id || (src ? src.replace('/merch/', '') : (a.textContent || '').trim().slice(0, 14)); }));
    }
    const wantOrder = ['Į turinį', 'OG Version', 'Albumas', 'rot', 'bf', 'bb', 'bz', 'v/ph/print-1600.jpg', 'v/ph/back-1600.jpg', 'sv', 'p/01.jpg', 'p/02.jpg', 'p/03.jpg', 'p/04.jpg', 'p/05.jpg', 'p/06.jpg', 'p/07.jpg', 'p/08.jpg', 'p/09.jpg', 'Klausyti YouTu', 'ogversion.com', '47 Studio', 'Radio'];
    ok('tab order: skip link, brand, Albumas, range input, Priekis, Nugara, Iš arti, photo print, photo back, Šviesa, nine grid buttons, album link, footer links', wantOrder.every((w, i) => order[i] === w), order.join(' | '));
    await p.evaluate(() => { document.activeElement.blur(); window.scrollTo(0, 0); });
    await ctx.close();
  }

  /* ---------- touch (phone, coarse pointer) ---------- */
  {
    const ctx = await b.newContext({ viewport: { width: 390, height: 664 }, deviceScaleFactor: 1, hasTouch: true, isMobile: true });
    const p = await ctx.newPage();
    p.on('pageerror', e => errors.push('pageerror ' + e.message));
    p.on('console', m => { if (m.type() === 'error') errors.push('console ' + m.text()); });
    await p.goto(URL, { waitUntil: 'load' });
    await ready(p);
    const cdp = await ctx.newCDPSession(p);
    const touch = async (pts, pause = 16) => {
      await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: pts[0][0], y: pts[0][1] }] });
      for (let i = 1; i < pts.length; i++) { await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: pts[i][0], y: pts[i][1] }] }); await p.waitForTimeout(pause); }
      await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    };
    const line = (x0, y0, x1, y1, n) => Array.from({ length: n + 1 }, (_, i) => [Math.round(x0 + (x1 - x0) * i / n), Math.round(y0 + (y1 - y0) * i / n)]);
    ok('coarse pointer starts at Q1 with DPR ≤ 1.5', await p.evaluate(() => window.__m.tier === 1 && window.__m.dpr <= 1.5), await p.evaluate(() => 'tier ' + window.__m.tier + ' dpr ' + window.__m.dpr));

    // vertical drag: page scrolls, yaw unchanged
    let a = await M(p);
    await touch(line(195, 420, 195, 220, 12));
    await p.waitForTimeout(600);
    let c = await M(p);
    ok('vertical touch drag scrolls the page and leaves yaw unchanged', c.y > 100 && Math.abs(c.yaw - a.yaw) < 0.01, 'scrollY ' + a.y + ' → ' + c.y + ', yaw ' + a.yaw.toFixed(2) + ' → ' + c.yaw.toFixed(2));
    await p.evaluate(() => window.scrollTo(0, 0));
    await p.waitForFunction(() => scrollY === 0 && !window.__m.running, { timeout: 60000 });

    // horizontal drag: spins, no scroll; "Suk." goes for good
    a = await M(p);
    const hintBefore = await p.evaluate(() => hint.textContent);
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: 110, y: 330 }] });
    for (const [x, y] of line(110, 330, 270, 334, 16).slice(1)) { await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x, y }] }); await p.waitForTimeout(25); }
    await frames(p, 3);
    c = await M(p);
    ok('horizontal touch drag spins the figure and does not scroll', Math.abs(c.yaw - a.yaw) > 40 && c.y === 0, 'yaw ' + a.yaw.toFixed(1) + ' → ' + c.yaw.toFixed(1) + ' for 160 px (0.56°/px), scrollY ' + c.y);
    await p.waitForTimeout(250);
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    ok('"Suk." goes for good after the first spin', hintBefore === 'Suk.' && (await p.evaluate(() => hint.textContent)) === '', JSON.stringify(hintBefore) + ' → ' + JSON.stringify(await p.evaluate(() => hint.textContent)));
    await rest(p);
    await p.tap('#bf'); await rest(p);

    // edge start: nothing
    a = await M(p);
    await touch(line(10, 330, 170, 332, 12));
    await p.waitForTimeout(400);
    c = await M(p);
    ok('a drag starting 10 px from the edge does nothing', Math.abs(c.yaw - a.yaw) < 0.01 && c.y === a.y && c.mode === 'rest', 'yaw ' + c.yaw.toFixed(2) + ' scrollY ' + c.y);

    // drag starting on a button: nothing
    const bb = await p.locator('#bb').boundingBox();
    await touch(line(bb.x + 20, bb.y + 20, bb.x + 180, bb.y + 22, 12));
    await p.waitForTimeout(400);
    c = await M(p);
    ok('a drag starting on a button does not spin', c.mode === 'rest' && (c.detent === 0 || c.detent === 180), 'mode ' + c.mode);
    await p.tap('#bf'); await rest(p);

    // a tap on the figure does nothing (no poke any more)
    a = await M(p);
    await p.touchscreen.tap(195, 300);
    await frames(p, 3);
    c = await M(p);
    ok('a tap on the figure changes nothing', Math.abs(c.yaw - a.yaw) < 0.01 && c.mode === 'rest' && c.y === a.y && !(await p.evaluate(() => document.getElementById('v').hasAttribute('open'))), 'yaw ' + c.yaw.toFixed(2) + ' mode ' + c.mode);
    await p.waitForFunction(() => !window.__m.running, { timeout: 120000 }).then(() => ok('everything settles and the loop stops (within the idle window)', true), () => ok('everything settles and the loop stops (within the idle window)', false));
    const f0 = await p.evaluate(() => window.__m.frames); await p.waitForTimeout(2000);
    ok('idle: no rAF callbacks for 2 s', (await p.evaluate(() => window.__m.frames)) === f0);

    // HUD off while scrolled: inert, nothing in it takes focus
    await p.evaluate(() => window.scrollTo(0, Math.round(0.5 * innerHeight)));
    await p.waitForFunction(() => document.documentElement.classList.contains('hud-off') && !window.__m.running, { timeout: 60000 });
    await p.waitForTimeout(300);
    const off1 = await p.evaluate(() => { const h = document.querySelector('.hud'); bf.focus(); return { inert: h.inert, focusTaken: document.activeElement === bf, vis: getComputedStyle(h).visibility, line: getComputedStyle(document.querySelector('.hero__f')).visibility }; });
    ok('HUD is off and inert past 0.15 S', off1.inert && !off1.focusTaken && off1.vis === 'hidden' && off1.line === 'hidden', JSON.stringify(off1));
    await p.evaluate(() => window.scrollTo(0, Math.round(0.12 * innerHeight)));
    await p.waitForFunction(() => !window.__m.running, { timeout: 60000 });
    ok('HUD stays off between 0.10 S and 0.15 S on the way back (hysteresis)', await p.evaluate(() => document.documentElement.classList.contains('hud-off')));
    await p.evaluate(() => window.scrollTo(0, 0));
    await p.waitForFunction(() => !document.documentElement.classList.contains('hud-off') && !window.__m.running, { timeout: 60000 });
    ok('HUD returns below 0.10 S', await p.evaluate(() => !document.querySelector('.hud').inert));

    // Šviesa: scroll default, press override, Esc, leaving the range
    const at = (id, t) => p.evaluate(([id, t]) => Math.round(window.__m.at(id, t) * window.__m.dbg.stage.S), [id, t]);
    const go = async y => { await p.evaluate(y => window.scrollTo(0, y), y); await p.waitForFunction(y => Math.abs(window.__m.s * window.__m.dbg.stage.S - y) < 1 && !window.__m.running, y, { timeout: 90000 }); };
    await go(await at('sk', 0.5));
    c = await M(p);
    ok('before sk@0.62 the lights are on', c.L === 0 && (await p.evaluate(() => sv.getAttribute('aria-pressed'))) === 'true', 'L ' + c.L);
    await go(await at('sk', 0.9));
    c = await M(p);
    ok('past sk@0.62 the lights are out and "Šviesa" is not pressed', c.L === 1 && (await p.evaluate(() => sv.getAttribute('aria-pressed'))) === 'false', 'L ' + c.L);
    await p.tap('#sv');
    await p.waitForFunction(() => window.__m.L === 0, { timeout: 60000 });
    ok('"Šviesa" turns the lights back on', (await p.evaluate(() => sv.getAttribute('aria-pressed'))) === 'true');
    await p.keyboard.press('Escape');
    await p.waitForFunction(() => window.__m.L === 1, { timeout: 60000 }).then(() => ok('Esc clears the lights override', true), () => ok('Esc clears the lights override', false));
    await p.tap('#sv');
    await p.waitForFunction(() => window.__m.L === 0, { timeout: 60000 });
    await go(await at('sk', 0.1));
    await go(await at('sk', 0.9));
    c = await M(p);
    ok('leaving sk@0.2 … tiek@0.7 drops the override', c.L === 1, 'L ' + c.L);
    // wiggle in the dark beat: ±35° limit holds, line stays (it is a child of the shirt)
    a = await M(p);
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: 120, y: 200 }] });
    for (const [x, y] of line(120, 200, 300, 202, 12).slice(1)) { await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x, y }] }); await p.waitForTimeout(25); }
    await frames(p, 3);
    c = await M(p);
    const off = ((c.yaw + 180) % 360) - 180;
    await p.screenshot({ path: __dirname + '/shots-na2/390x664-dark-wiggle.png' });
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    const lit = await p.evaluate(() => { const D = window.__m.dbg, w = D.world; return { lit: w.printLit.visible, line: w.lineRed.visible, lineParent: w.lineRed.parent === w.content, litParent: w.printLit.parent === w.printBack.parent, calls: window.__m.calls, az: window.__m.az }; });
    ok('wiggle in the dark beat: the back follows the finger about 1:1, stays inside ±35°, map and red line stay on the cloth', Math.abs(off) > 10 && Math.abs(off) <= 35.5 && lit.lit && lit.line && lit.lineParent && lit.litParent, '180 px → yaw ' + off.toFixed(1) + '°; lit map ' + lit.lit + ', red line ' + lit.line + ' (child of the figure: ' + lit.lineParent + '), camera az ' + lit.az.toFixed(1) + ', draw calls ' + lit.calls);
    await rest(p);

    // resize: phone turned on its side
    await p.evaluate(() => window.scrollTo(0, 0));
    await p.setViewportSize({ width: 844, height: 390 });
    await p.waitForFunction(() => window.__m.dbg.stage.W === 844 && !window.__m.dbg.stage.portrait && !window.__m.running, { timeout: 60000 }).then(() => ok('resize to landscape re-measures the stage', true), () => ok('resize to landscape re-measures the stage', false));
    await frames(p, 4);
    await p.screenshot({ path: __dirname + '/shots-na2/resize-390x664-to-844x390.png' });
    const rs = await p.evaluate(() => { const D = window.__m.dbg; const r = document.querySelector('.fr-hero').getBoundingClientRect(); return { fov: D.stage.camera.fov, cx: D.tl.pose.cx, frame: r.left + r.width / 2, sw: document.documentElement.scrollWidth }; });
    ok('after the resize the figure sits in the new frame (FOV 30°, no h-scroll)', rs.fov === 30 && Math.abs(rs.cx - rs.frame) < 1 && rs.sw <= 844, JSON.stringify(rs));
    await ctx.close();
  }

  /* ---------- quality overrides render without errors ---------- */
  for (const q of [0, 2, 3]) {
    const ctx = await b.newContext({ viewport: { width: 390, height: 664 }, deviceScaleFactor: 2, hasTouch: true, isMobile: true });
    const p = await ctx.newPage();
    const errs = [];
    p.on('pageerror', e => errs.push(e.message)); p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
    await p.goto(URL + '&q=' + q + '&s=sk@0.95', { waitUntil: 'load' });
    await p.waitForFunction(() => window.__m && (window.__m.ready || window.__m.fallback), { timeout: 120000 });
    await p.waitForFunction(() => window.__m.L === 1 && !window.__m.running, { timeout: 120000 }).catch(() => {});
    const m = await p.evaluate(() => ({ ready: window.__m.ready, tier: window.__m.tier, dpr: window.__m.dpr, calls: window.__m.calls, rimR: window.__m.dbg.world.rimR.intensity, phys: !!window.__m.dbg.world.groups.tee[0].material.isMeshPhysicalMaterial, L: window.__m.L }));
    const cap = [1.5, 1.5, 1.25, 1][q];   // coarse pointer: never above 1.5
    ok('?q=' + q + ' renders the dark beat without errors (DPR ≤ ' + cap + ' on a 2× phone)', m.ready && m.tier === q && m.dpr <= cap && errs.length === 0 && m.L === 1 && (q !== 0 || m.phys) && (q !== 3 || m.rimR === 0), JSON.stringify(m) + (errs.length ? ' ' + errs.join(';') : ''));
    await ctx.close();
  }

  await b.close();
  ok('no console errors or page errors during the interaction run', errors.length === 0, errors.join(' ; '));
  require('fs').writeFileSync(__dirname + '/tmp/test-int-na2.json', JSON.stringify(results, null, 1));
  console.log(results.filter(r => !r.pass).length + ' failed of ' + results.length);
})().catch(e => { console.error(e); process.exit(1); });
