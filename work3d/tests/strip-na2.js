// The whole story as a strip of frames, reached by real scrolling.
//   node strip-na2.js <viewport> [step in screens, default 0.1] [--color white] [--fill kind] [from] [to]
//   → tmp/strip-<viewport>[-white][-fill<kind>].png (a contact sheet) and one line of state per frame
const { chromium, open, ready, arrived, settle, anchors, scrollToS, state, fill } = require('./lib-na2.js');
(async () => {
  const args = process.argv.slice(2);
  const opt = n => { const i = args.indexOf('--' + n); return i < 0 ? null : args.splice(i, 2)[1]; };
  const color = opt('color'), kind = opt('fill');
  const [view = '390x664', stepArg = '0.1', fromArg = '0', toArg] = args;
  const b = await chromium.launch();
  const { p, log } = await open(b, view);
  await ready(p); await arrived(p); await settle(p);
  if (color) { await p.evaluate(c => { window.__m.color = c; }, color); await settle(p); }
  if (kind) { await fill(p, kind); await p.waitForTimeout(600); }
  const A = await anchors(p);
  const end = toArg ? +toArg : A.stBottom + 0.3, step = +stepArg, files = [];
  for (let s = +fromArg; s <= end + 1e-6; s += step) {
    await scrollToS(p, s);
    const f = __dirname + '/tmp/strip-' + s.toFixed(2) + '.png';
    await p.screenshot({ path: f });
    files.push(f);
    const st = await state(p);
    console.log(s.toFixed(2), 'd', st.d, 'az', st.az, 'L', st.L, 'line', st.line, 'rail', st.rail, 'sw', st.sw ? 1 : 0, st.cls);
  }
  if (log.errors.length || log.bad.length) console.log('problems', JSON.stringify(log.errors.concat(log.bad)));
  await b.close();
  const out = __dirname + '/tmp/strip-' + view + (color === 'white' ? '-white' : '') + (kind ? '-fill' + kind : '') + '.png';
  const V = view.split('x').map(Number), scale = V[0] > 1000 ? 0.16 : V[0] > 700 ? 0.25 : 0.4, cols = V[0] > 700 ? 8 : 12;
  require('child_process').execFileSync('node', [__dirname + '/sheet.js', out, String(cols), String(scale), ...files], { stdio: 'inherit' });
  for (const f of files) require('fs').unlinkSync(f);
})().catch(e => { console.error(e); process.exit(1); });
