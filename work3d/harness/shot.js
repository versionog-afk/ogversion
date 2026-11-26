// Usage: node work3d/harness/shot.js <model .glb inside the repository> <output dir> [front.png] [back.png]   (needs: npm install in work3d/)
// Renders the standard views with the shared viewer and writes contact sheets + stats.json with contract checks.
// Do not edit: every model version is judged with this file.
const http = require('http'), fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const ROOT = path.resolve(__dirname, '../..'); // repository root
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.glb': 'model/gltf-binary', '.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp', '.json': 'application/json', '.wasm': 'application/wasm', '.bin': 'application/octet-stream' };
const rel = p => '/' + path.relative(ROOT, path.resolve(p));
(async () => {
  const model = path.resolve(process.argv[2]), out = path.resolve(process.argv[3]);
  if (!model.startsWith(ROOT + '/')) { console.error('model must be inside ' + ROOT); process.exit(2); }
  fs.mkdirSync(out, { recursive: true });
  const srv = http.createServer((req, res) => {
    const p = path.normalize(path.join(ROOT, decodeURIComponent(req.url.split('?')[0])));
    if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end('nf'); }
    res.writeHead(200, { 'content-type': MIME[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(res);
  });
  await new Promise(r => srv.listen(0, '127.0.0.1', r));
  const base = 'http://127.0.0.1:' + srv.address().port;
  const b = await chromium.launch();
  const T = 560, p = await b.newPage({ viewport: { width: T, height: T }, deviceScaleFactor: 1 });
  const errs = []; p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); }); p.on('pageerror', e => errs.push(e.message));
  let url = base + '/work3d/harness/viewer.html?model=' + encodeURIComponent(rel(model));
  if (process.argv[4]) url += '&front=' + encodeURIComponent(rel(process.argv[4]));
  if (process.argv[5]) url += '&back=' + encodeURIComponent(rel(process.argv[5]));
  await p.goto(url); await p.waitForFunction(() => window.__ready, { timeout: 240000 });
  const stats = await p.evaluate(() => window.__stats) || {};
  stats.fileBytes = fs.statSync(model).size; stats.errors = errs.concat(await p.evaluate(() => window.__errors));
  const w = [];
  if (!stats.meshes) w.push('MODEL DID NOT LOAD');
  else {
    const c = stats.counts;
    if (!c.tee) w.push('no shirt mesh (name it Tee, material Fabric)');
    if (c.printFront !== 1) w.push('need exactly one mesh named PrintFront, found ' + c.printFront);
    if (c.printBack !== 1) w.push('need exactly one mesh named PrintBack, found ' + c.printBack);
    if (!c.body) w.push('no body mesh (name it Body)');
    if (!c.pants) w.push('no trousers mesh (name it Pants)');
    if (c.other) w.push(c.other + ' mesh(es) with unrecognised names: ' + stats.meshes.filter(m => m.cls === 'other').map(m => m.mesh).join(', '));
    if (stats.triangles > 130000) w.push('more than 130k triangles: ' + stats.triangles);
    const H = stats.figureMaxY - stats.figureMinY;
    if (c.body && (H < 1.55 || H > 1.85)) w.push('figure height ' + H.toFixed(3) + ' m outside 1.55-1.85');
    if (c.body && Math.abs(stats.figureMinY) > 0.02) w.push('lowest point is at y = ' + stats.figureMinY + ', the figure must stand on y = 0');
    const pf = stats.printFrontSizeM, pb = stats.printBackSizeM;
    if (pf) { if (pf[0] < 0.09 || pf[0] > 0.13) w.push('PrintFront width ' + pf[0] + ' m, expected about 0.105'); if (stats.printFrontCenterM[0] < 0.03) w.push('PrintFront must sit on the wearer\'s left chest (+X, centre x at least 0.03), got x = ' + stats.printFrontCenterM[0]); if (stats.printFrontNormal && stats.printFrontNormal[2] < 0.6) w.push('PrintFront must face +Z, average normal ' + stats.printFrontNormal); }
    if (pb) { if (pb[0] < 0.32 || pb[0] > 0.44) w.push('PrintBack width ' + pb[0] + ' m, expected about 0.38'); if (Math.abs(stats.printBackCenterM[0]) > 0.02) w.push('PrintBack must be centred on the back, got x = ' + stats.printBackCenterM[0]); if (stats.printBackNormal && stats.printBackNormal[2] > -0.6) w.push('PrintBack must face -Z, average normal ' + stats.printBackNormal); }
    if (stats.fileBytes > 8e6) w.push('file larger than 8 MB');
  }
  stats.contractWarnings = w;
  const SHEETS = { 'studio-full': ['studio', ['full-front', 'full-q34', 'full-side', 'full-back']], 'studio-top': ['studio', ['top-front', 'top-q34', 'top-side', 'top-back', 'top-q34b', 'top-high']], 'clay-top': ['clay', ['top-front', 'top-q34', 'top-side', 'top-back', 'top-low', 'neck']], 'dark': ['dark', ['top-front', 'top-q34', 'top-back', 'top-q34b', 'full-q34', 'neck']], 'prints': ['studio', ['close-front', 'close-back']], 'uv': ['uv', ['close-front', 'close-back']] };
  if (stats.meshes) for (const [name, [look, views]] of Object.entries(SHEETS)) {
    const imgs = [];
    for (const v of views) { await p.evaluate(([v, l]) => window.__shoot(v, l), [v, look]); imgs.push({ v, data: (await p.screenshot({ type: 'png' })).toString('base64') }); }
    const cols = views.length > 4 ? 3 : 2, sp = await b.newPage({ viewport: { width: cols * T, height: Math.ceil(views.length / cols) * T } });
    await sp.setContent('<body style="margin:0;background:#000;display:grid;grid-template-columns:repeat(' + cols + ',' + T + 'px);font:600 18px sans-serif">' +
      imgs.map(i => '<div style="position:relative"><img style="display:block" src="data:image/png;base64,' + i.data + '"><span style="position:absolute;left:10px;top:8px;color:#fff;background:#000a;padding:2px 8px">' + look + ' / ' + i.v + '</span></div>').join('') + '</body>');
    await sp.screenshot({ path: path.join(out, 'sheet-' + name + '.png') }); await sp.close();
  }
  if (stats.meshes) {
    await p.setViewportSize({ width: 900, height: 1200 });
    for (const [v, l, n] of [['top-q34', 'dark', 'hero-dark-front'], ['top-q34b', 'dark', 'hero-dark-back'], ['close-back', 'dark', 'hero-dark-map'], ['close-front', 'dark', 'hero-dark-na2']]) { await p.evaluate(([v, l]) => window.__shoot(v, l), [v, l]); await p.screenshot({ path: path.join(out, n + '.png') }); }
  }
  fs.writeFileSync(path.join(out, 'stats.json'), JSON.stringify(stats, null, 1));
  console.log(JSON.stringify(stats, null, 1));
  await b.close(); srv.close();
})().catch(e => { console.error(e); process.exit(1); });
