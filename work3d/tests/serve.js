// Tiny static server for tests: node serve.js [port]   (root = the repo)
const http = require('http'), fs = require('fs'), path = require('path'), zlib = require('zlib');
const ROOT = process.env.ROOT || path.resolve(__dirname, '../..'); // repository root
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.glb': 'model/gltf-binary', '.webp': 'image/webp', '.jpg': 'image/jpeg', '.png': 'image/png', '.json': 'application/json', '.txt': 'text/plain', '.css': 'text/css' };
const port = +process.argv[2] || 8347;
http.createServer((req, res) => {
  let u = decodeURIComponent(req.url.split('?')[0]);
  if (u === '/merch' || u === '/merch/') u = '/merch/index.html';
  const p = path.normalize(path.join(ROOT, u));
  if (!p.startsWith(ROOT + '/') || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404, { 'content-type': 'text/plain' }); return res.end('not found'); }
  const st = fs.statSync(p), ext = path.extname(p);
  // text is served gzipped, as the production host does; binaries as stored
  if ((ext === '.js' || ext === '.html') && /gzip/.test(req.headers['accept-encoding'] || '')) {
    const z = zlib.gzipSync(fs.readFileSync(p));
    res.writeHead(200, { 'content-type': MIME[ext], 'content-encoding': 'gzip', 'content-length': z.length, 'cache-control': 'no-store' });
    return res.end(z);
  }
  res.writeHead(200, { 'content-type': MIME[ext] || 'application/octet-stream', 'content-length': st.size, 'cache-control': 'no-store' });
  fs.createReadStream(p).pipe(res);
}).listen(port, '127.0.0.1', () => console.log('http://127.0.0.1:' + port + '/merch'));
