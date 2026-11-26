// Light / material variants side by side.
//   node tune-na2.js <w> <h> <coarse 0|1> <stop> <out.png> [cols] [scale] [clip x,y,w,h]
//   stop: a scroll position in screens or an anchor such as info@0.3 (the ?s= hook)
//   VARIANTS=<file.json> (default tune-variants.json): { name: { color: 'white', LIGHT: {…}, CLOTH: {…}, PANTS: {…}, PLASTER: {…}, yaw: 180 }, … }
//   CLOTH takes base, rim, rimPow, color, roughness, sheenColor and is applied to the tee as it is after `color` was chosen.
const fs = require('fs');
const { chromium, open, ready, settle } = require('./lib-na2.js');
const VARIANTS = JSON.parse(fs.readFileSync(process.env.VARIANTS || __dirname + '/tune-variants.json', 'utf8'));
(async () => {
  const [w, h, coarse, stop, out, cols = '3', scale = '0.5', clipArg] = process.argv.slice(2);
  const clip = clipArg ? (([x, y, cw, ch]) => ({ x, y, width: cw, height: ch }))(clipArg.split(',').map(Number)) : undefined;
  const b = await chromium.launch();
  const { p } = await open(b, { width: +w, height: +h, coarse: coarse === '1' }, '&s=' + encodeURIComponent(stop) + (process.env.Q ? '&q=' + process.env.Q : ''));
  await ready(p);
  const files = [];
  for (const [name, v] of Object.entries(VARIANTS)) {
    await p.evaluate(c => { window.__m.color = c; }, v.color || 'black');
    await settle(p);
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
    await settle(p, 8000);
    const f = __dirname + '/tmp/tune-' + name + '.png';
    await p.screenshot({ path: f, clip });
    files.push(f);
  }
  await b.close();
  require('child_process').execFileSync('node', [__dirname + '/sheet.js', out, cols, scale, ...files], { stdio: 'inherit' });
})().catch(e => { console.error(e); process.exit(1); });
