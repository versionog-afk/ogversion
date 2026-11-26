/* HUD: view buttons, the hidden range input, hints, the live region, the
   "Šviesa" button, Esc order and the bridge to the page's lightbox. */
import { CFG } from './config.js';
import { tl, setNear, toggleLight, clearLight } from './timeline.js';
import { spin, turnTo, yaw, detent } from './spin.js';
import { loop } from './loop.js';

const $ = id => document.getElementById(id);
const html = document.documentElement;
const mod360 = a => ((a % 360) + 360) % 360;

export const hud = {
  el: null, front: null, back: null, near: null, rot: null, hint: null, live: null, status: null, light: null,
  hintGone: false,      // "Suk." leaves for good after the first real spin
  lastDetent: 0
};

export function say(text) { const el = hud.live || $('live'); if (el) el.textContent = text; }
export function setStatus(text) { if (hud.status) hud.status.textContent = text; }

function valueText(deg) {
  const a = mod360(Math.round(deg));
  if (a === 0) return 'Priekis';
  if (a === 180) return 'Nugara';
  if (a === 90 || a === 270) return 'Šonas';
  return a + '°';
}

/* Mirrors the shirt's angle into the controls. */
export function syncControls() {
  const d = detent();
  hud.front.setAttribute('aria-pressed', d === 0 ? 'true' : 'false');
  hud.back.setAttribute('aria-pressed', d === 180 ? 'true' : 'false');
  const a = Math.min(345, Math.round(mod360(yaw()) / 15) * 15 % 360);
  if (document.activeElement !== hud.rot) hud.rot.value = String(a);
  hud.rot.setAttribute('aria-valuetext', valueText(+hud.rot.value));
}

function showHint() {
  const keys = html.classList.contains('kf');
  hud.hint.textContent = keys ? '← → Suk.' : hud.hintGone ? '' : 'Suk.';
}

/* called by the pointer code */
export function hintSpun() {
  if (hud.hintGone) return;
  hud.hintGone = true;
  showHint();
}
export function hintPulse() {
  if (hud.hintGone) return;
  hud.hint.classList.remove('pulse');
  void hud.hint.offsetWidth;              // restart the CSS animation
  hud.hint.classList.add('pulse');
}

export function initHud() {
  hud.el = document.querySelector('.hud');
  hud.front = $('bf'); hud.back = $('bb'); hud.near = $('bz');
  hud.rot = $('rot'); hud.hint = $('hint'); hud.live = $('live'); hud.status = $('st'); hud.light = $('sv');

  hud.front.addEventListener('click', () => { setNear(false); turnTo(0, CFG.SPIN.zetaButton); spin.onInput(); });
  hud.back.addEventListener('click', () => { setNear(false); turnTo(180, CFG.SPIN.zetaButton); spin.onInput(); });
  hud.near.addEventListener('click', () => { setNear(!tl.nearOn); spin.onInput(); });

  /* keyboard rotation: arrows, Home and End on a real range input */
  hud.rot.addEventListener('input', () => {
    setNear(false);
    turnTo(+hud.rot.value, CFG.SPIN.zetaRange);
    hud.rot.setAttribute('aria-valuetext', valueText(+hud.rot.value));
    spin.onInput();
  });
  /* the input is 1 px large, so only a keyboard (or a screen reader) can focus it:
     show where the focus is with a ring on the shirt and say which keys turn it */
  hud.rot.addEventListener('focus', () => { html.classList.add('kf'); showHint(); });
  hud.rot.addEventListener('blur', () => { html.classList.remove('kf'); showHint(); syncControls(); });

  hud.light.addEventListener('click', () => { toggleLight(); loop.wake(); });

  /* timeline → controls */
  tl.onNear = on => { hud.near.setAttribute('aria-pressed', on ? 'true' : 'false'); html.classList.toggle('near', on); loop.wake(); };
  tl.onLight = on => hud.light.setAttribute('aria-pressed', on ? 'true' : 'false');
  tl.onHud = off => { hud.el.inert = off; if (off && hud.el.contains(document.activeElement)) document.activeElement.blur(); };

  /* shirt → controls and the live region */
  spin.onSettle = d => {
    syncControls();
    if (d !== null && d !== hud.lastDetent) { hud.lastDetent = d; say(d === 0 ? 'Priekis.' : 'Nugara.'); }
  };

  /* Esc closes, in order: lightbox (its own handler), "Iš arti", lights override */
  document.addEventListener('keydown', e => {
    if (e.key !== 'Escape') return;
    const dlg = $('v');
    if (dlg && dlg.hasAttribute('open')) return;
    if (tl.nearOn) setNear(false);
    else if (clearLight()) loop.wake();
  });

  /* the renderer sleeps while the lightbox is open */
  document.addEventListener('lb', e => loop.block('dialog', !!(e.detail && e.detail.open)));

  showHint();
  syncControls();
}
