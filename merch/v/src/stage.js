/* Stage: renderer, canvas size, device pixel ratio, frame rects, the pose
   solver, the projection of the giant HTML "NA2" as a sign behind the figure,
   and where the hem of the tee is on screen (for the colour swatches). */
import { WebGLRenderer, PerspectiveCamera, Vector3, ACESFilmicToneMapping, SRGBColorSpace } from 'three';
import { CFG, rad } from './config.js';

export const stage = {
  el: null,          // .stage, 100vw × 100svh, fixed
  canvas: null,      // 100vw × 100lvh, so a mobile toolbar never resizes the buffer
  n: null,           // the giant "NA2" span of the <h1>
  renderer: null,
  camera: null,
  W: 1, H: 1,        // canvas size in CSS px
  S: 1,              // one screen (100svh) in px
  f: 1,              // focal length in CSS px
  fov: 40, portrait: true, coarse: false, dpr: 1,
  fadeUntil: 0,      // performance.now() until which a canvas fade is running
  rect: {},          // frame rects by name: hero, print, side, item; sw is the row of colour swatches
  nRest: null        // rest rect of the sign (no transform)
};

const FRAMES = { hero: '.fr-hero', print: '.fr-print', side: '.fr-side', item: '.fr-item', sw: '.sw' };

/* Creates the WebGL2 context and the renderer. Returns false when the
   browser cannot give us a context (the caller falls back to the static page). */
export function initStage() {
  stage.el = document.querySelector('.stage');
  stage.canvas = document.getElementById('gl');
  stage.n = document.querySelector('#t .n');
  stage.coarse = matchMedia('(pointer:coarse)').matches;

  const mem = navigator.deviceMemory;
  const attrs = { antialias: !(mem && mem <= 2), alpha: true, stencil: false, depth: true, powerPreference: 'high-performance', premultipliedAlpha: true };
  const context = stage.canvas.getContext('webgl2', attrs);
  if (!context) return false;

  const r = new WebGLRenderer(Object.assign({ canvas: stage.canvas, context }, attrs));
  r.setClearColor(0x000000, 0);
  r.toneMapping = ACESFilmicToneMapping;
  r.outputColorSpace = SRGBColorSpace;
  stage.renderer = r;
  stage.camera = new PerspectiveCamera(CFG.FOV_PORTRAIT, 1, CFG.NEAR, CFG.FAR);
  return true;
}

function box(el) {
  const r = el.getBoundingClientRect();
  return { x: r.left, y: r.top, w: r.width, h: r.height, cx: r.left + r.width / 2, cy: r.top + r.height / 2 };
}

/* Reads everything that depends on the viewport. Call on load and on resize. */
export function measure(tier) {
  const c = stage.canvas;
  stage.W = Math.max(1, c.clientWidth);
  stage.H = Math.max(1, c.clientHeight);
  stage.S = Math.max(1, stage.el.clientHeight);
  stage.portrait = stage.W / stage.S < 1;
  stage.fov = stage.portrait ? CFG.FOV_PORTRAIT : CFG.FOV_LANDSCAPE;
  stage.f = stage.H / (2 * Math.tan(rad(stage.fov) / 2));

  for (const k in FRAMES) stage.rect[k] = box(stage.el.querySelector(FRAMES[k]));

  /* the sign's rest rect, read without the transform the script writes */
  const keep = stage.n.style.transform;
  stage.n.style.transform = 'none';
  stage.nRest = box(stage.n);
  stage.n.style.transform = keep;
  lastSign = '';

  stage.dpr = Math.min(window.devicePixelRatio || 1, stage.coarse ? 1.5 : 2, CFG.DPR[tier]);
  stage.renderer.setPixelRatio(stage.dpr);
  stage.renderer.setSize(stage.W, stage.H, false);
  stage.camera.fov = stage.fov;
  stage.camera.aspect = stage.W / stage.H;
  stage.camera.updateProjectionMatrix();
}

/* ---- poses ------------------------------------------------------------ */

/* Distance at which a w × h subject fills a frame rect (contain). */
export function fitDistance(w, h, r) {
  return Math.max(w * stage.f / r.w, h * stage.f / r.h);
}

/* A pose is: look-at target, ln(distance), azimuth, elevation, roll and the
   screen point (frame centre) the target is put on. */
export function makePose(target, d, angles, r) {
  return { t: target.clone(), ln: Math.log(d), az: rad(angles.az), el: rad(angles.el), roll: rad(angles.roll), cx: r.cx, cy: r.cy };
}

export function mixPose(a, b, k, out) {
  out.t.lerpVectors(a.t, b.t, k);
  out.ln = a.ln + (b.ln - a.ln) * k;
  out.az = a.az + (b.az - a.az) * k;
  out.el = a.el + (b.el - a.el) * k;
  out.roll = a.roll + (b.roll - a.roll) * k;
  out.cx = a.cx + (b.cx - a.cx) * k;
  out.cy = a.cy + (b.cy - a.cy) * k;
  return out;
}

export function copyPose(a, out) { return mixPose(a, a, 0, out); }
export function blankPose() { return { t: new Vector3(), ln: 0, az: 0, el: 0, roll: 0, cx: 0, cy: 0 }; }

/* Moves the camera to a pose. setViewOffset shifts the picture so that the
   target lands on the frame centre instead of the canvas centre. */
export function applyPose(p) {
  const cam = stage.camera, d = Math.exp(p.ln), ce = Math.cos(p.el);
  cam.position.set(p.t.x + d * Math.sin(p.az) * ce, p.t.y + d * Math.sin(p.el), p.t.z + d * Math.cos(p.az) * ce);
  cam.up.set(Math.sin(p.roll) * Math.cos(p.az), Math.cos(p.roll), -Math.sin(p.roll) * Math.sin(p.az));
  cam.lookAt(p.t);
  cam.setViewOffset(stage.W, stage.H, stage.W / 2 - p.cx, stage.H / 2 - p.cy, stage.W, stage.H);
  cam.updateMatrixWorld();
}

/* ---- the giant NA2 as a sign behind the figure ------------------------- */

const signA = new Vector3(), signB = new Vector3(), _v = new Vector3(), _d = new Vector3();
let lastSign = '';

function toPlane(px, py, z, out) {
  const cam = stage.camera;
  _v.set(px / stage.W * 2 - 1, 1 - py / stage.H * 2, 0.5).unproject(cam);
  _d.copy(_v).sub(cam.position);
  out.copy(cam.position).addScaledVector(_d, (z - cam.position.z) / _d.z);
}

/* Pins the sign's rest rect to the plane z = planeZ as seen from the hero pose. */
export function setSign(heroPose, planeZ) {
  applyPose(heroPose);
  const r = stage.nRest;
  toPlane(r.x, r.y, planeZ, signA);
  toPlane(r.x + r.w, r.y + r.h, planeZ, signB);
}

/* Projects the pinned rect through the live camera and writes the one
   transform and one opacity that script is allowed to touch per frame. */
export function projectSign(opacity) {
  const cam = stage.camera, r = stage.nRest;
  _v.copy(signA).project(cam);
  const ax = (_v.x + 1) / 2 * stage.W, ay = (1 - _v.y) / 2 * stage.H;
  _v.copy(signB).project(cam);
  const bx = (_v.x + 1) / 2 * stage.W;
  const sc = (bx - ax) / r.w;
  const css = 'translate(' + (ax - r.x).toFixed(2) + 'px,' + (ay - r.y).toFixed(2) + 'px) scale(' + sc.toFixed(4) + ')|' + opacity.toFixed(3);
  if (css === lastSign) return;
  lastSign = css;
  const cut = css.indexOf('|');
  stage.n.style.transform = css.slice(0, cut);
  stage.n.style.opacity = css.slice(cut + 1);
}

/* ---- the hem on screen ------------------------------------------------- */

/* The lowest of the given points (the bottom corners of the tee, relative to
   the figure's yaw group) as the camera sees them now: y in CSS px from the
   top of the stage. Infinity when one of them is beside or behind the camera. */
export function lowestOnScreen(points, matrix) {
  const cam = stage.camera;
  let y = -Infinity;
  for (const p of points) {
    _v.copy(p).applyMatrix4(matrix);
    if (_d.copy(_v).applyMatrix4(cam.matrixWorldInverse).z > -cam.near) return Infinity;
    _v.project(cam);
    y = Math.max(y, (1 - _v.y) / 2 * stage.H);
  }
  return y;
}

/* ---- canvas opacity (arrival flicker, jump dip, fades) ---------------- */

export function setCanvasOpacity(v, ms) {
  const s = stage.canvas.style;
  s.transition = ms ? 'opacity ' + ms + 'ms linear' : 'none';
  s.opacity = String(v);
  /* the render loop stays awake until the fade is over (a fade counts as a tween) */
  stage.fadeUntil = ms ? performance.now() + ms + 60 : 0;
}
