/* /merch in 3D: boot order, the ready sequence, the fall back to the static
   page, and the test hooks.

   The inline gate in index.html decided that this device gets 3D and added
   class "gl" to <html>; the page is already painted and scrollable. */
import { CFG, clamp } from './config.js';
import { loadAssets } from './load.js';
import { stage, initStage, measure, setCanvasOpacity } from './stage.js';
import { world, shirt, stepShirt, buildScene, buildEnvironment, disposeScene } from './scene.js';
import { tl, layout, update } from './timeline.js';
import { spin, initSpin, initPointer, stepSpin, spinBusy, grab, drag, release, yaw, detent } from './spin.js';
import { rack } from './rack.js';
import { initControls, say, setColor } from './controls.js';
import { quality, startTier } from './quality.js';
import { loop } from './loop.js';

const html = document.documentElement;
const params = new URLSearchParams(location.search);
const forced = params.get('3d') === '1';   // ?3d=1: the tests run on software GL (see quality.lab)

const app = {
  ready: false,
  fallback: null,
  lastInput: -1e9,        // ms; idle sway runs for a few seconds after it
  rackDrag: false,        // the current horizontal gesture belongs to the rack
  uiTimer: 0,
  swayPhase: 0,
  odd: false,
  abort: new AbortController(),
  timeout: 0
};

/* ---- test hooks (6.12) ------------------------------------------------ */

window.__m = {
  get ready() { return app.ready; },
  get tier() { return quality.tier; },
  get dpr() { return stage.dpr; },
  get calls() { return stage.renderer ? stage.renderer.info.render.calls : 0; },
  get tris() { return stage.renderer ? stage.renderer.info.render.triangles : 0; },
  get yaw() { return app.ready ? ((yaw() % 360) + 360) % 360 : 0; },
  get detent() { return app.ready ? detent() : null; },
  get u() { return rack.u; },
  get L() { return tl.dark; },
  /* the colour of the tee, 'black' or 'white'; assigning switches it like a press on a swatch */
  get color() { return shirt.name; },
  set color(name) { if (app.ready && !app.fallback) setColor(name); },
  get fallback() { return app.fallback; },
  /* extras for the test scripts */
  get s() { return tl.s / stage.S; },
  get d() { return tl.d; },
  get az() { return tl.pose.az * 180 / Math.PI; },
  get frames() { return loop.frames; },
  get running() { return loop.running; },
  get lights() { let n = 0; if (world.scene) world.scene.traverse(o => { if (o.isLight) n++; }); return n; },
  get shadows() { return stage.renderer ? stage.renderer.shadowMap.enabled : false; },
  at(id, t) { return (document.getElementById(id).getBoundingClientRect().top + scrollY - stage.S + t * stage.S) / stage.S; }
};
/* with ?3d=1 the test scripts may also reach inside */
if (forced) window.__m.dbg = { CFG, world, stage, tl, spin, shirt, rack, loop, quality, buildEnvironment, goStatic: r => goStatic(r) };

/* ---- fall back to the static page (5.4) ------------------------------- */

export function goStatic(reason) {
  if (app.fallback) return;
  app.fallback = reason || 'unknown';
  clearTimeout(app.timeout);
  clearTimeout(app.uiTimer);
  app.abort.abort();
  loop.block('static', true);

  const change = () => {
    html.classList.remove('gl', 'rdy', 'ui-off', 'n-off', 'sw-on', 'kf', 'drag');
    html.style.removeProperty('--p');
    if (stage.n) { stage.n.style.transform = ''; stage.n.style.opacity = ''; }
    try { disposeScene(); } catch (e) { /* nothing to free */ }
    if (stage.renderer) { try { stage.renderer.dispose(); stage.renderer.forceContextLoss(); } catch (e) { /* already gone */ } }
    const c = document.getElementById('gl');
    if (c) c.remove();
    say('');
  };
  /* the page's own helper keeps the reader's place across the change (the one scripted scroll, see index.html) */
  if (window.__keep) window.__keep(change); else change();
}

/* ---- frame ------------------------------------------------------------ */

const rad = Math.PI / 180;

function frame(dt, now) {
  /* 1. scroll → camera, lights, classes */
  const moving = update(dt, now);
  if (tl.asleep) return false;          // past the rack: stop until the next scroll event

  /* 2. the hand: yaw */
  stepSpin(dt);
  const busy = spinBusy();

  /* 3. the colour of the tee easing from one to the other */
  const tinting = stepShirt(dt);

  /* 4. idle sway for a few seconds after the last input, hero only */
  const since = (now - app.lastInput) / 1000;
  let sway = 0, swaying = false;
  const W = CFG.SWAY;
  if (quality.tier < 3 && !busy && !tl.uiOff && since < W.life) {
    app.swayPhase += dt;
    const env = clamp(app.swayPhase / 0.8, 0, 1) * clamp((W.life - since) / 1.2, 0, 1);
    sway = W.deg * Math.sin(2 * Math.PI * W.hz * app.swayPhase) * env;
    swaying = true;
  } else if (busy) app.swayPhase = 0;

  world.yaw.rotation.y = (yaw() + sway) * rad;

  /* 5. draw; when only the idle sway is left, every second frame is enough */
  app.odd = !app.odd;
  const onlySway = swaying && !moving && !busy && !tinting;
  if (!(onlySway && app.odd)) stage.renderer.render(world.scene, stage.camera);

  return moving || busy || tinting || swaying || now < stage.fadeUntil;
}

function touch() { app.lastInput = performance.now(); loop.wake(); }

/* ---- resize (6.8) ----------------------------------------------------- */

function watchResize() {
  let timer = 0, w = innerWidth, h = innerHeight;
  const run = () => {
    timer = 0;
    if (app.fallback) return;
    const dw = Math.abs(innerWidth - w), dh = Math.abs(innerHeight - h);
    /* a phone toolbar sliding in or out changes only the height, a little: ignore it */
    if (stage.coarse && dw === 0 && dh < CFG.TOOLBAR_PX && dh > 0) return;
    w = innerWidth; h = innerHeight;
    measure(quality.tier);
    layout();
    rack.layout();
    loop.wake();
  };
  const later = () => { clearTimeout(timer); timer = setTimeout(run, CFG.RESIZE_MS); };
  if (window.ResizeObserver) new ResizeObserver(later).observe(document.body);
  addEventListener('resize', later, { passive: true });
  addEventListener('orientationchange', later, { passive: true });
}

/* ---- ready sequence (5.2) --------------------------------------------- */

/* from here on the swatches may show and the cursor says the figure can be turned */
function showUi() { html.classList.add('rdy'); }

function lightsOn() {
  const A = CFG.ARRIVAL;
  let freeze = params.get('s');
  if (freeze !== null) {
    /* ?s=1.25 or ?s=info@0.15: jump there and pin the timeline (tests only) */
    const m = /^([a-z]+)@([\d.]+)$/.exec(freeze);
    const S = m ? window.__m.at(m[1], +m[2]) : parseFloat(freeze);
    if (isFinite(S)) {
      window.scrollTo({ top: Math.round(S * stage.S), left: 0, behavior: 'instant' });
      tl.frozen = Math.round(S * stage.S);
      tl.first = true;
    } else freeze = null;
  }

  say('3D vaizdas paruoštas.');
  app.ready = true;
  clearTimeout(app.timeout);

  if (freeze === null && window.scrollY < A.maxScroll * stage.S) {
    /* arrival: a short flicker while the figure turns in. The turn is a
       synthetic flick from behind that the ordinary spin code lands on the front. */
    for (const [ms, o] of A.flicker) setTimeout(() => { if (!app.fallback) setCanvasOpacity(o); }, ms);
    spin.core.x = A.from;
    spin.core.release(-A.from * CFG.SPIN.k);
    const settle = spin.onSettle;
    let done = false;
    const finish = () => { if (done) return; done = true; app.uiTimer = setTimeout(showUi, A.uiDelayMs); };
    spin.onSettle = d => { spin.onSettle = settle; settle(d); finish(); };
    spin.onInput = () => { touch(); finish(); };    // any pointerdown takes over
  } else {
    /* reloaded mid-page: fade in at the pose for that scroll */
    setCanvasOpacity(1, A.fadeMs);
    showUi();
  }
  touch();
}

async function boot() {
  startTier(params);
  say('Kraunamas 3D vaizdas.');

  /* not ready 10 s after app.js starts → static page, fetches aborted
     (20 s with ?3d=1: software rendering needs longer to compile and draw) */
  app.timeout = setTimeout(() => goStatic('timeout'), forced ? CFG.TIMEOUT_LAB_MS : CFG.TIMEOUT_MS);

  if (!initStage()) return goStatic('webgl');
  const setP = p => html.style.setProperty('--p', p.toFixed(4));

  let assets;
  try {
    assets = await loadAssets(setP, app.abort.signal);
  } catch (e) {
    return goStatic(app.fallback || 'load');
  }
  if (app.fallback) return;

  try {
    initSpin();
    buildScene(assets.gltf, assets, stage.renderer, quality.tier);
    rack.build(world.scene, { world, stage, loop });
    measure(quality.tier);
    layout();
    rack.layout();
    initControls();

    /* compile off the main path, then one hidden frame so nothing hitches when the lights come on */
    setCanvasOpacity(0);
    update(1 / 60, performance.now());
    await stage.renderer.compileAsync(world.scene, stage.camera);
    if (app.fallback) return;
    stage.renderer.render(world.scene, stage.camera);
  } catch (e) {
    return goStatic('decode');
  }
  setP(1);

  /* the hand */
  spin.onInput = touch;
  /* Degrees per pixel. Far away the spec's rate applies. Close up that rate
     would throw the print across the screen, so there the cloth tracks the
     finger 1:1 instead (printR = distance from the yaw axis to the prints). */
  const rateAt = rate => Math.min(rate, tl.d / (world.printR * stage.f) * 180 / Math.PI);
  /* how many screen pixels one step along the rack is right now (4.2: 0.66·f/d) */
  const pxPerPanel = () => CFG.PANEL.step * stage.f / tl.d;
  initPointer({
    canStart: () => app.ready && !app.fallback && !tl.asleep,
    start: () => {
      app.rackDrag = tl.s >= tl.A.stPhotos;
      if (app.rackDrag) rack.onDragStart(); else grab();
      spin.onInput();
    },
    move: (dx, rate) => {
      if (app.rackDrag) rack.onDrag(dx, pxPerPanel());
      else drag(dx * rateAt(rate));
      touch();
    },
    end: (v, rate) => { if (app.rackDrag) rack.onDragEnd(v, pxPerPanel()); else release(v * rateAt(rate)); touch(); },
    tap: e => { if (tl.s >= tl.A.stPhotos) rack.onTap(e); }
  });

  /* wake on anything that can change the picture */
  addEventListener('scroll', () => loop.wake(), { passive: true });
  addEventListener('keydown', () => loop.wake(), { passive: true });
  document.addEventListener('visibilitychange', () => loop.block('hidden', document.hidden));
  watchResize();

  /* a tier change (the governor, later) only needs the new pixel ratio; the lights read the tier every frame */
  quality.onChange = t => { measure(t); layout(); rack.layout(); loop.wake(); };

  loop.start(frame);
  if (document.hidden) loop.block('hidden', true);
  lightsOn();
}

boot();
