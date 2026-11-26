// Usage: node myshot.js <model.glb> <out.png> <look> <views-json> [tile]
// views-json: [[label, tx,ty,tz, yaw, el, dist], ...]  -> one contact sheet
const http = require('http'), fs = require('fs'), path = require('path');
// ROOT: the only machine-specific path here (the folder that holds na2/ and v3/node_modules/three). Override with NA2_ROOT.
const ROOT = process.env.NA2_ROOT || require('path').resolve(__dirname, '../../../_root');
const { chromium } = require('playwright');
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.glb': 'model/gltf-binary', '.png': 'image/png', '.jpg': 'image/jpeg', '.json': 'application/json', '.wasm': 'application/wasm' };
const rel = p => '/' + path.relative(ROOT, path.resolve(p));
(async () => {
  const model = path.resolve(process.argv[2]), out = path.resolve(process.argv[3]), look = process.argv[4] || 'studio';
  const views = JSON.parse(process.argv[5]); const T = +(process.argv[6] || 520);
  const srv = http.createServer((req, res) => {
    const p = path.normalize(path.join(ROOT, decodeURIComponent(req.url.split('?')[0])));
    if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end('nf'); }
    res.writeHead(200, { 'content-type': MIME[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(res);
  });
  await new Promise(r => srv.listen(0, '127.0.0.1', r));
  const base = 'http://127.0.0.1:' + srv.address().port;
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: T, height: T }, deviceScaleFactor: 1 });
  const errs = []; p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); }); p.on('pageerror', e => errs.push(e.message));
  await p.goto(base + rel(path.join(__dirname, 'myview.html')) + '?model=' + encodeURIComponent(rel(model)));
  await p.waitForFunction(() => window.__ready, { timeout: 240000 });
  const e2 = await p.evaluate(() => window.__errors); if (errs.length || e2.length) console.log('errors', errs, e2);
  const imgs = [];
  for (const v of views) { await p.evaluate(([v, l]) => window.__shoot(v, l), [v.slice(1), look]); imgs.push({ v: v[0], data: (await p.screenshot({ type: 'png' })).toString('base64') }); }
  const cols = Math.min(views.length, views.length > 4 ? (views.length > 6 ? 4 : 3) : views.length), sp = await b.newPage({ viewport: { width: cols * T, height: Math.ceil(views.length / cols) * T } });
  await sp.setContent('<body style="margin:0;background:#000;display:grid;grid-template-columns:repeat(' + cols + ',' + T + 'px);font:600 16px sans-serif">' +
    imgs.map(i => '<div style="position:relative"><img style="display:block" src="data:image/png;base64,' + i.data + '"><span style="position:absolute;left:8px;top:6px;color:#fff;background:#000a;padding:2px 6px">' + look + ' / ' + i.v + '</span></div>').join('') + '</body>');
  await sp.screenshot({ path: out }); await sp.close();
  await b.close(); srv.close();
})().catch(e => { console.error(e); process.exit(1); });
