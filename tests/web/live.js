/* Opens the published web version in Chromium and uses it like a person: add a file, cut a part, transcribe
   (Groq is imitated), reload, settings, wide screens. Screenshots go to the folder given. */
const { chromium } = require('playwright');
const P = process.argv[2], URL0 = process.argv[3] || 'https://agaatworld.github.io/Maqatei/open/';
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
  // pretend to be Groq
  await ctx.route('https://api.groq.com/**', r => r.fulfill({ status: 200, contentType: 'application/json', headers: { 'access-control-allow-origin': '*' },
    body: JSON.stringify(r.request().method() === 'GET' ? { data: [] } : { text: 'بسم الله الرحمن الرحيم', segments: [{ start: 0.5, end: 6, text: 'بسم الله الرحمن الرحيم' }], words: [] }) }));
  const pg = await ctx.newPage(); const errs = [];
  pg.on('pageerror', e => errs.push('PAGEERR ' + e.message)); pg.on('response', r => { if (r.status() >= 400) errs.push(r.status() + ' ' + r.url()); }); pg.on('console', m => { if (m.type() === 'error') errs.push('CONSOLE ' + m.text()); });
  const t0 = Date.now();
  await pg.goto(URL0); await pg.waitForSelector('#boot', { state: 'detached', timeout: 120000 });
  console.log('booted in', (Date.now() - t0) / 1000, 's');
  await pg.waitForTimeout(1500); await pg.screenshot({ path: P + '/w1-lib.png' });
  // set a key so transcription is allowed
  console.log(await pg.evaluate(async () => (await fetch('api/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ groq_key: 'gsk_test' }) })).status));
  // add a file
  await pg.click('[data-act="add"] >> nth=0'); await pg.waitForTimeout(600); await pg.click('#sheet [data-m="files"]'); await pg.waitForTimeout(200);
  await pg.screenshot({ path: P + '/w2-add.png' });
  await pg.setInputFiles('#fileIn', P + '/test40.mp3'); await pg.click('#addGo');
  await pg.waitForURL(/#\/item\/\d+/, { timeout: 30000 }); await pg.waitForTimeout(2000);
  await pg.screenshot({ path: P + '/w3-item.png' });
  const id = +pg.url().match(/item\/(\d+)/)[1];
  const it = await pg.evaluate(async id => (await fetch('api/items/' + id)).json(), id);
  console.log('item', [it.duration, it.media, it.file]);
  // media range
  console.log('range', await pg.evaluate(async f => { const r = await fetch('media/' + f.split('/').map(encodeURIComponent).join('/'), { headers: { Range: 'bytes=0-99' } }); return [r.status, r.headers.get('content-range'), (await r.arrayBuffer()).byteLength]; }, it.file));
  // cut a part and transcribe
  const mk = await pg.evaluate(async id => (await fetch(`api/items/${id}/bookmarks`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: 'part', start: 5, end: 15.5 }) })).json(), id);
  console.log('mark', JSON.stringify(mk).slice(0, 200));
  const bid = mk.id;
  console.log('clip', await pg.evaluate(async bid => (await fetch('api/bookmarks/action', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ids: [bid], action: 'mp3' }) })).text(), bid));
  console.log('tr', await pg.evaluate(async id => (await fetch(`api/items/${id}/action`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'transcribe' }) })).text(), id));
  for (let i = 0; i < 90; i++) {
    const js = await pg.evaluate(async () => (await fetch('api/jobs')).json());
    const list = js.jobs || js;
    if (i % 5 === 0) console.log(list.map(j => `${j.id}:${j.kind}:${j.status}:${j.message || ''}`).join(' | '));
    if (list.length && list.every(j => ['done', 'error'].includes(j.status))) { console.log('final', list.map(j => `${j.kind}:${j.status}:${j.result || j.message}`).join(' | ')); break; }
    await pg.waitForTimeout(2000);
  }
  const clipB64 = await pg.evaluate(async () => { const r = await fetch('media/' + ['test40', 'المقاطع', 'part (00-05 – 00-15).mp3'].map(encodeURIComponent).join('/')); const u = new Uint8Array(await r.arrayBuffer()); let s = ''; for (const x of u) s += String.fromCharCode(x); return btoa(s); });
  require('fs').writeFileSync(P + '/clip-web.mp3', Buffer.from(clipB64, 'base64'));
  console.log('tx', JSON.stringify((await pg.evaluate(async id => (await fetch('api/items/' + id)).json(), id)).transcripts).slice(0, 300));
  await pg.goto(URL0 + '#/item/' + id); await pg.waitForTimeout(3000);
  await pg.screenshot({ path: P + '/w4-done.png', fullPage: false });
  // reload: data must still be there
  await pg.reload(); await pg.waitForSelector('#boot', { state: 'detached', timeout: 120000 }); await pg.waitForTimeout(2000);
  // a real YouTube link through the free mirrors (they come and go, so this is reported, not required)
  try {
    await ctx.unroute('https://api.groq.com/**');
    const yt = await pg.evaluate(async () => (await fetch('api/links', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: 'https://www.youtube.com/watch?v=jNQXAC9IVRw', mode: 'audio' }) })).json());
    let last = '';
    for (let i = 0; i < 90; i++) {
      const js = await pg.evaluate(async () => (await fetch('api/jobs')).json());
      const mine = js.filter(j => j.item_id === yt.ids[0]); last = mine.map(j => `${j.kind}:${j.status}:${(j.message || '').slice(0, 60)}`).join(' | ');
      if (mine.length && mine.every(j => ['done', 'error'].includes(j.status)) && (mine.some(j => j.kind === 'fetch') || mine.some(j => j.status === 'error'))) break;
      await pg.waitForTimeout(3000);
    }
    const it = await pg.evaluate(async id => (await fetch('api/items/' + id)).json(), yt.ids[0]);
    console.log('YOUTUBE (mirrors):', last, '→', it.title, it.duration, it.file || '(no file)');
  } catch (e) { console.log('YOUTUBE (mirrors): failed', e.message); }
  console.log('after reload items', (await pg.evaluate(async () => (await fetch('api/state')).json())).items?.length);
  await pg.goto(URL0 + '#/settings'); await pg.waitForTimeout(2500); await pg.screenshot({ path: P + '/w5-settings.png', fullPage: true });
  for (const [w, h] of [[1366, 768], [1920, 1080]]) { await pg.setViewportSize({ width: w, height: h }); await pg.goto(URL0 + '#/item/' + id); await pg.waitForTimeout(2500); await pg.screenshot({ path: `${P}/w6-${w}.png` }); }
  console.log(errs.join('\n') || 'no errors');
  if (errs.some(e => e.startsWith('PAGEERR'))) process.exit(1);
  await b.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
