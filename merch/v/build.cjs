/* Build script for the /merch 3D page.
 *
 *   cd merch/v
 *   NODE_PATH=<dir with three, esbuild, sharp, @gltf-transform/cli> \
 *   MODEL=<figure .glb> FRONT=<front.png> BACK=<back.png> ARTMETA=<meta.json> \
 *   PHOTOS=<dir with worn-back.jpg, worn-front.jpg, print-closeup.jpg> \
 *   node build.cjs
 *
 * Vercel runs no build step, so every output of this script is committed:
 *   figure.glb                 the figure wearing the tee (meshopt, WebP textures)
 *   front.webp, front-hi.webp  chest print, 1024 px wide and (if the source is larger) full size
 *   back.webp                  back print, 1536 px wide, lossless line art
 *   art.json                   pixel sizes of both prints and the caption box of the back print
 *   ph/<name>-1600.jpg, -800.jpg   the three real photos, cropped to the garment
 *   og.jpg                     1200 × 630 share image
 *   g/01.jpg … g/09.jpg        1024 px copies of the nine grid photos
 *   app.js                     the bundle
 *
 * Every variable except NODE_PATH is optional. Without one, the committed
 * output it would have produced is kept, so a clean checkout plus NODE_PATH
 * rebuilds the code and re-checks every budget.
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
  tris: 130000,                  // model contract
  glb: 1.4 * 1024 * 1024,        // after meshopt and texture compression
  jsGzip: 260 * 1024,
  firstView: 2.3 * 1024 * 1024,  // HTML + JS (as transferred, gzip) + GLB + front.webp + back.webp
  textures: [1024, 768, 512]     // longest side of the textures embedded in the model: the first that fits the GLB budget
};

/* How meshes are told apart: the same table as the runtime (src/scene.js). */
const CLASSES = [
  ['printFront', /print.?front/i], ['printBack', /print.?back/i], ['hair', /hair/i], ['pants', /pants|trouser/i],
  ['shoes', /shoe|sneaker|boot/i], ['body', /body|skin|mannequin|figure/i], ['tee', /tee|fabric|shirt|collar|rib|sleeve/i]
];

/* The real photos: source file, crop as fractions of the source (left, top,
   width) and the crop's aspect, so a sharper source of the same framing can
   be dropped in. The crops keep the garment and as little of the room as
   possible, and nothing of the wearer's face. */
const PHOTOS = {
  back: { file: 'worn-back.jpg', left: 0.215, top: 0.232, width: 0.570, aspect: 4 / 5 },
  front: { file: 'worn-front.jpg', left: 0.160, top: 0.075, width: 0.705, aspect: 4 / 5 },
  print: { file: 'print-closeup.jpg', left: 0.040, top: 0.190, width: 0.920, aspect: 4 / 3 }
};
const CAPTION_DEFAULT = { u0: 0.17, u1: 0.82, v0: 0.895, v1: 0.945 };

function fail(msg) { console.error('build failed: ' + msg); process.exit(1); }
function kb(n) { return (n / 1024).toFixed(1) + ' KB'; }
function gt() { execFileSync(GLTF, Array.prototype.slice.call(arguments), { stdio: ['ignore', 'ignore', 'inherit'] }); }
const out = name => path.join(HERE, name);
const size = name => fs.statSync(out(name)).size;

/* Reads the JSON chunk of a .glb: enough to count triangles and classify
   meshes, also on a meshopt-compressed file (accessor counts stay in the JSON). */
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
/* Counts meshes per class: first by the node (or mesh) name, then by
   name + material + parent name. */
function classify(json) {
  const count = { printFront: 0, printBack: 0, hair: 0, pants: 0, shoes: 0, body: 0, tee: 0, other: 0 };
  const parent = {};
  (json.nodes || []).forEach((n, i) => (n.children || []).forEach(c => { parent[c] = i; }));
  (json.nodes || []).forEach((n, i) => {
    if (n.mesh === undefined) return;
    const mesh = json.meshes[n.mesh], many = mesh.primitives.length > 1;
    mesh.primitives.forEach((p, k) => {
      /* the loader names a one-primitive mesh after its node; the parts of a
         multi-primitive mesh become "<mesh>_<k>" under a group named after the node */
      const name = many ? (mesh.name || '') + '_' + k : n.name || mesh.name || '';
      const up = many ? n.name || '' : parent[i] !== undefined ? json.nodes[parent[i]].name || '' : '';
      const mat = p.material !== undefined ? json.materials[p.material].name || '' : '';
      const id = name + ' ' + mat + ' ' + up;
      const hit = CLASSES.find(c => c[1].test(name)) || CLASSES.find(c => c[1].test(id));
      count[hit ? hit[0] : 'other']++;
    });
  });
  return count;
}

/* 1. Model: dedup (keeping materials apart), weld, simplify only when too
      heavy, shrink and re-encode embedded textures, meshopt. No join: every
      named mesh stays its own node, the runtime recognises them by name. */
function buildModel(src) {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'figure-'));
  const a = path.join(tmp, 'a.glb'), b = path.join(tmp, 'b.glb'), c = path.join(tmp, 'c.glb'), dst = out('figure.glb');
  gt('dedup', src, a, '--materials', 'false'); // the default would merge the two print materials
  gt('weld', a, b);
  if (triangles(glbJson(b)) > LIMIT.tris) gt('simplify', b, b, '--ratio', String(Math.min(0.9, LIMIT.tris / triangles(glbJson(b)))), '--error', '0.0005');
  if (!(glbJson(b).images || []).length) gt('meshopt', b, dst, '--level', 'medium');
  else for (const px of LIMIT.textures) {
    gt('resize', b, c, '--width', String(px), '--height', String(px));
    gt('webp', c, c, '--quality', '82');
    gt('meshopt', c, dst, '--level', 'medium');
    if (fs.statSync(dst).size <= LIMIT.glb) { console.log('model textures: at most ' + px + ' px'); break; }
  }
  fs.rmSync(tmp, { recursive: true, force: true });
}
function checkModel() {
  if (!fs.existsSync(out('figure.glb'))) fail('figure.glb missing: pass MODEL=<path to the source .glb>');
  const json = glbJson(out('figure.glb'));
  const tris = triangles(json), n = classify(json);
  if (n.printFront !== 1) fail('model needs exactly one mesh named PrintFront, found ' + n.printFront);
  if (n.printBack !== 1) fail('model needs exactly one mesh named PrintBack, found ' + n.printBack);
  if (!n.tee) fail('model has no tee mesh (name it Tee, Fabric, Shirt, Collar, Rib or Sleeve)');
  if (tris > LIMIT.tris) fail('model has ' + tris + ' triangles (limit ' + LIMIT.tris + ')');
  if (size('figure.glb') > LIMIT.glb) fail('figure.glb is ' + kb(size('figure.glb')) + ' (limit ' + kb(LIMIT.glb) + ')');
  return { size: size('figure.glb'), tris, classes: n };
}

/* 2. Prints. Front: 1024 px for first view, and the full-size source for a
      later swap when it is larger. Back: white lines on transparent, lossless. */
async function buildFront(sharp, src) {
  const meta = await sharp(src).metadata();
  await sharp(src).resize({ width: 1024, withoutEnlargement: true }).webp({ quality: 80, alphaQuality: 90 }).toFile(out('front.webp'));
  if (meta.width > 1024) await sharp(src).resize({ width: 2048, withoutEnlargement: true }).webp({ quality: 82, alphaQuality: 90 }).toFile(out('front-hi.webp'));
  else fs.rmSync(out('front-hi.webp'), { force: true });
}
async function buildBack(sharp, src) {
  await sharp(src).resize({ width: 1536, withoutEnlargement: true }).webp({ nearLossless: true, quality: 60 }).toFile(out('back.webp'));
}
/* art.json: what the bundle needs to know about the prints. Rewritten from
   the outputs each time; the caption box comes from ARTMETA when given and
   is otherwise kept. */
async function artInfo(sharp) {
  for (const f of ['front.webp', 'back.webp']) if (!fs.existsSync(out(f))) fail(f + ' missing: pass FRONT=<front.png> BACK=<back.png>');
  let kept = {};
  try { kept = JSON.parse(fs.readFileSync(out('art.json'), 'utf8')); } catch (e) { /* first build */ }
  let caption = (kept.back && kept.back.captionBox) || CAPTION_DEFAULT;
  if (process.env.ARTMETA) {
    try {
      const m = JSON.parse(fs.readFileSync(path.resolve(process.env.ARTMETA), 'utf8'));
      caption = (m.back && m.back.captionBox) || CAPTION_DEFAULT;
    } catch (e) { caption = CAPTION_DEFAULT; }     // a missing or broken meta.json: the documented default
  }
  for (const k of ['u0', 'u1', 'v0', 'v1']) if (!(caption[k] >= 0 && caption[k] <= 1)) fail('captionBox.' + k + ' must be a number in 0…1');
  const f = await sharp(out('front.webp')).metadata(), b = await sharp(out('back.webp')).metadata();
  const hi = fs.existsSync(out('front-hi.webp')) ? await sharp(out('front-hi.webp')).metadata() : null;
  const art = {
    front: { w: f.width, h: f.height, hiW: hi ? hi.width : 0 },
    back: { w: b.width, h: b.height, captionBox: { u0: caption.u0, u1: caption.u1, v0: caption.v0, v1: caption.v1 } }
  };
  fs.writeFileSync(out('art.json'), JSON.stringify(art) + '\n');
  return art;
}

/* 3. Photos. The three real photos (1600 and 800 px on the long side) and
      the share image; then the 1024 px grid copies of /merch/p/01…09. */
async function buildPhotos(sharp, dir) {
  fs.mkdirSync(out('ph'), { recursive: true });
  const crop = async k => {
    const P = PHOTOS[k], src = path.join(dir, P.file);
    if (!fs.existsSync(src)) fail('photo missing: ' + src);
    const m = await sharp(src).rotate().metadata();
    const width = Math.round(P.width * m.width), height = Math.round(width / P.aspect);
    const box = { left: Math.round(P.left * m.width), top: Math.round(P.top * m.height), width, height };
    if (box.left + box.width > m.width || box.top + box.height > m.height) fail('crop of ' + P.file + ' leaves the picture');
    return sharp(await sharp(src).rotate().extract(box).toBuffer());
  };
  for (const k of Object.keys(PHOTOS)) for (const long of [1600, 800]) {
    const P = PHOTOS[k], w = P.aspect >= 1 ? long : Math.round(long * P.aspect), h = P.aspect >= 1 ? Math.round(long / P.aspect) : long;
    await (await crop(k)).resize(w, h).jpeg({ quality: 82, progressive: true, mozjpeg: true }).toFile(out('ph/' + k + '-' + long + '.jpg'));
  }
  /* share image: the back photo, full height, centred on black */
  const tile = await (await crop('back')).resize({ height: 630 }).toBuffer();
  await sharp({ create: { width: 1200, height: 630, channels: 3, background: '#000' } })
    .composite([{ input: tile, gravity: 'centre' }]).jpeg({ quality: 84, progressive: true, mozjpeg: true }).toFile(out('og.jpg'));
}
async function buildGrid(sharp) {
  fs.mkdirSync(out('g'), { recursive: true });
  const avg = [];
  for (let k = 1; k <= 9; k++) {
    const name = '0' + k + '.jpg', src = path.join(HERE, '..', 'p', name), dst = out('g/' + name);
    if (fs.existsSync(src)) await sharp(src).resize(1024, 1024).jpeg({ quality: 78, progressive: true, mozjpeg: true }).toFile(dst);
    else if (!fs.existsSync(dst)) fail('grid photo missing: ' + src);
    /* average colour: the rack shows it, darkened, until a photo is decoded */
    const px = await sharp(dst).resize(1, 1).removeAlpha().raw().toBuffer();
    avg.push((px[0] << 16) | (px[1] << 8) | px[2]);
  }
  return avg;
}

/* 4. Code: one ES module. The byte counts drive the loader line. */
async function buildCode(esbuild, bytes, art, avg) {
  const outfile = out('app.js');
  const run = js => esbuild.build({
    entryPoints: [path.join(HERE, 'src', 'main.js')],
    bundle: true, minify: true, format: 'esm', target: 'es2020', outfile,
    nodePaths: [NODE_DIR], legalComments: 'none', logLevel: 'warning',
    define: { __BYTES__: JSON.stringify(Object.assign({ js }, bytes)), __ART__: JSON.stringify(art), __AVG__: JSON.stringify(avg) }
  });
  await run(0);
  await run(zlib.gzipSync(fs.readFileSync(outfile), { level: 9 }).length); // second pass knows its own size
  return outfile;
}

(async () => {
  const sharp = require('sharp');
  const esbuild = require('esbuild');
  const env = k => process.env[k] ? path.resolve(process.env[k]) : null;

  /* outputs of the previous product */
  for (const f of ['tee.glb', 'print.webp', 'print-2048.webp']) fs.rmSync(out(f), { force: true });

  if (env('MODEL')) buildModel(env('MODEL'));
  else console.log('MODEL not set: keeping the committed figure.glb');
  const model = checkModel();

  if (env('FRONT')) await buildFront(sharp, env('FRONT'));
  else console.log('FRONT not set: keeping the committed front.webp');
  if (env('BACK')) await buildBack(sharp, env('BACK'));
  else console.log('BACK not set: keeping the committed back.webp');
  const art = await artInfo(sharp);

  if (env('PHOTOS')) await buildPhotos(sharp, env('PHOTOS'));
  else console.log('PHOTOS not set: keeping the committed ph/*.jpg and og.jpg');
  for (const k of Object.keys(PHOTOS)) for (const long of [1600, 800]) {
    if (!fs.existsSync(out('ph/' + k + '-' + long + '.jpg'))) fail('ph/' + k + '-' + long + '.jpg missing: pass PHOTOS=<dir with the three source photos>');
  }
  if (!fs.existsSync(out('og.jpg'))) fail('og.jpg missing: pass PHOTOS=<dir with the three source photos>');

  const avg = await buildGrid(sharp);
  const bytes = { glb: model.size, front: size('front.webp'), back: size('back.webp'), frontHi: art.front.hiW ? size('front-hi.webp') : 0 };
  const app = await buildCode(esbuild, bytes, art, avg);

  /* 5. Budgets */
  const js = fs.readFileSync(app);
  const jsGzip = zlib.gzipSync(js, { level: 9 }).length;
  const html = fs.readFileSync(path.join(HERE, '..', 'index.html'));
  const htmlGzip = zlib.gzipSync(html, { level: 9 }).length;
  const firstView = htmlGzip + jsGzip + bytes.glb + bytes.front + bytes.back;
  const n = model.classes;
  console.log([
    'figure.glb       ' + kb(model.size) + '  (' + model.tris + ' triangles; tee ' + n.tee + ', body ' + n.body + ', hair ' + n.hair + ', pants ' + n.pants + ', shoes ' + n.shoes + ', other ' + n.other + ', prints ' + (n.printFront + n.printBack) + ')',
    'front.webp       ' + kb(bytes.front) + '  (' + art.front.w + ' × ' + art.front.h + ')' + (art.front.hiW ? '   front-hi.webp ' + kb(bytes.frontHi) + ' (' + art.front.hiW + ' px wide)' : ''),
    'back.webp        ' + kb(bytes.back) + '  (' + art.back.w + ' × ' + art.back.h + ', caption box ' + JSON.stringify(art.back.captionBox) + ')',
    'photos           ' + Object.keys(PHOTOS).map(k => k + ' ' + kb(size('ph/' + k + '-800.jpg')) + ' / ' + kb(size('ph/' + k + '-1600.jpg'))).join(', ') + ', og.jpg ' + kb(size('og.jpg')),
    'app.js           ' + kb(js.length) + '  (gzip ' + kb(jsGzip) + ')',
    'index.html       ' + kb(html.length) + '  (gzip ' + kb(htmlGzip) + ')',
    'first view       ' + kb(firstView) + '  (HTML and JS as gzip, GLB and prints as stored; limit ' + kb(LIMIT.firstView) + ')'
  ].join('\n'));
  if (jsGzip > LIMIT.jsGzip) fail('app.js gzip is ' + kb(jsGzip) + ' (limit ' + kb(LIMIT.jsGzip) + ')');
  if (firstView > LIMIT.firstView) fail('first view is ' + kb(firstView) + ' (limit ' + kb(LIMIT.firstView) + ')');
  console.log('ok');
})().catch(e => fail(e && e.stack || String(e)));
