// Storyboard screenshots of the NA2 page.
//   node shots-na2.js [viewport ...] [--only stop,stop] [--color white] [--real] [--fill 1|2|5|long]
//   → shots-na2/<viewport>-<stop>[-white][-real][-fill<kind>].png, and a line of state per shot
// Default: every stop through ?s= (the timeline pinned there). --real scrolls the page instead.
// --fill puts dummy values into the info block and shoots the plate (always with real scrolling).
const { chromium, VIEWS, open, ready, arrived, settle, anchors, scrollToS, state, fill } = require('./lib-na2.js');
const OUT = __dirname + '/shots-na2/';
const DEFAULT_VIEWS = ['390x664', '844x390', '1440x900'];

// stop name → scroll position in screens, from the anchors the page reports
const STOPS = [
  ['push', A => 0.45],                                   // half way into the chest: the sign is being eclipsed
  ['chest', A => (A.chestAt + A.walkFrom) / 2],          // the chest lettering
  ['side', A => A.side],                                 // half way round
  ['back', A => (A.back + A.mapFrom) / 2],               // the back with the map
  ['dark-half', A => (A.line0 + A.line1) / 2],           // lights out, the red line half drawn
  ['dark', A => A.line1 + 0.15],                         // only the map, the line complete
  ['lights', A => (A.infoLight + A.infoBack) / 2],       // lights back on, pulling away from the map
  ['side2', A => A.stSide],                              // the other side
  ['item', A => A.stItem + 0.02],                        // the figure as an item, before the rail
  ['rail', A => A.stRail1 + 0.1],                        // … under the rail
  ['photos', A => A.stPhotos + 0.45],                    // along the rack
  ['end', A => A.stEnd - 0.02]                           // the end of the rail, the grid about to enter
];
// with dummy values in the info block: the plate entering, in the middle of the viewport, leaving
const FILL_STOPS = [
  ['info-in', (A, I) => I.top - 0.55],
  ['info-mid', (A, I) => Math.max(I.top - 0.9, I.mid - 0.5)],
  ['info-end', (A, I) => I.bottom - 1],
  ['info-out', (A, I) => I.bottom - 0.45]
];

(async () => {
  const args = process.argv.slice(2);
  const opt = name => { const i = args.indexOf('--' + name); return i < 0 ? null : args[i + 1]; };
  const flag = name => args.includes('--' + name);
  const only = opt('only') ? opt('only').split(',') : null;
  const color = opt('color'), kind = opt('fill'), real = flag('real') || !!kind;
  const skip = new Set(['only', 'color', 'fill'].map(n => args.indexOf('--' + n) + 1).filter(i => i > 0));
  const views = args.filter((a, i) => !a.startsWith('--') && !skip.has(i));
  const suffix = (color === 'white' ? '-white' : '') + (flag('real') ? '-real' : '') + (kind ? '-fill' + kind : '');
  const want = name => !only || only.includes(name);

  const b = await chromium.launch();
  const report = {};
  for (const name of views.length ? views : DEFAULT_VIEWS) {
    const dress = async p => { if (color) { await p.evaluate(c => { window.__m.color = c; }, color); await settle(p); } };
    const shot = async (p, log, label) => {
      await p.screenshot({ path: OUT + name + '-' + label + suffix + '.png' });
      report[name + '-' + label + suffix] = Object.assign(await state(p), log.errors.length || log.bad.length ? { errors: log.errors.concat(log.bad) } : {});
    };

    // the hero after the real arrival, then the figure turned by the hidden range input
    let { ctx, p, log } = await open(b, name);
    await ready(p); await arrived(p); await settle(p);
    const A = await anchors(p);
    report[name + '-anchors'] = Object.assign({ pageScreens: +(await p.evaluate(() => document.documentElement.scrollHeight / window.__m.dbg.stage.S)).toFixed(2) }, A);
    await dress(p);
    if (!kind) {
      if (want('hero')) await shot(p, log, 'hero');
      for (const [label, presses] of [['yaw90', 6], ['yaw180', 12]]) {
        if (!want(label)) continue;
        await p.focus('#rot');
        await p.keyboard.press('Home');
        for (let i = 0; i < presses; i++) await p.keyboard.press('ArrowRight');
        await p.waitForFunction(deg => Math.abs(window.__m.yaw - deg) < 0.5 && !window.__m.dbg.spin.core.busy, presses * 15, { timeout: 30000 });
        await p.evaluate(() => document.activeElement.blur());
        await settle(p);
        await shot(p, log, label);
      }
    }

    if (kind) {
      // the info plate with dummy values, reached by real scrolling
      await fill(p, kind);
      await p.waitForTimeout(600);                        // the page re-measures after the block changed height
      const I = await p.evaluate(() => { const r = document.getElementById('info').getBoundingClientRect(), S = window.__m.dbg.stage.S; return { top: (r.top + scrollY) / S, bottom: (r.bottom + scrollY) / S, mid: (r.top + r.bottom) / 2 / S + scrollY / S, h: r.height / S }; });
      const A2 = await anchors(p);
      report[name + '-info' + suffix] = Object.assign({ plateScreens: +I.h.toFixed(2) }, A2);
      for (const [label, f] of FILL_STOPS) {
        if (!want(label)) continue;
        await scrollToS(p, f(A2, I));
        await shot(p, log, label);
      }
      await ctx.close();
      continue;
    }

    for (const [label, f] of STOPS) {
      if (!want(label)) continue;
      if (real) await scrollToS(p, f(A));
      else {
        await ctx.close();
        ({ ctx, p, log } = await open(b, name, '&s=' + f(A).toFixed(4)));
        await ready(p); await settle(p);
        await dress(p);
      }
      await shot(p, log, label);
    }
    await ctx.close();
  }
  await b.close();
  for (const k in report) console.log(k, JSON.stringify(report[k]));
})().catch(e => { console.error(e); process.exit(1); });
