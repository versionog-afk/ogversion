/* Loading: byte-progress fetches, abort, GLB parse, print bitmap.
   (The lazy queue for the rack photos is added with the rack.) */
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { BYTES, URLS } from './config.js';

/* Fetches a file through a stream reader so the loader line can show real bytes. */
async function fetchBytes(url, expected, onBytes, signal) {
  const res = await fetch(url, { signal });
  if (!res.ok) throw new Error(url + ' ' + res.status);
  if (!res.body || !res.body.getReader) {           // very old engines: no streaming, count at the end
    const all = await res.arrayBuffer();
    onBytes(all.byteLength);
    return all;
  }
  const reader = res.body.getReader();
  const chunks = [];
  let got = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
    got += value.byteLength;
    onBytes(value.byteLength);
  }
  const out = new Uint8Array(got);
  let at = 0;
  for (const c of chunks) { out.set(c, at); at += c.byteLength; }
  if (expected && got !== expected) onBytes(expected - got); // a stale build number must not leave the line short
  return out.buffer;
}

/* Loads the model and the print together.
   onProgress(0..1) counts app.js itself as already received. */
export async function loadAssets(onProgress, signal) {
  const total = BYTES.js + BYTES.glb + BYTES.print;
  let got = BYTES.js;
  let shown = 0;
  const add = n => {
    got += n;
    const p = Math.min(1, got / total);
    if (p > shown) { shown = p; onProgress(p); }     // monotonic by construction
  };
  add(0);

  const [glbBuf, printBuf] = await Promise.all([
    fetchBytes(URLS.glb, BYTES.glb, add, signal),
    fetchBytes(URLS.print, BYTES.print, add, signal)
  ]);

  const loader = new GLTFLoader();
  loader.setMeshoptDecoder(MeshoptDecoder);
  const [gltf, print] = await Promise.all([
    loader.parseAsync(glbBuf, ''),
    decodeImage(printBuf, 'image/webp')
  ]);
  if (signal && signal.aborted) throw new Error('aborted');
  onProgress(1);
  return { gltf, print };
}

/* Decodes to an ImageBitmap with straight alpha and no flip (the print's
   v = 0 is its top row, matching texture.flipY = false). */
export async function decodeImage(buffer, type) {
  const blob = new Blob([buffer], { type });
  if (typeof createImageBitmap === 'function') {
    try { return await createImageBitmap(blob, { premultiplyAlpha: 'none', colorSpaceConversion: 'none' }); }
    catch (e) { /* fall through to <img> */ }
  }
  const img = new Image();
  img.src = URL.createObjectURL(blob);   // kept alive: the upload may need to decode again
  await img.decode();
  return img;
}
