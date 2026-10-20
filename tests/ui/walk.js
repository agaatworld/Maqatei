// Clicks through every screen like a person would and reports any page error.
// Usage: node walk.js <port> <outdir>   (an engine with some lessons must be running)
const { chromium } = require('playwright');
(async () => {
  const [port, out] = process.argv.slice(2);
  const base = `http://127.0.0.1:${port}/`;
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', headless: false, args: ['--headless=new', '--autoplay-policy=no-user-gesture-required'] });
  const p = await b.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
  const errs = [], steps = [];
  p.on('pageerror', e => errs.push(`[${steps.at(-1)}] ${e.message}`));
  p.on('console', m => { if (m.type() === 'error' && !/favicon|404|net::/.test(m.text())) errs.push(`[${steps.at(-1)}] console: ${m.text()}`); });
  const step = async (name, fn) => { steps.push(name); try { await fn(); } catch (e) { errs.push(`[${name}] FAILED: ${e.message.split('\n')[0]}`); } await p.waitForTimeout(400); };
  const closeSheet = async () => { await p.evaluate(() => { const d = document.getElementById('sheet'); if (d.open) d.close(); }); };
  const hideToast = () => p.evaluate(() => { const t = document.getElementById('toast'); if (t) t.hidden = true; });

  await step('library', async () => { await p.goto(base + '#/lib'); await p.waitForTimeout(1500); await hideToast(); });
  await step('theme toggle', async () => { await p.click('#themeBtn'); await p.waitForTimeout(500); await p.click('#themeBtn'); });
  await step('list view', async () => { await p.click('[data-act=lib-view][data-v=list]'); await p.click('[data-act=lib-view][data-v=grid]'); });
  await step('next reminder', async () => { await p.click('.rmd'); });
  await step('my works', async () => { await p.click('a.works'); await p.waitForTimeout(800); await p.click('[data-act=wfold] >> nth=1'); });
  await step('add sheet', async () => { await p.click('.tabbar .tadd'); await p.waitForTimeout(500); await p.click('#sheet .segc button >> nth=1'); await closeSheet(); });
  await step('folder', async () => { await p.goto(base + '#/lib/f/1'); await p.waitForTimeout(800); await p.click('[data-act=folder-menu]'); await p.waitForTimeout(300); await closeSheet();
    for (const k of ['works', 'parts', 'ex', 'lessons']) { await p.goto(base + '#/lib/f/1/' + k); await p.waitForTimeout(500); } });
  await step('lesson', async () => { await p.goto(base + '#/item/1'); await p.waitForTimeout(1500); await hideToast(); });
  await step('play', async () => { await p.click('#dock [data-act=pp]'); await p.waitForTimeout(1500); });
  await step('speed / skip / fine', async () => { await p.click('[data-act=rate-next]'); await p.click('[data-act=skip-next]'); await p.click('[data-act=fine-toggle]'); await p.click('[data-act=fine][data-d="0.1"]'); });
  await step('new part with start/end', async () => { await p.click('#dock [data-act=mstart]'); await p.waitForTimeout(1600); await p.click('#dock [data-act=mend]'); await p.waitForTimeout(700);
    const open = await p.evaluate(() => document.getElementById('sheet').open); if (!open) throw new Error('the name window did not open');
    await p.screenshot({ path: out + '/walk-newpart.png' });
    await p.fill('#sheet input', 'مقطع من الاختبار'); await p.click('#sheet button[value=save]'); await p.waitForTimeout(800); });
  await step('part menu', async () => { await p.click('.mark [data-act=mark-more] >> nth=0'); await p.waitForTimeout(400); await p.screenshot({ path: out + '/walk-partmenu.png' }); await closeSheet(); });
  await step('edit times', async () => { await p.click('.mark [data-act=mark-more] >> nth=0'); await p.click('#sheet [data-act=mark-times]'); await p.waitForTimeout(500); await closeSheet(); });
  await step('lock (two steps)', async () => { await p.click('.mark [data-act=mark-more] >> nth=0'); await p.click('#sheet [data-act=mark-done]'); await p.waitForTimeout(300); await p.click('[data-act=mark-done-ok]'); await p.waitForTimeout(600);
    if (!await p.$('.mark.done')) throw new Error('not locked'); });
  await step('select mode', async () => { await p.click('[data-act=sel-mode]'); await p.click('.mark .sel >> nth=0'); await p.waitForTimeout(300); await p.click('[data-act=sel-mode]'); });
  for (const k of ['tr', 'notes', 'files', 'marks']) await step('tab ' + k, async () => { await p.click(`[data-act=itab][data-k=${k}]`); });
  await step('lesson menu + export', async () => { await p.click('[data-act=item-menu]'); await p.click('#sheet [data-act=export]'); await p.waitForTimeout(600); await p.screenshot({ path: out + '/walk-export.png' }); await closeSheet(); });
  await step('search', async () => { await p.goto(base + '#/search'); await p.waitForTimeout(600); await p.fill('#sq', 'جمله'); await p.press('#sq', 'Enter'); await p.waitForTimeout(1200); await p.screenshot({ path: out + '/walk-search.png' }); });
  await step('projects', async () => { await p.goto(base + '#/projects'); await p.waitForTimeout(800); const a = await p.$('a[href^="#/project/"]'); if (a) { await a.click(); await p.waitForTimeout(1000); await p.screenshot({ path: out + '/walk-project.png' }); } });
  await step('tasks', async () => { await p.goto(base + '#/tasks'); await p.waitForTimeout(800); await p.click('a[href="#/tasks/done"]'); await p.waitForTimeout(600); await p.click('[data-act=tasks-menu]'); await closeSheet(); });
  await step('settings', async () => { await p.goto(base + '#/settings'); await p.waitForTimeout(1200); await p.screenshot({ path: out + '/walk-settings.png' }); });
  await step('wifi switch', async () => { await p.click('label:has(#lanSw)'); await p.waitForTimeout(1200); await p.click('label:has(#lanSw)'); await p.waitForTimeout(800); });
  await step('guide', async () => { await p.goto(base + '#/help'); await p.waitForTimeout(1000); });
  await b.close();
  console.log(errs.length ? 'PROBLEMS:\n' + errs.join('\n') : `no problems in ${steps.length} steps`);
})();
