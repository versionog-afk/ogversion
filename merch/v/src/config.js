/* Every constant of the /merch 3D page lives here.
   Lengths are metres, angles degrees, times seconds unless a name says otherwise. */

/* Injected by build.cjs: byte sizes for the loader line, the pixel sizes of
   the two prints with the caption box of the back print, and the average
   colour of each rack photo. */
/* global __BYTES__, __ART__, __AVG__ */
export const BYTES = __BYTES__;
export const ART = __ART__;
export const AVG = __AVG__;

/* Runtime files sit next to the bundle, wherever the folder is served from. */
const beside = name => new URL('./' + name, import.meta.url).href;
export const URLS = {
  glb: beside('figure.glb'),
  front: beside('front.webp'),
  back: beside('back.webp'),
  frontHi: beside('front-hi.webp')    // the sharper chest print, swapped in after idle (next stage)
};

export const CFG = {
  /* transparent canvas over the real <h1>; the opaque variant is a later stage */
  SANDWICH: true,

  /* How meshes are recognised: first by mesh name, then by mesh + material +
     parent name; the first class that matches wins. Anything else is "other"
     and is dressed like the trousers. */
  CLASSES: [
    ['printFront', /print.?front/i], ['printBack', /print.?back/i], ['hair', /hair/i], ['pants', /pants|trouser/i],
    ['shoes', /shoe|sneaker|boot/i], ['body', /body|skin|mannequin|figure/i], ['tee', /tee|fabric|shirt|collar|rib|sleeve/i]
  ],

  /* anchors measured on the model */
  TOP_BELOW_HEM: 0.06,        // the "top" box runs from this far below the hem to the top of the head
  CHEST_GROW: 2.4,            // CHEST frames the chest print grown by this
  BACK_GROW: 1.12,            // BACK frames the back print grown by this
  /* MAP frames this part of the back print (v from the top). Portrait: the upper 62 %, the caption sits
     under the frame, on screen. Landscape: the frame is nearly as high as the screen, so there the caption
     has to be inside it and the top of the map may run past it instead. */
  MAP_PART_P: [0, 0.62], MAP_PART_L: [0.08, 1.0],
  /* the red line under the caption of the back print: caption box bottom + dv, drawn as a ribbon on the cloth */
  LINE: { dv: 0.022, height: 0.0025, lift: 0.0005, steps: 48, color: 0xc6362b },

  /* camera */
  FOV_PORTRAIT: 40,
  FOV_LANDSCAPE: 30,
  NEAR: 0.05,
  FAR: 30,
  SIGN_DEPTH: 2.0,            // the giant NA2 behaves like a sign this far behind the figure
  HERO_CREEP: 0.97,           // distance factor reached at 0.2 S
  /* az: camera azimuth round the figure, 0 in front, 180 behind; never wrapped,
     so the story makes one full circle from 0 to 360 */
  POSE: {
    HERO: { az: 0, el: -2, roll: 0 },
    CHEST: { az: 10, el: 3, roll: 0 },
    CHEST_END: { az: 4, el: 3, roll: 0 },
    SIDE: { az: 95, el: 4, roll: 0 },
    BACK: { az: 180, el: 0, roll: 0 },
    MAP: { az: 186, el: 3, roll: -3 },
    SIDE2: { az: 265, el: 4, roll: 0 },
    ITEM: { az: 360, el: 0, roll: 0 },
    NEAR_BACK: { az: 0, el: 0, roll: 0 }   // "Iš arti" with the figure turned round: its back, seen from the front
  },
  CHEST_SHARP: 1.5,           // never magnify a chest-print texel beyond this many device pixels

  /* scroll storyboard, in screens (S) or as block anchors id@t */
  KEY: {
    creepEnd: 0.2, chestAt: 0.8,
    hudOff: 0.15, hudOn: 0.10, typeOff: 0.8,
    holdFrom: 0.25,                       // from here the story holds the figure to its front, ±35°
    apFrom: 0.10, apSide: 0.50, apBack: 1.00,
    skMapFrom: 0.45, skMapAt: 0.85,
    skDark: 0.62, skLine0: 0.75, skLine1: 0.95,
    tiekLight: 0.55, tiekBack: 0.80,
    stSide: 0.15, stFree: 0.30, stItem: 0.40,
    walk: 0.30,                           // least scroll for each leg of the walk back to the front
    stRail0: 0.70, stRail1: 0.90, stPhotos: 0.90, stSpan: 1.40,
    /* Portrait: plates are full width, so whatever happens while a plate is
       still leaving the screen happens behind it. There the windows are
       taller (ap 130svh, sk 100svh, stovas 280svh) and these beats start
       once the frame is clear: the walk round, the rail and the photos. */
    apFromP: 0.50, apSideP: 0.90, apBackP: 1.30,
    stRail0P: 1.05, stRail1P: 1.30, stPhotosP: 1.40,
    lightKeep0: 0.2, lightKeep1: 0.7,     // "Šviesa" override lives inside sk@0.2 … tiek@0.7
    minGap: 0.05
  },
  SCROLL_TAU: 0.12,
  JUMP: 2,                    // a jump of more than this many screens in one frame dips the canvas
  JUMP_MS: 220,
  NEAR_MS: 700,               // "Iš arti" camera ease
  NEAR_RELEASE: 0.35,         // screens of scrolling that release it

  /* rack */
  RAIL: { size: 0.01, above: 0.10, x0: -0.9, x1pad: 0.6, color: 0xc6362b },
  PANEL: { size: 0.60, first: 1.15, step: 0.66, count: 9, drop: 0.35 },
  DWELL: 0.6,

  /* lights */
  LIGHT: {
    /* Spec: key 1.6 and rims 4.0 / 2.5 in "Tipas", 6.0 / 4.0 in "Stendas". The hero is raised after looking
       at renders: with the spec numbers the black tee sank into the black void. */
    key: { color: 0xfff4e6, pos: [0.8, 2, 2.5], tipas: 2.2, stendas: 1.8 },
    rimL: { pos: [-2, 1.2, -2], tipas: [0xefece6, 6.0], stendas: [0xb06cff, 6.0] },
    rimR: { pos: [2.2, 0.6, -1.8], tipas: [0xefece6, 4.0], stendas: [0xff5a7a, 4.0] },
    env: 0.35, envDark: 0.004,
    keyDark: 0.006, rimDark: 0.004,     // spec: 0.05 / 0.1 / 0.1 and env 0.03; the pale figure needs far less to stay unlit
    emissive: 0.22,
    tau: 0.12,
    follow: 1,                          // 1: lamps and environment turn with the camera's azimuth (see scene.js)
    rackKey: 0.5, rackFade: [0.5, 2.5]  // key × this along the rack (spec: 1.6 → 0.8)
  },
  ROOM: {
    size: [6, 4, 6], wall: 0x020203, sigma: 0.04,
    panels: [
      /* colour, multiplier, w, h, position, facing */
      [0xefece6, 6, 2.4, 1.2, [0, 1.6, -2.9], 'z'],
      [0xb06cff, 8, 1.6, 2.4, [-2.9, 0.6, -1.2], 'x'],
      [0xff5a7a, 6, 1.6, 2.4, [2.9, 0.4, -1.2], '-x'],
      [0xdfe6f0, 2, 3.0, 0.4, [0, 1.95, 1], '-y']
    ]
  },

  /* materials */
  /* spec: tee colour 0x0e0e10, rim 8.0 with power 3.0 and no base gain; tuned on renders (see LIGHT) */
  CLOTH: { color: 0x16161a, roughness: 0.9, base: 2.0, rim: 16.0, rimPow: 2.0, sheen: 1, sheenRoughness: 0.75, sheenColor: 0x2a2a30 },
  PANTS: { color: 0x2b2a28, roughness: 0.9, base: 1.0, rim: 8.0, rimPow: 2.2, sheen: 0.6, sheenRoughness: 0.75, sheenColor: 0x3a3832 },
  SHOES: { color: 0x121213, roughness: 0.55 },
  PLASTER: { color: 0xd6cfc3, roughness: 0.62, hairDarker: 0.12 },
  PRINT: { roughness: 0.82 },
  FADE: [0.30, 0.85],         // legs fade into the dark between these heights above the ground

  /* spin */
  STEP: 1 / 120, MAX_STEPS: 4, MAX_DT: 0.05,
  SPIN: {
    touchPerWidth: 220, touchMin: 0.35, touchMax: 0.60, mouse: 0.40,
    sampleMs: 80, vMax: 1440,
    k: 1.6, kick: 20,
    vFlick: 180, kMin: 0.75, kMax: 1.4, vSpring: 90, snap: 18,
    K: 90, zeta: 0.55,
    limit: 35, beyond: 0.35, vClose: 330, zetaClose: 0.8, zetaRange: 0.9, zetaButton: 0.75,
    vRest: 2, xRest: 0.3
  },
  SWAY: { deg: 2, hz: 0.2, life: 4 },
  ARRIVAL: { from: -200, flicker: [[0, 0], [60, 0.25], [120, 0.05], [180, 1]], hudDelayMs: 300, fadeMs: 300, maxScroll: 0.3 },

  /* pointer arbitration */
  EDGE: 20, SLOP: 8, HORIZ: 1.2, TAP_MS: 250, HINT_PX: 12,

  /* loading and fallback */
  TIMEOUT_MS: 10000,
  TIMEOUT_LAB_MS: 20000,      // with ?3d=1 (software GL in tests)

  /* quality tiers: device-pixel-ratio caps (Q2 coming from Q0 uses 1.5) */
  DPR: [2, 1.5, 1.25, 1],
  RESIZE_MS: 150, TOOLBAR_PX: 150
};

export const rad = d => d * Math.PI / 180;
export const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, t) => a + (b - a) * t;
export const smoothstep = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
export const easeInOutCubic = t => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
/* exponential approach with a time constant: how far to move this frame */
export const follow = (dt, tau) => 1 - Math.exp(-dt / tau);
