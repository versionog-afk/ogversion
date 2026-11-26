// Full-page screenshots of the plain (static) page.
//   node static-na2.js <w> <h> [fill kind: 1|2|5|long] [name]   → shots-na2/<name>-<w>x<h>[-fill<kind>].png and …-top.png
const { chromium, open, fill } = require('./lib-na2.js');
(async () => {
  const [w, h, kind = '', name = 'static'] = process.argv.slice(2);
  const b = await chromium.launch();
  const { p, log } = await open(b, { width: +w, height: +h, coarse: +w < 900 }, '', '0');
  if (kind) await fill(p, kind);
  // walk down the page once so that lazy images load
  await p.evaluate(async () => { for (let y = 0; y < document.documentElement.scrollHeight; y += innerHeight / 2) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 80)); } window.scrollTo(0, 0); });
  await p.waitForTimeout(800);
  console.log(await p.evaluate(() => JSON.stringify({
    gl: document.documentElement.classList.contains('gl'), scrollW: document.documentElement.scrollWidth, innerW: innerWidth, pageH: document.documentElement.scrollHeight,
    h1: Math.round(document.querySelector('h1 .n').getBoundingClientRect().width), info: getComputedStyle(document.getElementById('info')).display,
    swatches: getComputedStyle(document.querySelector('.sw')).display, tiles: document.querySelectorAll('.g .z').length,
    visibleText: [...document.querySelectorAll('body *')].filter(e => e.children.length === 0 && e.textContent.trim() && e.getClientRects().length && !e.closest('.sr,script,style,dialog')).map(e => e.textContent.trim())
  })));
  if (log.errors.length || log.bad.length || log.external.length) console.log('problems', JSON.stringify(log.errors.concat(log.bad, log.external)));
  const file = __dirname + '/shots-na2/' + name + '-' + w + 'x' + h + (kind ? '-fill' + kind : '');
  await p.screenshot({ path: file + '.png', fullPage: true });
  await p.screenshot({ path: file + '-top.png' });
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
