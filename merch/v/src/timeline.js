/* Timeline: scroll anchors, the smoothed ("applied") scroll, the jump dip,
   and what the scroll position means each frame: camera pose, light state,
   the giant NA2's projection and the HUD classes.

   Scroll owns camera and light; the hand owns the figure's yaw (spin.js).
   The story walks the camera once round the figure: front, chest, side,
   back, the map in the dark, the other side, and front again as an item
   under the rail. */
import { ART, CFG, clamp, lerp, smoothstep, easeInOutCubic, follow, rad } from './config.js';
import { stage, fitDistance, makePose, mixPose, blankPose, applyPose, setSign, projectSign, setCanvasOpacity } from './stage.js';
import { world, setLights } from './scene.js';
import { rack } from './rack.js';
import { setClose } from './spin.js';
import { quality } from './quality.js';
import { Vector3 } from 'three';

export const tl = {
  y: 0,                 // window.scrollY this frame
  s: 0,                 // applied scroll: follows y with a 0.12 s time constant
  frozen: null,         // ?s= test hook: the applied scroll is pinned here
  calm: false,
  A: {},                // anchors in px of scroll
  keys: [],             // camera keyframes { at, pose }
  P: {},                // named poses
  pose: blankPose(),
  d: 1, dHero: 1, dChest: 1,
  near: 0, nearOn: false, nearFrom: 0, nearBack: false,   // "Iš arti"; nearBack: the figure shows its back
  hold: false,          // the story holds the figure to its front (±35°)
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
    creepEnd: K.creepEnd * S, chestAt: K.chestAt * S,
    hudOff: K.hudOff * S, hudOn: K.hudOn * S, typeOff: K.typeOff * S,
    holdFrom: K.holdFrom * S,
    apFrom: at('ap', tall ? K.apFromP : K.apFrom), apSide: at('ap', tall ? K.apSideP : K.apSide), apBack: at('ap', tall ? K.apBackP : K.apBack),
    skMapFrom: at('sk', K.skMapFrom), skMapAt: at('sk', K.skMapAt),
    skDark: at('sk', K.skDark), skLine0: at('sk', K.skLine0), skLine1: at('sk', K.skLine1),
    tiekLight: at('tiek', K.tiekLight), tiekBack: at('tiek', K.tiekBack),
    stBottom: st.top + y0 + st.height,
    keep0: at('sk', K.lightKeep0), keep1: at('tiek', K.lightKeep1)
  };

  /* The way back to the front: back → the other side → item. A short facts
     plate (the landscape cards) leaves less scroll between tiek@0.80 and
     stovas@0.40 than that half circle needs, so each leg gets at least
     K.walk screens and everything after it moves along. */
  const walk = K.walk * S;
  A.stSide = Math.max(at('stovas', K.stSide), A.tiekBack + walk);
  A.stItem = Math.max(at('stovas', K.stItem), A.stSide + walk);
  A.stFree = A.stItem - (K.stItem - K.stFree) * S;
  A.stRail0 = Math.max(at('stovas', tall ? K.stRail0P : K.stRail0), A.stItem + K.minGap * S);
  A.stRail1 = A.stRail0 + (tall ? K.stRail1P - K.stRail0P : K.stRail1 - K.stRail0) * S;
  A.stPhotos = Math.max(at('stovas', tall ? K.stPhotosP : K.stPhotos), A.stRail1);
  /* the camera has passed the last photo when the grid reaches the viewport */
  A.stEnd = Math.max(A.stPhotos + S, A.stBottom - S);

  /* poses, solved against the frame rects */
  const R = stage.rect, Q = CFG.POSE, P = tl.P, w = world;
  const top3 = w.TOP.getSize(new Vector3()), pf = w.PF.getSize(new Vector3()), pb = w.PB.getSize(new Vector3());
  const pfC = w.PF.getCenter(new Vector3()), pbC = w.PB.getCenter(new Vector3());
  /* how wide a box looks from an azimuth */
  const wide = (size, az) => Math.abs(Math.cos(rad(az))) * size.x + Math.abs(Math.sin(rad(az))) * size.z;

  tl.dHero = fitDistance(top3.x, top3.y, R.hero);
  P.hero = makePose(w.C, tl.dHero, Q.HERO, R.hero);
  P.hero2 = makePose(w.C, tl.dHero * CFG.HERO_CREEP, Q.HERO, R.hero);

  /* the chest lettering, never closer than its texture stays sharp */
  const sharp = pf.x / (ART.front.w || 1024) * stage.f * stage.dpr / CFG.CHEST_SHARP;
  tl.dChest = Math.max(fitDistance(pf.x * CFG.CHEST_GROW, pf.y * CFG.CHEST_GROW, R.print), sharp);
  P.chest = makePose(pfC, tl.dChest, Q.CHEST, R.print);
  P.chest2 = makePose(pfC, tl.dChest, Q.CHEST_END, R.print);

  const dSide = fitDistance(wide(top3, Q.SIDE.az), top3.y, R.print);
  P.side = makePose(w.C, dSide, Q.SIDE, R.print);
  P.side2 = makePose(w.C, dSide, Q.SIDE2, R.print);

  const dBack = fitDistance(pb.x * CFG.BACK_GROW, pb.y * CFG.BACK_GROW, R.print);
  P.back = makePose(pbC, dBack, Q.BACK, R.print);
  /* the map in the dark: closer, slightly tilted, the caption and its red line on screen */
  const part = tall ? CFG.MAP_PART_P : CFG.MAP_PART_L;
  _t.set(pbC.x, w.PB.max.y - pb.y * (part[0] + part[1]) / 2, pbC.z);
  P.map = makePose(_t, fitDistance(pb.x, pb.y * (part[1] - part[0]), R.print), Q.MAP, R.print);
  /* "Iš arti" with the figure turned round: its back print, where a half turn about the yaw axis puts it */
  _t.set(2 * w.axis.x - pbC.x, pbC.y, 2 * w.axis.z - pbC.z);
  P.nearBack = makePose(_t, dBack, Q.NEAR_BACK, R.print);

  /* the figure as an item under the rail: head to hem plus the rail above it */
  const railTop = w.Yr + CFG.RAIL.size;
  _t.set(w.C.x, (railTop + w.TOP.min.y) / 2, w.C.z);
  P.item = makePose(_t, fitDistance(top3.x * 1.04, (railTop - w.TOP.min.y) * 1.04, R.item), Q.ITEM, R.item);
  /* world x of the screen's left and right edge at that pose: the rail draws across it */
  const perPx = Math.exp(P.item.ln) / stage.f;
  tl.railSpan = [P.item.t.x - P.item.cx * perPx, P.item.t.x + (stage.W - P.item.cx) * perPx];
  /* a photo panel as an item (the camera slides along x for the others) */
  _t.set(rack.X(0), w.Yr - CFG.PANEL.drop, w.axis.z);
  P.panel = makePose(_t, fitDistance(CFG.PANEL.size, CFG.PANEL.size, R.item), Q.ITEM, R.item);

  const keys = tl.keys = [
    { at: 0, pose: P.hero },
    { at: A.creepEnd, pose: P.hero2 },
    { at: A.chestAt, pose: P.chest },
    { at: A.apFrom, pose: P.chest2 },
    { at: A.apSide, pose: P.side },
    { at: A.apBack, pose: P.back },
    { at: A.skMapFrom, pose: P.back },
    { at: A.skMapAt, pose: P.map },
    { at: A.tiekLight, pose: P.map },
    { at: A.tiekBack, pose: P.back },
    { at: A.stSide, pose: P.side2 },
    { at: A.stItem, pose: P.item },
    { at: A.stPhotos, pose: P.item }
  ];
  /* a keyframe is never less than 0.05 S after the previous one */
  for (let i = 1; i < keys.length; i++) keys[i].at = Math.max(keys[i].at, keys[i - 1].at + K.minGap * S);

  /* the giant NA2 is pinned 2 m behind the figure as seen from the hero pose */
  setSign(P.hero, w.C.z - CFG.SIGN_DEPTH);
  tl.first = true;
}

/* ITEM(u): −1 the figure, 0…8 the panels, linear between */
function itemPose(u, out) {
  const P = tl.P;
  if (u <= -1) return mixPose(P.item, P.item, 0, out);
  if (u < 0) return mixPose(P.item, P.panel, u + 1, out);
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

/* "Iš arti": the camera eases to the print that faces it. back = the figure
   is turned round, so that print is the map. */
export function setNear(on, back) {
  if (on === tl.nearOn) return;
  tl.nearOn = on;
  if (on) { tl.nearBack = !!back; tl.nearFrom = tl.s; }
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
  const S = stage.S, A = tl.A;
  const y = tl.y = tl.frozen !== null ? tl.frozen : window.scrollY;   // the one scroll read per frame

  /* applied scroll */
  if (tl.first) { tl.s = y; tl.first = false; }
  else if (Math.abs(y - tl.s) > CFG.JUMP * S) {
    /* anchor link, End key, restored position: no fly-through, dip instead */
    tl.s = y;
    setCanvasOpacity(0);
    tl.dipUntil = now + CFG.JUMP_MS;
  } else if (tl.calm || tl.frozen !== null) tl.s = y;
  else {
    tl.s += (y - tl.s) * follow(dt, CFG.SCROLL_TAU);
    if (Math.abs(y - tl.s) < 0.3) tl.s = y;
  }
  const s = tl.s;
  if (tl.dipUntil && now >= tl.dipUntil) { tl.dipUntil = 0; setCanvasOpacity(1, 160); }

  /* past the rack the stage is covered by opaque blocks */
  tl.asleep = s > A.stBottom && y > A.stBottom;

  /* HUD classes (CSS does the 180 ms transitions) */
  const hudOff = tl.hudOff ? s > A.hudOn : s > A.hudOff;
  if (hudOff !== tl.hudOff) { tl.hudOff = hudOff; html.classList.toggle('hud-off', hudOff); tl.onHud && tl.onHud(hudOff); }
  const typeOff = s > A.typeOff;
  if (typeOff !== tl.typeOff) { tl.typeOff = typeOff; html.classList.toggle('n-off', typeOff); }

  /* rack: where the scroll puts the camera along the rail (soft dwell per panel) */
  const f = 9 * clamp((s - A.stPhotos) / (A.stEnd - A.stPhotos), 0, 1);
  tl.uScroll = -1 + f - CFG.DWELL * Math.sin(2 * Math.PI * f) / (2 * Math.PI);
  tl.rail = clamp((s - A.stRail0) / (A.stRail1 - A.stRail0), 0, 1);
  rack.update(dt, { uScroll: tl.uScroll, rail: tl.rail, railFrom: tl.railSpan[0], railTo: tl.railSpan[1], s, inPhotos: s >= A.stPhotos, dark: tl.dark });

  /* From "Artyn" to "Kol kas tiek" the story holds the figure to its front
     and the camera does the walking; the hand only wiggles it. */
  tl.hold = s >= A.holdFrom && s < A.stFree;

  /* "Iš arti": ease to the print without scrolling; scrolling releases it */
  if (tl.nearOn && (Math.abs(s - tl.nearFrom) > CFG.NEAR_RELEASE * S || (tl.nearBack && tl.hold))) setNear(false);
  const nearWant = tl.nearOn ? 1 : 0;
  if (tl.near !== nearWant) {
    const step = tl.calm ? 1 : dt / (CFG.NEAR_MS / 1000);
    tl.near = nearWant > tl.near ? Math.min(1, tl.near + step) : Math.max(0, tl.near - step);
  }
  const nearK = easeInOutCubic(tl.near);
  setClose(tl.hold || tl.nearOn, tl.hold || !tl.nearBack ? 0 : 180);

  /* camera */
  const pose = scrollPose(s, tl.pose);
  if (tl.near > 0) mixPose(pose, tl.nearBack ? tl.P.nearBack : tl.P.chest, nearK, pose);
  applyPose(pose);
  const d = tl.d = Math.exp(pose.ln);

  /* lights: "Tipas" in the hero and on the rack, "Stendas" for the whole
     close story; out for the only-the-map beat */
  const m = Math.max(nearK, smoothstep(A.creepEnd, A.chestAt, s) * (1 - smoothstep(A.tiekBack, A.stItem, s)));
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
  const fade = s >= A.stPhotos ? smoothstep(CFG.LIGHT.rackFade[0], CFG.LIGHT.rackFade[1], pose.t.x - world.axis.x) : 0;
  setLights(m, tl.dark, 1 - fade, lerp(1, CFG.LIGHT.rackKey, fade), tl.line, quality.tier, pose.az);

  /* the giant NA2: one transform and one opacity */
  if (!typeOff) projectSign(smoothstep(1.2 * tl.dChest, 2.2 * tl.dChest, d) * (1 - nearK));

  return Math.abs(y - s) > 0 || tl.near !== nearWant || tl.dark !== want || tl.line !== lineWant || tl.dipUntil > 0;
}
