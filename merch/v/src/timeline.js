/* Timeline: scroll anchors, the smoothed ("applied") scroll, the jump dip,
   and what the scroll position means each frame: camera pose, light state,
   the giant NA2's projection, and when the range input and the colour
   swatches are live.

   Scroll owns camera and light; the hand owns the figure's yaw (spin.js).
   The story walks the camera once round the figure: front, chest, side,
   back, the map in the dark, the other side, and front again as an item
   under the rail. */
import { ART, CFG, clamp, lerp, smoothstep, easeInOutCubic, follow, rad } from './config.js';
import { stage, fitDistance, makePose, mixPose, blankPose, applyPose, setSign, projectSign, setCanvasOpacity, lowestOnScreen } from './stage.js';
import { world, setLights } from './scene.js';
import { rack } from './rack.js';
import { setClose } from './spin.js';
import { quality } from './quality.js';
import { Vector3 } from 'three';

export const tl = {
  y: 0,                 // window.scrollY this frame
  s: 0,                 // applied scroll: follows y with a 0.12 s time constant
  frozen: null,         // ?s= test hook: the applied scroll is pinned here
  A: {},                // anchors in px of scroll
  keys: [],             // camera keyframes { at, pose }
  P: {},                // named poses
  pose: blankPose(),
  d: 1, dHero: 1, dChest: 1,
  hold: false,          // the story holds the figure to its front (±35°)
  dark: 0, darkWant: 0, // lights: 0 on … 1 out
  line: 0, rail: 0, railSpan: [0, 0], uScroll: -1,
  asleep: false, uiOff: false, typeOff: false,
  swOn: false,          // the colour swatches are shown
  info: [0, 0],         // document y of the info block's top and bottom edge
  dipUntil: 0,
  first: true,
  onUi: null,           // (off) → controls: the range input is live in the hero only
  onSwatches: null      // (on) → controls
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
  const info = rectOf('info'), st = rectOf('stovas');
  tl.info = [info.top + y0, info.bottom + y0];

  const A = tl.A = {
    creepEnd: K.creepEnd * S, chestAt: K.chestAt * S, typeOff: K.typeOff * S,
    uiOff: K.uiOff * S, uiOn: K.uiOn * S,
    holdFrom: K.holdFrom * S,
    walkFrom: K.walkFrom * S, side: K.side * S, back: K.back * S,
    mapFrom: K.mapFrom * S, mapAt: K.mapAt * S,
    dark: K.dark * S, line0: K.line0 * S, line1: K.line1 * S,
    infoLight: at('info', K.infoLight), infoBack: at('info', K.infoBack),
    stBottom: st.top + y0 + st.height
  };

  /* The way back to the front: back → the other side → item, timed from the
     end of the info block. Each leg gets at least K.walk screens, whatever
     the block's height, and everything after it moves along. */
  const walk = K.walk * S, gap = K.minGap * S;
  A.stSide = Math.max(at('stovas', K.stSide), A.infoBack + walk);
  A.stItem = Math.max(at('stovas', K.stItem), A.stSide + walk);
  A.stFree = A.stItem - (K.stItem - K.stFree) * S;
  A.stRail0 = Math.max(at('stovas', K.stRail0), A.stItem + gap);
  A.stRail1 = A.stRail0 + (K.stRail1 - K.stRail0) * S;
  A.stPhotos = Math.max(at('stovas', K.stPhotos), A.stRail1 + gap);
  /* the camera has passed the last photo when the grid reaches the viewport */
  A.stEnd = Math.max(A.stPhotos + S, A.stBottom - S);

  /* poses, solved against the frame rects */
  const R = stage.rect, Q = CFG.POSE, P = tl.P, w = world;
  const top3 = w.TOP.getSize(new Vector3()), pf = w.PF.getSize(new Vector3());
  const pfC = w.PF.getCenter(new Vector3());
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

  /* the back: the artwork (map and caption) with a margin; then, for the
     dark beat, closer: the artwork and the red line under its caption fill
     the frame */
  const art = w.art, shot = w.mapShot, air = 1 + 2 * CFG.MAP_AIR;
  P.back = makePose(art.c, fitDistance(art.w * CFG.BACK_GROW, art.h * CFG.BACK_GROW, R.print), Q.BACK, R.print);
  P.map = makePose(shot.c, fitDistance(shot.w * air, shot.h + shot.w * (air - 1), R.print), Q.MAP, R.print);

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
    { at: A.walkFrom, pose: P.chest2 },
    { at: A.side, pose: P.side },
    { at: A.back, pose: P.back },
    { at: A.mapFrom, pose: P.back },
    { at: A.mapAt, pose: P.map },
    { at: A.infoLight, pose: P.map },
    { at: A.infoBack, pose: P.back },
    { at: A.stSide, pose: P.side2 },
    { at: A.stItem, pose: P.item },
    { at: A.stPhotos, pose: P.item }
  ];
  /* a keyframe is never less than 0.05 S after the previous one */
  for (let i = 1; i < keys.length; i++) keys[i].at = Math.max(keys[i].at, keys[i - 1].at + gap);

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

/* ---- colour swatches --------------------------------------------------- */

/* The two dots sit at the bottom centre of the stage. They are shown while
   the figure is the subject and nothing of the tee is behind them: the
   lights are on, the hem is clear above their row, the info block is not
   passing over it, and the camera has not left for the photos. */
function swatchesWanted(s) {
  const W = CFG.SWATCH, row = stage.rect.sw;
  if (tl.darkWant || tl.asleep || s >= tl.A.stPhotos) return false;
  if (tl.info[0] - s - W.lip < row.y + row.h && tl.info[1] - s + W.lip > row.y) return false;
  const hem = lowestOnScreen(world.hem, world.yaw.matrixWorld);
  return hem < row.y - (tl.swOn ? W.off : W.on);
}

/* ---- per frame -------------------------------------------------------- */

/* Returns true while the timeline itself is still moving. */
export function update(dt, now) {
  const S = stage.S, A = tl.A;
  const y = tl.y = tl.frozen !== null ? tl.frozen : window.scrollY;   // the one scroll read per frame

  /* applied scroll */
  if (tl.first) { tl.s = y; tl.first = false; }
  else if (Math.abs(y - tl.s) > CFG.JUMP * S) {
    /* End key, restored position: no fly-through, dip instead */
    tl.s = y;
    setCanvasOpacity(0);
    tl.dipUntil = now + CFG.JUMP_MS;
  } else if (tl.frozen !== null) tl.s = y;
  else {
    tl.s += (y - tl.s) * follow(dt, CFG.SCROLL_TAU);
    if (Math.abs(y - tl.s) < 0.3) tl.s = y;
  }
  const s = tl.s;
  if (tl.dipUntil && now >= tl.dipUntil) { tl.dipUntil = 0; setCanvasOpacity(1, 160); }

  /* past the rack the stage is covered by the grid */
  tl.asleep = s > A.stBottom && y > A.stBottom;

  /* classes (CSS does the transitions) */
  const uiOff = tl.uiOff ? s > A.uiOn : s > A.uiOff;
  if (uiOff !== tl.uiOff) { tl.uiOff = uiOff; html.classList.toggle('ui-off', uiOff); tl.onUi && tl.onUi(uiOff); }
  const typeOff = s > A.typeOff;
  if (typeOff !== tl.typeOff) { tl.typeOff = typeOff; html.classList.toggle('n-off', typeOff); }

  /* rack: where the scroll puts the camera along the rail (soft dwell per panel) */
  const f = 9 * clamp((s - A.stPhotos) / (A.stEnd - A.stPhotos), 0, 1);
  tl.uScroll = -1 + f - CFG.DWELL * Math.sin(2 * Math.PI * f) / (2 * Math.PI);
  tl.rail = clamp((s - A.stRail0) / (A.stRail1 - A.stRail0), 0, 1);
  rack.update(dt, { uScroll: tl.uScroll, rail: tl.rail, railFrom: tl.railSpan[0], railTo: tl.railSpan[1], s, inPhotos: s >= A.stPhotos, dark: tl.dark });

  /* From the push-in until the camera is nearly back in front the story
     holds the figure to its front and the camera does the walking; the hand
     only wiggles it. */
  tl.hold = s >= A.holdFrom && s < A.stFree;
  setClose(tl.hold, 0);

  /* camera */
  const pose = scrollPose(s, tl.pose);
  applyPose(pose);
  const d = tl.d = Math.exp(pose.ln);

  /* lights: "Tipas" in the hero and on the rack, "Stendas" for the whole
     close story; out for the only-the-map beat */
  const m = smoothstep(A.creepEnd, A.chestAt, s) * (1 - smoothstep(A.infoBack, A.stItem, s));
  const want = s >= A.dark && s < A.infoLight ? 1 : 0;
  tl.darkWant = want;
  const kL = follow(dt, CFG.LIGHT.tau);
  tl.dark += (want - tl.dark) * kL;
  if (Math.abs(want - tl.dark) < 0.003) tl.dark = want;
  /* the red line draws with the scroll */
  const lineWant = clamp((s - A.line0) / (A.line1 - A.line0), 0, 1);
  tl.line += (lineWant - tl.line) * kL;
  if (Math.abs(lineWant - tl.line) < 0.003) tl.line = lineWant;
  /* along the rack the rims fade out and the key halves */
  const fade = s >= A.stPhotos ? smoothstep(CFG.LIGHT.rackFade[0], CFG.LIGHT.rackFade[1], pose.t.x - world.axis.x) : 0;
  setLights(m, tl.dark, 1 - fade, lerp(1, CFG.LIGHT.rackKey, fade), tl.line, quality.tier, pose.az);

  /* the giant NA2: one transform and one opacity */
  if (!typeOff) projectSign(smoothstep(1.2 * tl.dChest, 2.2 * tl.dChest, d));

  /* colour swatches */
  const swOn = swatchesWanted(s);
  if (swOn !== tl.swOn) { tl.swOn = swOn; html.classList.toggle('sw-on', swOn); tl.onSwatches && tl.onSwatches(swOn); }

  return Math.abs(y - s) > 0 || tl.dark !== want || tl.line !== lineWant || tl.dipUntil > 0;
}
