/* Render loop, on demand.

   wake() asks for frames; the frame callback returns true while anything is
   still moving. When it returns false the loop stops completely: no rAF is
   scheduled until the next wake(). block(reason, on) stops it outright
   (tab hidden, dialog open, context lost, static page). */
import { CFG } from './config.js';

let raf = 0, last = 0, onFrame = null;
const blocks = new Set();

function frame(t) {
  raf = 0;
  loop.frames++;
  if (blocks.size || !onFrame) return;
  const dt = Math.min(CFG.MAX_DT, Math.max(1 / 240, (t - last) / 1000));
  last = t;
  if (onFrame(dt, t)) raf = requestAnimationFrame(frame);
}

export const loop = {
  frames: 0,                         // rAF callbacks so far (tests read it)
  start(fn) { onFrame = fn; },
  wake() {
    if (raf || blocks.size || !onFrame) return;
    last = performance.now() - 16;
    raf = requestAnimationFrame(frame);
  },
  block(reason, on) {
    if (on) { blocks.add(reason); if (raf) { cancelAnimationFrame(raf); raf = 0; } }
    else if (blocks.delete(reason)) loop.wake();
  },
  get running() { return raf !== 0; }
};
