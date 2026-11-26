// full-page screenshots of the static page: node static-na2.js <w> <h> [name]
const { chromium } = require('playwright');
const PORT = process.env.PORT || 8361;
(async () => {
  const [w, h, name = 'static'] = process.argv.slice(2);
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: +w, height: +h }, deviceScaleFactor: 1 });
  const p = await ctx.newPage();
  p.on('pageerror', e => console.log('pageerror: ' + e.message));
  p.on('console', m => { if (m.type() === 'error') console.log('console error: ' + m.text()); });
  p.on('response', r => { if (r.status() >= 400) console.log('HTTP ' + r.status() + ' ' + r.url()); });
  await p.goto('http://127.0.0.1:' + PORT + '/merch?3d=0', { waitUntil: 'load' });
  await p.evaluate(async () => { for (let y = 0; y < document.documentElement.scrollHeight; y += innerHeight / 2) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 80)); } window.scrollTo(0, 0); });
  await p.waitForTimeout(800);
  console.log(await p.evaluate(() => JSON.stringify({ sw: document.documentElement.scrollWidth, iw: innerWidth, sh: document.documentElement.scrollHeight, h1: document.querySelector('h1').getBoundingClientRect().toJSON(), n: document.querySelector('h1 .n').getBoundingClientRect().width, f: document.querySelector('.hero__f').scrollWidth + '/' + document.querySelector('.hero__f').clientWidth })));
  await p.screenshot({ path: __dirname + '/shots-na2/' + name + '-' + w + 'x' + h + '.png', fullPage: true });
  await p.screenshot({ path: __dirname + '/shots-na2/' + name + '-' + w + 'x' + h + '-top.png' });
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
