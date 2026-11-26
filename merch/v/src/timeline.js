/* Timeline: scroll anchors, the smoothed ("applied") scroll, the jump dip,
   and what the scroll position means each frame: camera pose, light state,
   the giant 47's projection and the HUD classes.

   Scroll owns camera and light; the hand owns the shirt (spin.js). */
import { BYTES, CFG, clamp, lerp, smoothstep, easeInOutCubic, follow } from './config.js';
import { stage, fitDistance, makePose, mixPose, blankPose, applyPose, setSign, projectSign, setCanvasOpacity } from './stage.js';
import { world, setLights } from './scene.js';
import { rack } from './rack.js';
import { setClose } from './spin.js';
import { quality } from './quality.js';
import { Vector3 } from 'three';

export const tl = {
  y: 0,                 // window.scrollY this frame
  s: 0,                 // applied scroll: follows y with a 0.12 s time constant
  v: 0, acc: 0,         // applied scroll velocity (px/s) and acceleration (px/s²)
  frozen: null,         // ?s= test hook: the applied scroll is pinned here
  calm: false,
  A: {},                // anchors in px of scroll
  keys: [],             // camera keyframes { at, pose }
  P: {},                // named poses
  pose: blankPose(),
  d: 1, dHero: 1, dPrint: 1,
  near: 0, nearOn: false, nearFrom: 0,     // "Iš arti"
  dark: 0, darkWant: 0, lightOverride: null, // lights: 0 on … 1 out; override true = on, false = off
  line: 0, rail: 0, railSpan: [0, 0], uScroll: -1,
  asleep: false, hudOff: false, typeOff: false,
  dipUntil: 0,
  first: true,
  onNear: null,         // (on) → hud
  onLight: null,        // (lightsOn) → hud
  onHud: null           // (off) → hud
};

const html = document.documentElement;
const _t = new Vector3();

/* ---- layout: anchors, poses, keyframes -------------------------------- */

export function layout() {
  const S = stage.S, K = CFG.KEY, y0 = window.scrollY;
  const rectOf = id => document.getElementById(id).getBoundingClientRect();
  const top = id => rectOf(id).top + y0;
  /* id@t: the scrollY at which the block's top edge has travelled t screens up from the viewport bottom */
  const at = (id, t) => top(id) - S + t * S;
  const st = rectOf('stovas');
  const tall = stage.portrait;

  const A = tl.A = {
    creepEnd: K.creepEnd * S, printAt: K.printAt * S,
    hudOff: K.hudOff * S, hudOn: K.hudOn * S, typeOff: K.typeOff * S,
    skMacroFrom: at('sk', K.skMacroFrom), skMacroAt: at('sk', K.skMacroAt),
    skDark: at('sk', K.skDark), skLine0: at('sk', K.skLine0), skLine1: at('sk', K.skLine1),
    tiekLight: at('tiek', K.tiekLight), tiekPrint: at('tiek', K.tiekPrint),
    stItem: at('stovas', K.stItem),
    stRail0: at('stovas', tall ? K.stRail0P : K.stRail0), stRail1: at('stovas', tall ? K.stRail1P : K.stRail1),
    stPhotos: at('stovas', tall ? K.stPhotosP : K.stPhotos),
    stBottom: st.top + y0 + st.height,
    keep0: at('sk', K.lightKeep0), keep1: at('tiek', K.lightKeep1)
  };

  /* A short facts plate (landscape cards) would leave no room between the
     print pose and the item pose: give that pull-back at least 0.3 S, but
     have it done before the rail starts to draw. */
  A.stItem = Math.min(Math.max(A.stItem, A.tiekPrint + K.itemTravel * S), A.stRail0 - K.minGap * S);

  /* poses, solved against the frame rects */
  const R = stage.rect, Q = CFG.POSE, P = tl.P;
  tl.dHero = fitDistance(world.size.x, world.size.y, R.hero);
  P.hero = makePose(world.C, tl.dHero, Q.HERO, R.hero);
  P.hero2 = makePose(world.C, tl.dHero * CFG.HERO_CREEP, Q.HERO, R.hero);
  tl.dPrint = fitDistance(world.printSize.x, world.printSize.y, R.print);
  P.print = makePose(world.P, tl.dPrint, Q.PRINT, R.print);
  P.print2 = makePose(world.P, tl.dPrint, Q.PRINT_END, R.print);
  const sharp = world.printSize.x / (world.printTex.image.width || BYTES.printW) * stage.f * stage.dpr / CFG.MACRO_SHARP;
  P.macro = makePose(world.A47, Math.max(fitDistance(CFG.SIZE47.w, CFG.SIZE47.h, R.n47), sharp), Q.MACRO, R.n47);

  /* the tee as an item under the rail: whole shirt plus the rail above it */
  const railTop = world.Yr + CFG.RAIL.size;
  _t.set(world.C.x, (railTop + world.bottom) / 2, world.C.z);
  P.tee = makePose(_t, fitDistance(world.size.x * 1.06, (railTop - world.bottom) * 1.04, R.item), Q.ITEM, R.item);
  /* world x of the screen's left and right edge at that pose: the rail draws across it */
  const perPx = Math.exp(P.tee.ln) / stage.f;
  tl.railSpan = [P.tee.t.x - P.tee.cx * perPx, P.tee.t.x + (stage.W - P.tee.cx) * perPx];
  /* a photo panel as an item (the camera slides along x for the others) */
  _t.set(rack.X(0), world.Yr - CFG.PANEL.drop, world.C.z);
  P.panel = makePose(_t, fitDistance(CFG.PANEL.size, CFG.PANEL.size, R.item), Q.ITEM, R.item);

  const keys = tl.keys = [
    { at: 0, pose: P.hero },
    { at: A.creepEnd, pose: P.hero2 },
    { at: A.printAt, pose: P.print },
    { at: A.skMacroFrom, pose: P.print2 },
    { at: A.skMacroAt, pose: P.macro },
    { at: A.tiekLight, pose: P.macro },
    { at: A.tiekPrint, pose: P.print2 },
    { at: A.stItem, pose: P.tee },
    { at: A.stPhotos, pose: P.tee }
  ];
  /* a keyframe is never less than 0.05 S after the previous one */
  for (let i = 1; i < keys.length; i++) keys[i].at = Math.max(keys[i].at, keys[i - 1].at + K.minGap * S);

  /* the giant 47 is pinned 2 m behind the shirt as seen from the hero pose */
  setSign(P.hero, world.C.z - CFG.SIGN_DEPTH);
  tl.first = true;
}

/* ITEM(u): −1 the tee, 0…8 the panels, linear between */
function itemPose(u, out) {
  const P = tl.P;
  if (u <= -1) return mixPose(P.tee, P.tee, 0, out);
  if (u < 0) return mixPose(P.tee, P.panel, u + 1, out);
  mixPose(P.panel, P.panel, 0, out);
  out.t.x = rack.X(u);
  return out;
}

function scrollPose(s, out) {
  const k = tl.keys;
  if (s >= k[k.length - 1].at) return itemPose(rack.u, out);
  if (s <= k[0].at) return mixPose(k[0].pose, k[0].pose, 0, out);
  let i = 1;
  while (s > k[i].at) i++;
  const a = k[i - 1], b = k[i];
  return mixPose(a.pose, b.pose, easeInOutCubic((s - a.at) / (b.at - a.at)), out);
}

/* ---- controls --------------------------------------------------------- */

export function setNear(on) {
  if (on === tl.nearOn) return;
  tl.nearOn = on;
  tl.nearFrom = tl.s;
  tl.onNear && tl.onNear(on);
}

/* "Šviesa": flips the lights against whatever they are now; the override
   lasts until the applied scroll leaves sk@0.2 … tiek@0.7 */
export function toggleLight() {
  tl.lightOverride = tl.darkWant === 1;   // dark now → force on, lit now → force off
}
export function clearLight() {
  if (tl.lightOverride === null) return false;
  tl.lightOverride = null;
  return true;
}

/* ---- per frame -------------------------------------------------------- */

/* Returns true while the timeline itself is still moving. */
export function update(dt, now) {
  const S = stage.S, A = tl.A, K = CFG.KEY;
  const y = tl.y = tl.frozen !== null ? tl.frozen : window.scrollY;   // the one scroll read per frame

  /* applied scroll */
  const s0 = tl.s, v0 = tl.v;
  let jumped = false;
  if (tl.first) { tl.s = y; jumped = true; tl.first = false; }
  else if (Math.abs(y - tl.s) > CFG.JUMP * S) {
    /* anchor link, End key, restored position: no fly-through, dip instead */
    tl.s = y; jumped = true;
    setCanvasOpacity(0);
    tl.dipUntil = now + CFG.JUMP_MS;
  } else if (tl.calm || tl.frozen !== null) tl.s = y;
  else {
    tl.s += (y - tl.s) * follow(dt, CFG.SCROLL_TAU);
    if (Math.abs(y - tl.s) < 0.3) tl.s = y;
  }
  const s = tl.s;
  tl.v = jumped ? 0 : (s - s0) / dt;
  tl.acc = jumped ? 0 : (tl.v - v0) / dt;
  if (tl.dipUntil && now >= tl.dipUntil) { tl.dipUntil = 0; setCanvasOpacity(1, 160); }

  /* past the rack the stage is covered by opaque blocks */
  tl.asleep = s > A.stBottom && y > A.stBottom;

  /* HUD classes (CSS does the 180 ms transitions) */
  const hudOff = tl.hudOff ? s > A.hudOn : s > A.hudOff;
  if (hudOff !== tl.hudOff) { tl.hudOff = hudOff; html.classList.toggle('hud-off', hudOff); tl.onHud && tl.onHud(hudOff); }
  const typeOff = s > A.typeOff;
  if (typeOff !== tl.typeOff) { tl.typeOff = typeOff; html.classList.toggle('n-off', typeOff); }

  /* rack: where the scroll puts the camera along the rail (soft dwell per panel) */
  const f = 9 * clamp((s - A.stPhotos) / (K.stSpan * S), 0, 1);
  tl.uScroll = -1 + f - CFG.DWELL * Math.sin(2 * Math.PI * f) / (2 * Math.PI);
  tl.rail = clamp((s - A.stRail0) / (A.stRail1 - A.stRail0), 0, 1);
  rack.update(dt, { uScroll: tl.uScroll, rail: tl.rail, railFrom: tl.railSpan[0], railTo: tl.railSpan[1], s, inPhotos: s >= A.stPhotos, dark: tl.dark });

  /* "Iš arti": ease to the print pose without scrolling; scrolling releases it */
  if (tl.nearOn && Math.abs(s - tl.nearFrom) > CFG.NEAR_RELEASE * S) setNear(false);
  const nearWant = tl.nearOn ? 1 : 0;
  if (tl.near !== nearWant) {
    const step = tl.calm ? 1 : dt / (CFG.NEAR_MS / 1000);
    tl.near = nearWant > tl.near ? Math.min(1, tl.near + step) : Math.max(0, tl.near - step);
  }

  /* camera */
  const pose = scrollPose(s, tl.pose);
  if (tl.near > 0) mixPose(pose, tl.P.print, easeInOutCubic(tl.near), pose);
  applyPose(pose);
  const d = tl.d = Math.exp(pose.ln);
  setClose(d < CFG.CLOSE_D);

  /* lights: "Tipas" far, "Stendas" close; out for the only-the-number beat */
  const m = 1 - smoothstep(1.2 * tl.dPrint, 0.8 * tl.dHero, d);
  let want = s >= A.skDark && s < A.tiekLight ? 1 : 0;
  if (tl.lightOverride !== null) {
    if (s < A.keep0 || s > A.keep1) tl.lightOverride = null;
    else want = tl.lightOverride ? 0 : 1;
  }
  if (want !== tl.darkWant) { tl.darkWant = want; tl.onLight && tl.onLight(want === 0); }
  const kL = follow(dt, CFG.LIGHT.tau);
  tl.dark += (want - tl.dark) * kL;
  if (Math.abs(want - tl.dark) < 0.003) tl.dark = want;
  /* the red line draws with the scroll; a manual lights-out shows it whole */
  const lineWant = tl.lightOverride === false ? 1 : clamp((s - A.skLine0) / (A.skLine1 - A.skLine0), 0, 1);
  tl.line += (lineWant - tl.line) * kL;
  if (Math.abs(lineWant - tl.line) < 0.003) tl.line = lineWant;
  /* along the rack the rims fade out and the key halves */
  const fade = smoothstep(CFG.LIGHT.rackFade[0], CFG.LIGHT.rackFade[1], stage.camera.position.x - world.C.x);
  setLights(m, tl.dark, 1 - fade, lerp(1, CFG.LIGHT.rackKey, fade), tl.line, quality.tier);

  /* the giant 47: one transform and one opacity */
  if (!typeOff) projectSign(smoothstep(1.2 * tl.dPrint, 2.2 * tl.dPrint, d));

  return Math.abs(y - s) > 0 || tl.near !== nearWant || tl.dark !== want || tl.line !== lineWant || tl.dipUntil > 0;
}
