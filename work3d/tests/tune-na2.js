// Light / material variants side by side. node tune-na2.js <w> <h> <coarse> <stop> <out.png> [cols] [scale] [clip x,y,w,h]
const { chromium } = require('playwright');
const fs = require('fs');
const PORT = process.env.PORT || 8361;
const VARIANTS = JSON.parse(fs.readFileSync(process.env.VARIANTS || __dirname + '/tune-variants.json', 'utf8'));
(async () => {
  const [w, h, coarse, stop, out, cols = '3', scale = '0.5', clipArg] = process.argv.slice(2);
  const clip = clipArg ? (([x, y, cw, ch]) => ({ x, y, width: cw, height: ch }))(clipArg.split(',').map(Number)) : undefined;
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: +w, height: +h }, deviceScaleFactor: 1, hasTouch: coarse === '1', isMobile: coarse === '1' });
  const p = await ctx.newPage();
  p.on('pageerror', e => console.log('pageerror: ' + e.message));
  await p.goto('http://127.0.0.1:' + PORT + '/merch?3d=1&s=' + encodeURIComponent(stop) + (process.env.Q ? '&q=' + process.env.Q : ''), { waitUntil: 'load' });
  await p.waitForFunction(() => window.__m && window.__m.ready, { timeout: 180000 });
  const files = [];
  for (const [name, v] of Object.entries(VARIANTS)) {
    await p.evaluate(v => {
      const D = window.__m.dbg, L = D.CFG.LIGHT, G = D.world.groups;
      const set = (o, patch) => { for (const k in patch) { if (patch[k] && typeof patch[k] === 'object' && !Array.isArray(patch[k]) && o[k]) set(o[k], patch[k]); else o[k] = patch[k]; } };
      if (v.LIGHT) set(L, v.LIGHT);
      const cloth = (list, c) => list.forEach(m => { const u = m.material.userData.cloth; if (u && c) { if (c.base !== undefined) u.value.x = c.base; if (c.rim !== undefined) u.value.y = c.rim; if (c.rimPow !== undefined) u.value.z = c.rimPow; if (c.color !== undefined) m.material.color.setHex(c.color); if (c.roughness !== undefined) m.material.roughness = c.roughness; if (c.sheenColor !== undefined && m.material.sheenColor) m.material.sheenColor.setHex(c.sheenColor); } });
      cloth(G.tee, v.CLOTH); cloth(G.pants.concat(G.other), v.PANTS);
      if (v.PLASTER) G.body.concat(G.hair).forEach(m => { if (v.PLASTER.color !== undefined) m.material.color.setHex(v.PLASTER.color); if (v.PLASTER.roughness !== undefined) m.material.roughness = v.PLASTER.roughness; });
      if (v.yaw !== undefined) { D.spin.core.x = v.yaw; }
      D.loop.wake();
    }, v);
    const t0 = Date.now(); while (Date.now() - t0 < 8000) { await p.waitForTimeout(250); if (!(await p.evaluate(() => window.__m.running))) break; }
    const f = __dirname + '/tmp/tune-' + name + '.png';
    await p.screenshot({ path: f, clip });
    files.push(f);
  }
  await b.close();
  require('child_process').execFileSync('node', [__dirname + '/sheet.js', out, cols, scale, ...files], { stdio: 'inherit' });
})().catch(e => { console.error(e); process.exit(1); });
