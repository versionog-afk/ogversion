/* Rack: the red rail and, later, the nine photo panels that hang on it.

   THIS STAGE builds the rail only. The seam the rest of the code already
   uses is the whole interface of the finished module:

     rack.build(scene, ctx)      once, after the model is measured.
                                 ctx = { world, stage, loop }
     rack.layout()               after every resize (frame rects and poses changed)
     rack.update(dt, state)      every frame, before rendering.
                                 state = { uScroll, rail, railFrom, railTo, s, inPhotos, dark }
                                   uScroll   −1…8 from the scroll position (4.2)
                                   rail      0…1 how much of the rail is drawn
                                   railFrom, railTo   world x of the screen's left and right
                                             edge at the figure: the stretch the draw covers
                                   inPhotos  applied scroll is past stovas@0.90
     rack.u                      −1…8, the item the camera looks at (−1 = the figure).
                                 The timeline reads it for ITEM(u) every frame.
     rack.busy                   true while a flick, spring or swing is unsettled
     rack.X(u)                   world x of item u (−1 → the figure, 0…8 → panels)
     rack.onDragStart()          a horizontal gesture began past stovas@0.90
     rack.onDrag(dxPx, pxPerPanel)          pxPerPanel = 0.66·f/d right now, so Δu = −dxPx / pxPerPanel
     rack.onDragEnd(vPxPerSec, pxPerPanel)
     rack.onTap(event)           tap inside the rack beat → panel raycast, returns true if handled
     rack.step(delta)            the bar's ‹ › buttons
     rack.current                index 0…8 of the photo the bar shows: max(0, round(u))

   Still to come here (next stage): panels on clips (one InstancedMesh),
   placeholders in the average colours (AVG in config.js), reflections, lazy
   textures, flick physics (a Flick1D from spin.js with friction 2.2, spring
   110 / 0.8, detents on integers), per-panel swing springs, the tap raycast,
   scroll reclaiming uUser, and the bar's logic. Until then u = uScroll. */
import { Mesh, BoxGeometry, MeshBasicMaterial } from 'three';
import { CFG, clamp } from './config.js';

export const rack = {
  u: -1,
  busy: false,
  rail: null,
  x0: 0, x1: 0,
  current: 0,

  X(u) {
    const P = CFG.PANEL, cx = this.cx || 0;
    if (u <= -1) return cx;
    if (u < 0) return cx + (u + 1) * P.first;            // linear from the figure to the first panel
    return cx + P.first + P.step * Math.min(u, P.count - 1);
  },

  build(scene, ctx) {
    const R = CFG.RAIL, P = CFG.PANEL, w = ctx.world;
    this.cx = w.axis.x;
    this.z = w.axis.z;
    this.x0 = this.cx + R.x0;
    this.x1 = this.X(P.count - 1) + R.x1pad;
    /* a unit box that grows from its left end, so scale.x draws the rail left to right */
    const geo = new BoxGeometry(1, R.size, R.size).translate(0.5, 0, 0);
    const rail = this.rail = new Mesh(geo, new MeshBasicMaterial({ color: R.color, toneMapped: false }));
    rail.position.set(this.x0, w.Yr, this.z);
    rail.scale.x = 0.0001;
    rail.visible = false;
    scene.add(rail);
  },

  layout() {},

  update(dt, state) {
    this.u = clamp(state.uScroll, -1, CFG.PANEL.count - 1);
    this.current = Math.max(0, Math.round(this.u));
    /* the rail draws across what the camera sees at the figure; the rest of
       its length (off screen to the right) is there once the draw is done */
    const p = state.rail;
    const from = Math.max(this.x0, state.railFrom);
    const end = p >= 1 ? this.x1 : from + (state.railTo - from) * p;
    this.rail.visible = p > 0.001;
    this.rail.scale.x = Math.max(0.0001, end - this.x0);
  },

  onDragStart() {},
  onDrag() {},
  onDragEnd() {},
  onTap() { return false; },
  step() {}
};
