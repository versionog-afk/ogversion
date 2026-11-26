/* Controls: the hidden range input that turns the figure from the keyboard,
   the two colour swatches, the live region, and the bridge to the page's
   lightbox. Nothing here is visible text. */
import { CFG } from './config.js';
import { tl } from './timeline.js';
import { spin, turnTo, yaw } from './spin.js';
import { shirt, chooseShirt } from './scene.js';
import { loop } from './loop.js';

const $ = id => document.getElementById(id);
const html = document.documentElement;
const mod360 = a => ((a % 360) + 360) % 360;

export const ui = {
  group: null, rot: null, live: null,
  swatches: null, black: null, white: null,
  lastDetent: 0
};

export function say(text) { const el = ui.live || $('live'); if (el) el.textContent = text; }

function valueText(deg) {
  const a = mod360(Math.round(deg));
  if (a === 0) return 'Priekis';
  if (a === 180) return 'Nugara';
  if (a === 90 || a === 270) return 'Šonas';
  return a + '°';
}

/* Mirrors the figure's angle into the range input. */
export function syncRange() {
  const a = Math.min(345, Math.round(mod360(yaw()) / 15) * 15 % 360);
  if (document.activeElement !== ui.rot) ui.rot.value = String(a);
  ui.rot.setAttribute('aria-valuetext', valueText(+ui.rot.value));
}

/* The colour of the tee: 'black' or 'white'. Lasts for the page view only. */
export function setColor(name) {
  if (!chooseShirt(name)) return;
  syncSwatches();
  loop.wake();
}
function syncSwatches() {
  ui.black.setAttribute('aria-pressed', shirt.name === 'black' ? 'true' : 'false');
  ui.white.setAttribute('aria-pressed', shirt.name === 'white' ? 'true' : 'false');
}

export function initControls() {
  ui.group = $('ctl'); ui.rot = $('rot'); ui.live = $('live');
  ui.swatches = document.querySelector('.sw'); ui.black = $('cb'); ui.white = $('cw');

  /* keyboard rotation: arrows, Home and End on a real range input */
  ui.rot.addEventListener('input', () => {
    turnTo(+ui.rot.value, CFG.SPIN.zetaRange);
    ui.rot.setAttribute('aria-valuetext', valueText(+ui.rot.value));
    spin.onInput();
  });
  /* the input is 1 px large, so only a keyboard (or a screen reader) can focus it:
     show where the focus is with a ring on the figure */
  ui.rot.addEventListener('focus', () => html.classList.add('kf'));
  ui.rot.addEventListener('blur', () => { html.classList.remove('kf'); syncRange(); });

  /* colour: a click, a tap, Enter or Space on a swatch */
  ui.black.addEventListener('click', () => setColor('black'));
  ui.white.addEventListener('click', () => setColor('white'));

  /* timeline → controls: whatever is switched off is inert and gives up the focus */
  const live = (el, on) => { el.inert = !on; if (!on && el.contains(document.activeElement)) document.activeElement.blur(); };
  tl.onUi = off => live(ui.group, !off);
  tl.onSwatches = on => live(ui.swatches, on);
  live(ui.group, !tl.uiOff);
  live(ui.swatches, tl.swOn);

  /* figure → the range input and the live region */
  spin.onSettle = d => {
    syncRange();
    if (d !== null && d !== ui.lastDetent) { ui.lastDetent = d; say(d === 0 ? 'Priekis.' : 'Nugara.'); }
  };

  /* the renderer sleeps while the lightbox is open */
  document.addEventListener('lb', e => loop.block('dialog', !!(e.detail && e.detail.open)));

  syncRange();
  syncSwatches();
}
