// Screenshots of the main screens, light and dark, phone size. Usage: node shots.js <port> <outdir> <itemId>
const { chromium } = require('playwright');
(async () => {
  const [port, out, item] = process.argv.slice(2);
  const base = `http://127.0.0.1:${port}/`;
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', headless: false, args: ['--headless=new'] });
  const errors = [];
  for (const scheme of ['light', 'dark']) {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, colorScheme: scheme });
    const page = await ctx.newPage();
    page.on('pageerror', e => errors.push(scheme + ': ' + e.message));
    for (const [name, hash] of [['home', '#/home'], ['library', '#/lib'], ['lesson', `#/item/${item}`], ['search', '#/search'], ['tasks', '#/tasks'], ['settings', '#/settings'], ['folder', '#/lib/f/1']]) {
      await page.goto(base + hash);
      await page.waitForTimeout(1300);
      await page.screenshot({ path: `${out}/${scheme}-${name}.png` });
    }
    await page.goto(base + '#/lib'); await page.waitForTimeout(800);
    await page.click('.tabbar .tadd'); await page.waitForTimeout(700);
    await page.screenshot({ path: `${out}/${scheme}-add.png` });
    await ctx.close();
  }
  await browser.close();
  console.log(errors.length ? 'ERRORS:\n' + errors.join('\n') : 'no page errors');
})();
