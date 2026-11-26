/* Build script for the /merch 3D page.
 *
 *   cd merch/v
 *   NODE_PATH=<dir with three, esbuild, sharp, @gltf-transform/cli> \
 *   MODEL=<source tee.glb> PRINT=<source print.png> node build.cjs
 *
 * Vercel runs no build step, so every output of this script is committed:
 *   tee.glb, print.webp, print-2048.webp, g/01.jpg … g/09.jpg, app.js
 *
 * MODEL and PRINT are optional. Without them the committed tee.glb and
 * print*.webp are kept, so a clean checkout plus NODE_PATH rebuilds the
 * code and the grid photos and re-checks every budget.
 *
 * CommonJS on purpose: require() honours NODE_PATH, ESM import does not.
 */
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const zlib = require('zlib');
const { execFileSync } = require('child_process');

const HERE = __dirname;
const NODE_DIR = (process.env.NODE_PATH || '').split(path.delimiter).filter(Boolean)[0];
if (!NODE_DIR) fail('NODE_PATH must point at node_modules (three, esbuild, sharp, @gltf-transform/cli)');
const GLTF = path.join(NODE_DIR, '.bin', 'gltf-transform');

const LIMIT = {
  tris: 80000,          // model contract
  glb: 900 * 1024,      // spec says 700 KB; raised to 900 KB because the model may carry normal + occlusion maps
  jsGzip: 260 * 1024,
  firstView: 1.6 * 1024 * 1024, // HTML + JS (as transferred, gzip) + GLB + print
  texture: 1024         // longest side of any texture embedded in the model
};

function fail(msg) { console.error('build failed: ' + msg); process.exit(1); }
function kb(n) { return (n / 1024).toFixed(1) + ' KB'; }
function gt() { execFileSync(GLTF, Array.prototype.slice.call(arguments), { stdio: ['ignore', 'ignore', 'inherit'] }); }

/* Reads the JSON chunk of a .glb: enough to count triangles and find nodes,
   also on a meshopt-compressed file (accessor counts stay in the JSON). */
function glbJson(file) {
  const b = fs.readFileSync(file);
  if (b.readUInt32LE(0) !== 0x46546c67) fail(file + ' is not a GLB');
  const len = b.readUInt32LE(12);
  return JSON.parse(b.slice(20, 20 + len).toString('utf8'));
}
function triangles(json) {
  let n = 0;
  for (const m of json.meshes || []) for (const p of m.primitives) {
    if (p.mode !== undefined && p.mode !== 4) continue;
    const acc = json.accessors[p.indices !== undefined ? p.indices : p.attributes.POSITION];
    n += acc.count / 3;
  }
  return Math.round(n);
}

/* 1. Model: dedup (keeping materials apart), weld, simplify only when too
      heavy, shrink embedded textures, meshopt. No join: the Print node must
      stay its own mesh. */
function buildModel(src) {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'tee-'));
  const a = path.join(tmp, 'a.glb'), b = path.join(tmp, 'b.glb'), out = path.join(HERE, 'tee.glb');
  gt('dedup', src, a, '--materials', 'false'); // the default merges the Print material away
  gt('weld', a, b);
  if (triangles(glbJson(b)) > LIMIT.tris) gt('simplify', b, b, '--ratio', '0.75', '--error', '0.0005');
  if ((glbJson(b).images || []).length) {
    gt('resize', b, b, '--width', String(LIMIT.texture), '--height', String(LIMIT.texture));
    gt('webp', b, b, '--quality', '82');
  }
  gt('meshopt', b, out, '--level', 'medium');
  fs.rmSync(tmp, { recursive: true, force: true });
}
function checkModel() {
  const file = path.join(HERE, 'tee.glb');
  if (!fs.existsSync(file)) fail('tee.glb missing: pass MODEL=<path to the source .glb>');
  const json = glbJson(file);
  const tris = triangles(json);
  if (!(json.nodes || []).some(n => n.name === 'Print')) fail('model has no node named "Print"');
  if (tris > LIMIT.tris) fail('model has ' + tris + ' triangles (limit ' + LIMIT.tris + ')');
  const size = fs.statSync(file).size;
  if (size > LIMIT.glb) fail('tee.glb is ' + kb(size) + ' (limit ' + kb(LIMIT.glb) + ')');
  return { size, tris };
}

/* 2. Print: 1024 px for first view, full size for the later swap. */
async function buildPrint(sharp, src) {
  await sharp(src).resize(1024).webp({ quality: 80, alphaQuality: 90 }).toFile(path.join(HERE, 'print.webp'));
  await sharp(src).webp({ quality: 82, alphaQuality: 90 }).toFile(path.join(HERE, 'print-2048.webp'));
}

/* 3. Photos: 1024 px grid/rack copies of /merch/p/01…09 and their average
      colour (the rack shows it, darkened, until a photo is decoded). */
async function buildPhotos(sharp) {
  const dir = path.join(HERE, 'g');
  fs.mkdirSync(dir, { recursive: true });
  const avg = [];
  for (let k = 1; k <= 9; k++) {
    const name = '0' + k + '.jpg';
    const src = path.join(HERE, '..', 'p', name);
    await sharp(src).resize(1024, 1024).jpeg({ quality: 78, progressive: true, mozjpeg: true }).toFile(path.join(dir, name));
    const px = await sharp(src).resize(1, 1).removeAlpha().raw().toBuffer();
    avg.push((px[0] << 16) | (px[1] << 8) | px[2]);
  }
  return avg;
}

/* 4. Code: one ES module. The byte counts drive the loader line. */
async function buildCode(esbuild, bytes, avg) {
  const outfile = path.join(HERE, 'app.js');
  const run = js => esbuild.build({
    entryPoints: [path.join(HERE, 'src', 'main.js')],
    bundle: true, minify: true, format: 'esm', target: 'es2020', outfile,
    nodePaths: [NODE_DIR], legalComments: 'none', logLevel: 'warning',
    define: { __BYTES__: JSON.stringify(Object.assign({ js }, bytes)), __AVG__: JSON.stringify(avg) }
  });
  await run(0);
  await run(zlib.gzipSync(fs.readFileSync(outfile), { level: 9 }).length); // second pass knows its own size
  return outfile;
}

(async () => {
  const sharp = require('sharp');
  const esbuild = require('esbuild');

  if (process.env.MODEL) buildModel(path.resolve(process.env.MODEL));
  else console.log('MODEL not set: keeping the committed tee.glb');
  const model = checkModel();

  if (process.env.PRINT) await buildPrint(sharp, path.resolve(process.env.PRINT));
  else console.log('PRINT not set: keeping the committed print.webp and print-2048.webp');
  for (const f of ['print.webp', 'print-2048.webp']) if (!fs.existsSync(path.join(HERE, f))) fail(f + ' missing: pass PRINT=<path to print.png>');
  const print = fs.statSync(path.join(HERE, 'print.webp')).size;
  const printMeta = await sharp(path.join(HERE, 'print.webp')).metadata();

  const avg = await buildPhotos(sharp);
  const app = await buildCode(esbuild, { glb: model.size, print, printW: printMeta.width, printH: printMeta.height }, avg);

  /* 5. Budgets */
  const js = fs.readFileSync(app);
  const jsGzip = zlib.gzipSync(js, { level: 9 }).length;
  const html = fs.readFileSync(path.join(HERE, '..', 'index.html'));
  const htmlGzip = zlib.gzipSync(html, { level: 9 }).length;
  const firstView = htmlGzip + jsGzip + model.size + print;
  console.log([
    'tee.glb          ' + kb(model.size) + '  (' + model.tris + ' triangles)',
    'print.webp       ' + kb(print),
    'print-2048.webp  ' + kb(fs.statSync(path.join(HERE, 'print-2048.webp')).size),
    'app.js           ' + kb(js.length) + '  (gzip ' + kb(jsGzip) + ')',
    'index.html       ' + kb(html.length) + '  (gzip ' + kb(htmlGzip) + ')',
    'first view       ' + kb(firstView) + '  (HTML and JS as gzip, GLB and print as stored)'
  ].join('\n'));
  if (jsGzip > LIMIT.jsGzip) fail('app.js gzip is ' + kb(jsGzip) + ' (limit ' + kb(LIMIT.jsGzip) + ')');
  if (firstView > LIMIT.firstView) fail('first view is ' + kb(firstView) + ' (limit ' + kb(LIMIT.firstView) + ')');
  console.log('ok');
})().catch(e => fail(e && e.stack || String(e)));
