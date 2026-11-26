/* Every constant of the /merch 3D page lives here.
   Lengths are metres, angles degrees, times seconds unless a name says otherwise. */

/* Injected by build.cjs: byte sizes for the loader line, the print's pixel
   size, and the average colour of each rack photo. */
/* global __BYTES__, __AVG__ */
export const BYTES = __BYTES__;
export const AVG = __AVG__;

export const URLS = {
  glb: '/merch/v/tee.glb',
  print: '/merch/v/print.webp',
  print2k: '/merch/v/print-2048.webp'
};

export const CFG = {
  /* transparent canvas over the real <h1>; the opaque variant is a later stage */
  SANDWICH: true,

  /* the printed "47" inside the print texture (v = 0 at the top) */
  UV47: { u0: 0.4146, u1: 0.4668, v0: 0.588, v1: 0.6405 },
  SIZE47: { w: 0.0157, h: 0.0129 },
  LINE47: { v: 0.649, height: 0.0012, lift: 0.0005 },
  MASK: { w: 512, h: 421, grow: 0.003, feather: 2 },

  /* camera */
  FOV_PORTRAIT: 40,
  FOV_LANDSCAPE: 30,
  NEAR: 0.05,
  FAR: 30,
  SIGN_DEPTH: 2.0,            // the giant 47 behaves like a sign this far behind the shirt
  HERO_CREEP: 0.97,           // distance factor reached at 0.2 S
  CLOSE_D: 1.6,               // below this distance the shirt is "close": front only
  POSE: {
    HERO: { az: 0, el: -3, roll: 0 },
    PRINT: { az: 8, el: 2, roll: 0 },
    PRINT_END: { az: 3, el: 2, roll: 0 },
    MACRO: { az: -10, el: 5, roll: -4 },
    ITEM: { az: 0, el: 0, roll: 0 }
  },
  MACRO_SHARP: 1.5,           // never magnify a print texel beyond this many device pixels

  /* scroll storyboard, in screens (S) or as block anchors id@t */
  KEY: {
    creepEnd: 0.2, printAt: 0.8,
    hudOff: 0.15, hudOn: 0.10, typeOff: 0.8,
    skMacroFrom: 0.45, skMacroAt: 0.85,
    skDark: 0.62, skLine0: 0.75, skLine1: 0.95,
    tiekLight: 0.55, tiekPrint: 0.80,
    stItem: 0.40, itemTravel: 0.30, stRail0: 0.70, stRail1: 0.90, stPhotos: 0.90, stSpan: 1.40,
    /* portrait: the facts plate is full width and still covers the shirt until stovas@1.0,
       so the rail and the photos start later there (and the window is 280svh, not 230) */
    stRail0P: 1.05, stRail1P: 1.30, stPhotosP: 1.40,
    lightKeep0: 0.2, lightKeep1: 0.7,  // "Šviesa" override lives inside sk@0.2 … tiek@0.7
    minGap: 0.05
  },
  SCROLL_TAU: 0.12,
  JUMP: 2,                    // a jump of more than this many screens in one frame dips the canvas
  JUMP_MS: 220,
  NEAR_MS: 700,               // "Iš arti" camera ease
  NEAR_RELEASE: 0.35,         // screens of scrolling that release it

  /* rack */
  RAIL: { size: 0.01, above: 0.04, x0: -0.9, x1pad: 0.6, color: 0xc6362b },
  PANEL: { size: 0.60, first: 1.0, step: 0.66, count: 9, drop: 0.37 },
  DWELL: 0.6,

  /* lights */
  LIGHT: {
    /* spec: key 1.6, rims 4.0 / 2.5 in "Tipas". Raised for the hero after looking at renders:
       with the spec numbers the black shirt sank into the black void. */
    key: { color: 0xfff4e6, pos: [0.8, 2, 2.5], tipas: 2.4, stendas: 1.6 },
    rimL: { pos: [-2, 1.2, -2], tipas: [0xefece6, 6.0], stendas: [0xb06cff, 6.0] },
    rimR: { pos: [2.2, 0.6, -1.8], tipas: [0xefece6, 4.0], stendas: [0xff5a7a, 4.0] },
    env: 0.35, envDark: 0.02,
    keyDark: 0.02, rimDark: 0.05,       // spec: 0.03 / 0.05 / 0.1; lower so that only the 47 reads as lit
    emissive: 0.22,
    tau: 0.12,
    rackKey: 0.5, rackFade: [0.5, 2.5]   // key × this along the rack (spec: 1.6 → 0.8)
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
  /* spec: colour 0x0e0e10, rim 8.0 with power 3.0 and no base gain; tuned on renders (see LIGHT) */
  CLOTH: { color: 0x16161a, roughness: 0.9, base: 1.0, rim: 12.0, rimPow: 2.4, sheen: 1, sheenRoughness: 0.75, sheenColor: 0x2a2a30 },
  PRINT: { roughness: 0.82 },

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
  SWING: { pivot: 0.30, hz: 0.95, zeta: 0.25, max: 7, fromYaw: 0.12, fromScroll: 0.009, poke: 22 },
  SWAY: { deg: 2, hz: 0.2, life: 4 },
  ARRIVAL: { x: -1.4, time: 0.9, omega: 620, flicker: [[0, 0], [60, 0.25], [120, 0.05], [180, 1]], hudDelayMs: 300, fadeMs: 300, maxScroll: 0.3 },

  /* pointer arbitration */
  EDGE: 20, SLOP: 8, HORIZ: 1.2, TAP_MS: 250, HINT_PX: 12,

  /* loading and fallback */
  TIMEOUT_MS: 10000,

  /* quality tiers: device-pixel-ratio caps (Q2 coming from Q0 uses 1.5) */
  DPR: [2, 1.5, 1.25, 1],
  RESIZE_MS: 150, TOOLBAR_PX: 150
};

export const rad = d => d * Math.PI / 180;
export const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, t) => a + (b - a) * t;
export const smoothstep = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
export const easeInOutCubic = t => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
export const easeOutExpo = t => t >= 1 ? 1 : 1 - Math.pow(2, -10 * t);
/* exponential approach with a time constant: how far to move this frame */
export const follow = (dt, tau) => 1 - Math.exp(-dt / tau);
