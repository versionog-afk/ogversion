// contact sheet: node sheet.js <out.png> <cols> <scale> <file...>
const { chromium } = require('playwright'); const fs = require('fs'), path = require('path');
(async () => {
  const [out, cols, scale, ...files] = process.argv.slice(2);
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 800, height: 600 } });
  await p.setContent('<body style="margin:0;background:#333;display:grid;gap:6px;grid-template-columns:repeat(' + cols + ',max-content);font:600 13px sans-serif">' +
    files.map(f => '<div style="position:relative"><img style="display:block;zoom:' + scale + '" src="data:image/png;base64,' + fs.readFileSync(f).toString('base64') + '"><span style="position:absolute;left:4px;top:4px;color:#0f0;background:#000c;padding:1px 6px">' + path.basename(f, '.png') + '</span></div>').join('') + '</body>');
  const el = await p.$('body'); const bb = await el.boundingBox();
  await p.setViewportSize({ width: Math.ceil(bb.width), height: Math.ceil(bb.height) });
  await p.screenshot({ path: out, fullPage: true });
  await b.close();
})();
