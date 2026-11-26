/* Spin: pointer arbitration between scrolling and spinning, the shirt's yaw
   physics, and the pendulum that gives it weight.

   Flick1D is the drag / inertia / snap core. The shirt's yaw uses it here;
   the rack uses a second instance with its own numbers (see rack.js). */
import { CFG, clamp } from './config.js';

/* One dragged value with inertia and detents.
   p: { k, kick, vMax, vFlick, kMin, kMax, vSpring, snap, K, zeta, vRest, xRest,
        nearest(x) → the allowed detent nearest to x, onSettle() } */
export class Flick1D {
  constructor(p) {
    this.p = p;
    this.x = 0;            // value
    this.v = 0;            // velocity, units per second
    this.mode = 'rest';    // rest | drag | coast | flick | spring
    this.D = 0;            // where a flick or the spring is heading
    this.k1 = p.k;         // friction of the current flick
    this.z = p.zeta;       // damping ratio of the current spring
  }
  get busy() { return this.mode !== 'rest'; }

  grab() { this.mode = 'drag'; this.v = 0; }

  /* Let go with a velocity. Fast: coast so that it lands on a detent.
     Slow: coast to a stop; the spring takes it only close to a detent. */
  release(v0) {
    const p = this.p;
    v0 = clamp(v0, -p.vMax, p.vMax);
    this.v = v0;
    if (Math.abs(v0) >= p.vFlick) {
      this.D = p.nearest(this.x + v0 / p.k);
      const k1 = v0 / (this.D - this.x);
      this.k1 = clamp(isFinite(k1) ? k1 : p.k * p.kMax, p.k * p.kMin, p.k * p.kMax);
      this.mode = 'flick';
    } else {
      this.mode = 'coast';
    }
  }

  /* Send the spring to a value. */
  springTo(D, zeta) {
    this.D = D;
    this.z = zeta === undefined ? this.p.zeta : zeta;
    this.mode = 'spring';
  }

  step(h) {
    const p = this.p;
    if (this.mode === 'flick') {
      this.v -= this.k1 * this.v * h;
      this.x += this.v * h;
      if (Math.abs(this.v) < p.vSpring || Math.abs(this.x - this.D) < p.snap) this.springTo(this.D);
    } else if (this.mode === 'coast') {
      const s = Math.sign(this.v);
      this.v -= (p.k * this.v + p.kick * s) * h;
      if (Math.sign(this.v) !== s) this.v = 0;
      this.x += this.v * h;
      const near = p.nearest(this.x);
      if (Math.abs(this.x - near) < p.snap && Math.abs(this.v) < p.vSpring) this.springTo(near);
      else if (this.v === 0 || Math.abs(this.v) < p.vRest) { this.v = 0; this.mode = 'rest'; p.onSettle && p.onSettle(); }
    } else if (this.mode === 'spring') {
      const w = Math.sqrt(p.K);
      this.v += (-p.K * (this.x - this.D) - 2 * this.z * w * this.v) * h;
      this.x += this.v * h;
      if (Math.abs(this.v) < p.vRest && Math.abs(this.x - this.D) < p.xRest) {
        this.x = this.D; this.v = 0; this.mode = 'rest';
        p.onSettle && p.onSettle();
      }
    }
  }
}

/* ---- the shirt -------------------------------------------------------- */

const P = CFG.SPIN, W = CFG.SWING;

export const spin = {
  core: null,
  close: false,           // camera is close: front only, ±35°
  dragBase: 0,            // unresisted yaw while dragging in close-up
  swingX: 0, swingXv: 0,  // pendulum, sideways (degrees)
  swingZ: 0, swingZv: 0,  // pendulum, forward
  vis: 0, visPrev: 0,     // smoothed angular velocity that drives the pendulum
  lastX: 0,
  calm: false,
  onSettle: null,         // (detent | null) → hud
  onInput: null,          // any hand input → loop wake, sway timer
  turnsHook: null         // reserved for the 47-turns moment
};

const mod360 = a => ((a % 360) + 360) % 360;
/* the multiple of 360 (plus offset) nearest to x */
const nearestTurn = (x, offset) => Math.round((x - offset) / 360) * 360 + offset;

function nearestDetent(x) {
  const front = nearestTurn(x, 0);
  if (spin.close) return front;
  const back = nearestTurn(x, 180);
  return Math.abs(x - front) <= Math.abs(x - back) ? front : back;
}

export function initSpin() {
  spin.core = new Flick1D({
    k: P.k, kick: P.kick, vMax: P.vMax, vFlick: P.vFlick, kMin: P.kMin, kMax: P.kMax,
    vSpring: P.vSpring, snap: P.snap, K: P.K, zeta: P.zeta, vRest: P.vRest, xRest: P.xRest,
    nearest: nearestDetent,
    onSettle: () => {
      try { navigator.vibrate && navigator.vibrate(10); } catch (e) { /* haptics are optional */ }
      spin.onSettle && spin.onSettle(detent());
    }
  });
}

export const yaw = () => spin.core.x;
/* 0 or 180 when resting on a detent, otherwise null */
export function detent() {
  const c = spin.core;
  if (c.mode !== 'rest') return null;
  const a = mod360(c.x);
  if (Math.abs(a) < 0.5 || Math.abs(a - 360) < 0.5) return 0;
  if (Math.abs(a - 180) < 0.5) return 180;
  return null;
}

export function grab() {
  const c = spin.core;
  c.grab();
  spin.dragBase = c.x;
}

/* dx in degrees of unresisted hand travel */
export function drag(deg) {
  const c = spin.core;
  spin.dragBase += deg;
  if (spin.close) {
    /* past ±35° from the front the shirt only follows a third of the way */
    const front = nearestTurn(spin.dragBase, 0), off = spin.dragBase - front, lim = P.limit;
    c.x = front + (Math.abs(off) <= lim ? off : Math.sign(off) * (lim + (Math.abs(off) - lim) * P.beyond));
  } else {
    c.x = spin.dragBase;
  }
}

export function release(v) {
  const c = spin.core;
  if (spin.close) { c.v = clamp(v, -P.vClose, P.vClose); c.springTo(nearestTurn(c.x, 0), P.zetaClose); }
  else c.release(v);
}

/* Buttons and the range input: turn to an absolute angle by the short way. */
export function turnTo(deg, zeta) {
  const c = spin.core;
  const delta = mod360(deg - c.x + 180) - 180;
  c.springTo(c.x + delta, zeta);
}

export function poke() { if (!spin.calm) spin.swingZv += W.poke; }

/* Called when the camera crosses the close-up distance. */
export function setClose(on) {
  if (on === spin.close) return;
  spin.close = on;
  const c = spin.core;
  if (on && c.mode !== 'drag') {
    const front = nearestTurn(c.x, 0);
    if (c.mode !== 'rest' || Math.abs(c.x - front) > 0.01) c.springTo(front, P.zetaClose);
  }
  if (c.mode === 'drag') spin.dragBase = c.x;
}

/* One frame: fixed 1/120 s steps for the yaw and the pendulum.
   scrollAcc is the applied scroll's acceleration in px/s². */
export function stepSpin(dt, scrollAcc) {
  const c = spin.core, h = CFG.STEP;
  const steps = Math.min(CFG.MAX_STEPS, Math.max(1, Math.round(dt / h)));

  /* angular velocity as the pendulum feels it: measured while dragging */
  if (c.mode === 'drag') {
    const now = (c.x - spin.lastX) / Math.max(dt, 1e-3);
    spin.vis += (now - spin.vis) * (1 - Math.exp(-dt / 0.05));
  }
  spin.lastX = c.x;

  for (let i = 0; i < steps; i++) c.step(h);
  if (c.mode !== 'drag') spin.vis = c.v;
  const acc = clamp((spin.vis - spin.visPrev) / Math.max(dt, 1e-3), -20000, 20000);
  spin.visPrev = spin.vis;

  if (spin.calm) { spin.swingX = spin.swingZ = spin.swingXv = spin.swingZv = 0; return; }
  const w = 2 * Math.PI * W.hz, w2 = w * w, c2 = 2 * W.zeta * w;
  const ax = W.fromYaw * acc, az = W.fromScroll * clamp(scrollAcc, -60000, 60000);
  for (let i = 0; i < steps; i++) {
    spin.swingXv += (-w2 * spin.swingX - c2 * spin.swingXv + ax) * h;
    spin.swingX += spin.swingXv * h;
    spin.swingZv += (-w2 * spin.swingZ - c2 * spin.swingZv + az) * h;
    spin.swingZ += spin.swingZv * h;
    if (Math.abs(spin.swingX) > W.max) { spin.swingX = Math.sign(spin.swingX) * W.max; if (spin.swingXv * spin.swingX > 0) spin.swingXv = 0; }
    if (Math.abs(spin.swingZ) > W.max) { spin.swingZ = Math.sign(spin.swingZ) * W.max; if (spin.swingZv * spin.swingZ > 0) spin.swingZv = 0; }
  }
}

/* true while anything here still moves */
export function spinBusy() {
  return spin.core.busy ||
    Math.abs(spin.swingX) > 0.02 || Math.abs(spin.swingXv) > 0.05 ||
    Math.abs(spin.swingZ) > 0.02 || Math.abs(spin.swingZv) > 0.05;
}

/* ---- pointer arbitration ---------------------------------------------- */

/* The page scrolls natively (touch-action: pan-y). A primary pointer that
   starts off the screen edges and off any control is watched; after 8 px it
   is either a horizontal gesture (ours) or it is dropped (the browser's).
   All listeners are passive and nothing calls preventDefault.

   handlers: { canStart(e) → bool, start(), move(dxPx, degPerPx, farthestPx), end(vPxPerSec, degPerPx), tap(e) }
   degPerPx is the spec's drag rate for the pointer type (touch or mouse). */
export function initPointer(handlers) {
  const html = document.documentElement;
  let g = null;   // the watched gesture

  const cancel = () => {
    if (!g) return;
    if (g.mode === 'h') { html.classList.remove('drag'); handlers.end(0, g.rate); }
    g = null;
  };

  addEventListener('pointerdown', e => {
    if (!e.isPrimary) { cancel(); return; }                        // a second pointer cancels
    if (g) cancel();
    if (e.pointerType === 'mouse' && e.button !== 0) return;
    const vv = window.visualViewport;
    if (vv && vv.scale > 1.01) return;                             // pinch-zoomed: leave everything to the browser
    if (e.clientX < CFG.EDGE || e.clientX > innerWidth - CFG.EDGE) return;  // system back-swipe zones
    const t = e.target;
    if (!t || !t.closest || t.closest('a,button,input,dialog,.pl,.blk')) return;   // controls, text plates, the opaque blocks
    if (!handlers.canStart(e)) return;
    const touch = e.pointerType !== 'mouse';
    g = {
      id: e.pointerId, x0: e.clientX, y0: e.clientY, t0: e.timeStamp, mode: 'wait', target: t,
      x: e.clientX, far: 0, samples: [],
      rate: touch ? clamp(P.touchPerWidth / innerWidth, P.touchMin, P.touchMax) : P.mouse
    };
  }, { passive: true });

  addEventListener('pointermove', e => {
    if (!g || e.pointerId !== g.id) return;
    const dx = e.clientX - g.x0, dy = e.clientY - g.y0;
    if (g.mode === 'wait') {
      if (Math.hypot(dx, dy) < CFG.SLOP) return;
      if (Math.abs(dx) <= CFG.HORIZ * Math.abs(dy)) { g = null; return; }   // vertical: the page scrolls
      g.mode = 'h';
      g.x = e.clientX;
      try { g.target.setPointerCapture(g.id); } catch (err) { /* capture is a nicety */ }
      html.classList.add('drag');
      handlers.start();
    }
    const step = e.clientX - g.x;
    g.x = e.clientX;
    g.far = Math.max(g.far, Math.abs(dx));
    g.samples.push(e.timeStamp, e.clientX);
    if (g.samples.length > 40) g.samples.splice(0, 2);
    handlers.move(step, g.rate, g.far);
  }, { passive: true });

  addEventListener('pointerup', e => {
    if (!g || e.pointerId !== g.id) return;
    const cur = g;
    g = null;
    if (cur.mode === 'h') {
      html.classList.remove('drag');
      /* release velocity: mean over the last 80 ms */
      const s = cur.samples, tEnd = e.timeStamp;
      let i = s.length - 2;
      while (i > 0 && tEnd - s[i - 2] <= P.sampleMs) i -= 2;
      const span = (tEnd - s[i]) / 1000;
      const v = span > 0.008 && tEnd - s[s.length - 2] < 60 ? (e.clientX - s[i + 1]) / span : 0;
      handlers.end(v, cur.rate);
    } else if (e.timeStamp - cur.t0 < CFG.TAP_MS && Math.hypot(e.clientX - cur.x0, e.clientY - cur.y0) < CFG.SLOP) {
      handlers.tap(e);
    }
  }, { passive: true });

  addEventListener('pointercancel', e => { if (g && e.pointerId === g.id) cancel(); }, { passive: true });
  addEventListener('blur', cancel);
}
