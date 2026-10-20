/* Maqati for iPhone: starts the real Maqati engine (Python, via Pyodide) inside this page, then the normal app.
   The service worker (sw.js) sends every api/…, media/… and export request of the app here, and this page answers
   from the engine. Media work (cutting, preparing speech) is done by ffmpeg.wasm; transcription calls Groq directly.
   Everything is kept in the browser's storage on this device (IndexedDB). */
(() => {
  'use strict';
  window.MAQATI_WEB = true;
  const ROOT = '/maqati', LIB = ROOT + '/lib';
  const say = (ar, en) => { const el = document.getElementById('bootMsg'); if (el) el.textContent = document.documentElement.lang === 'en' ? en : ar; };
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  let py, eng, FS, ff = null, ffIn = {};

  /* ---------- saving to the browser's storage ---------- */
  let saveT = null, saving = false, again = false;
  function save(now) {
    clearTimeout(saveT);
    saveT = setTimeout(async () => {
      if (saving) { again = true; return; }
      saving = true;
      await new Promise(res => FS.syncfs(false, e => { if (e) console.warn('save', e); res(); }));
      saving = false;
      if (again) { again = false; save(); }
    }, now ? 0 : 1200);
  }
  document.addEventListener('visibilitychange', () => { if (document.hidden && FS) save(true); });

  /* ---------- the engine ---------- */
  async function start() {
    say('جارٍ تشغيل مقاطع…', 'Starting Maqati…');
    py = await loadPyodide({ indexURL: './py/' });
    await py.loadPackage('sqlite3');
    FS = py.FS;
    FS.mkdirTree(ROOT);
    FS.mount(py.FS.filesystems.IDBFS, {}, ROOT);
    await new Promise(res => FS.syncfs(true, e => { if (e) console.warn('load', e); res(); }));
    say('جارٍ تجهيز المحرك…', 'Preparing the engine…');
    const zip = await (await fetch('./engine.zip?v=' + (window.MQ_V || ''))).arrayBuffer();
    py.unpackArchive(zip, 'zip', { extractDir: '/engine' });
    py.runPython(`
import os, sys
os.environ.update(MAQATI_DATA="${ROOT}/data", MAQATI_LIBRARY="${LIB}", MAQATI_WEB="1", MAQATI_FFMPEG="ffmpeg")
sys.path.insert(0, "/engine")
from app import webapi
`);
    eng = py.pyimport('app.webapi');
    if (navigator.storage && navigator.storage.persist) navigator.storage.persist().catch(() => {});
  }

  function call(method, url, body, dur, kind) {
    const r = eng.dispatch(method, url, body || null, dur ?? null, kind ?? null);
    const [status, ctype, data, name] = r.toJs();
    r.destroy();
    return { status, ctype, data: data instanceof Uint8Array ? data : new TextEncoder().encode(String(data)), name };
  }

  /* the engine sometimes needs ffmpeg or the internet even to answer (e.g. the transcription test) */
  async function answer(method, url, body, dur, kind) {
    for (let i = 0; i < 40; i++) {
      const r = call(method, url, body, dur, kind);
      if (r.status !== 0) return r;
      await need(JSON.parse(new TextDecoder().decode(r.data)));
    }
    return { status: 500, ctype: 'application/json', data: new TextEncoder().encode('{"detail":"busy"}') };
  }

  /* length and kind of a file the user is adding, measured by the browser (no ffmpeg needed) */
  function measure(bytes, name) {
    return new Promise(res => {
      const url = URL.createObjectURL(new Blob([bytes]));
      const video = /\.(mp4|mov|m4v|webm|mkv|3gp)$/i.test(name);
      const el = document.createElement(video ? 'video' : 'audio');
      let done = false;
      const fin = (d, k) => { if (done) return; done = true; URL.revokeObjectURL(url); el.removeAttribute('src'); res([isFinite(d) ? d : 0, k]); };
      el.preload = 'metadata'; el.muted = true;
      el.onloadedmetadata = () => fin(el.duration, video && el.videoWidth > 0 ? 'video' : 'audio');
      el.onerror = () => fin(0, video ? 'video' : 'audio');
      setTimeout(() => fin(el.duration || 0, video ? 'video' : 'audio'), 15000);
      el.src = url;
    });
  }

  /* a media file, in parts (players ask for byte ranges) */
  function media(rel, range, dl) {
    const path = LIB + '/' + rel;
    let st;
    try { st = FS.stat(path); } catch (e) { return { status: 404, ctype: 'text/plain', data: new Uint8Array() }; }
    if (!FS.isFile(st.mode) || rel.split('/').includes('..')) return { status: 404, ctype: 'text/plain', data: new Uint8Array() };
    const size = st.size, ctype = MIME[(rel.match(/\.\w+$/) || [''])[0].toLowerCase()] || 'application/octet-stream';
    let a = 0, b = size - 1, status = 200;
    const m = /bytes=(\d*)-(\d*)/.exec(range || '');
    if (m) {
      if (m[1] === '') { a = Math.max(0, size - +m[2]); } else { a = +m[1]; if (m[2] !== '') b = Math.min(+m[2], size - 1); else b = Math.min(size - 1, a + (8 << 20) - 1); }
      status = 206;
    }
    if (a >= size && size) return { status: 416, ctype, data: new Uint8Array(), size };
    const buf = new Uint8Array(Math.max(0, b - a + 1)), s = FS.open(path, 'r');
    try { FS.read(s, buf, 0, buf.length, a); } finally { FS.close(s); }
    return { status, ctype, data: buf, size, a, b, name: dl ? rel.split('/').pop() : null };
  }
  const MIME = { '.mp3': 'audio/mpeg', '.m4a': 'audio/mp4', '.aac': 'audio/aac', '.wav': 'audio/wav', '.ogg': 'audio/ogg', '.opus': 'audio/ogg', '.flac': 'audio/flac',
    '.mp4': 'video/mp4', '.m4v': 'video/mp4', '.mov': 'video/quicktime', '.webm': 'video/webm', '.zip': 'application/zip', '.txt': 'text/plain; charset=utf-8',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.pdf': 'application/pdf', '.html': 'text/html; charset=utf-8',
    '.srt': 'text/plain; charset=utf-8', '.vtt': 'text/vtt; charset=utf-8', '.json': 'application/json', '.jpg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp' };

  /* ---------- requests from the service worker ---------- */
  navigator.serviceWorker.addEventListener('message', async e => {
    const q = e.data, port = e.ports[0];
    if (!q || q.t !== 'req' || !port) return;
    let r;
    try {
      await ready;
      const u = new URL(q.url, location.href);
      const rel = q.path;                                   // e.g. "api/items/3" or "media/Lesson/a.mp3"
      if (rel.startsWith('media/')) {
        r = media(decodeURIComponent(rel.slice(6)), q.range, u.searchParams.get('dl') === '1');
      } else {
        let dur = null, kind = null;
        if (rel === 'api/upload' && q.body) [dur, kind] = await measure(q.body, u.searchParams.get('name') || '');
        r = await answer(q.method, '/' + rel + u.search, q.body ? new Uint8Array(q.body) : null, dur, kind);
        if (q.method !== 'GET') { save(); wake(); }
      }
    } catch (err) {
      console.error(err);
      r = { status: 500, ctype: 'application/json', data: new TextEncoder().encode(JSON.stringify({ detail: String(err && err.message || err) })) };
    }
    port.postMessage(r, [r.data.buffer]);
  });

  /* ---------- tasks (cut, convert, transcribe, project export) ---------- */
  let wakeUp = null;
  const wake = () => { if (wakeUp) { wakeUp(); wakeUp = null; } };
  async function runner() {
    for (;;) {
      let jid = null;
      try { jid = eng.next_job(); } catch (e) { console.error(e); }
      if (jid == null) { await Promise.race([sleep(3000), new Promise(r => wakeUp = r)]); continue; }
      let r;
      try { r = JSON.parse(eng.step(jid)); } catch (e) { console.error(e); await sleep(2000); continue; }
      if (r.need) { await need(r, jid); continue; }
      save();
    }
  }

  async function need(n, jid) {
    let res;
    if (n.need === 'ffmpeg') res = await runFF(n.cmd, jid);
    else if (n.need === 'http') res = await runHTTP(n, jid);
    else res = [1, 'unknown'];
    eng.provide(n.key, JSON.stringify(res));
  }

  /* ffmpeg.wasm: the engine's files are copied in, the results copied back */
  async function loadFF() {
    if (ff) return ff;
    const { FFmpeg } = await import('./ff/ffmpeg/index.js');
    ff = new FFmpeg();
    await ff.load({ coreURL: new URL('./ff/core/ffmpeg-core.js', location.href).href, wasmURL: new URL('./ff/core/ffmpeg-core.wasm', location.href).href });
    ffIn = {};
    return ff;
  }
  let ffLog = [];
  async function runFF(cmd, jid) {
    const f = await loadFF();
    const args = cmd.slice(1), outs = [], used = new Set();
    let k = 0;
    for (let i = 0; i < args.length; i++) {
      const a = args[i];
      if (!a.startsWith(ROOT + '/')) continue;
      const ext = (a.match(/\.\w{1,5}$/) || [''])[0];
      let st = null;
      try { st = FS.stat(a); } catch (e) {}
      if (args[i - 1] === '-i' && st) {
        const tag = a + ':' + st.size + ':' + (+st.mtime);
        let name = ffIn[tag];
        if (!name) { name = 'in' + (Date.now() % 1e9) + '_' + (k++) + ext; await f.writeFile(name, FS.readFile(a)); ffIn[tag] = name; }
        used.add(name); args[i] = name;
      } else {
        const name = 'out' + (k++) + ext; outs.push([name, a]); args[i] = name;
      }
    }
    for (const [tag, name] of Object.entries(ffIn)) if (!used.has(name)) { try { await f.deleteFile(name); } catch (e) {} delete ffIn[tag]; }
    ffLog = [];
    const onLog = ({ message }) => { ffLog.push(message); if (ffLog.length > 4000) ffLog.splice(0, 2000); };
    f.on('log', onLog);
    let code = 1, stop = false;
    const watch = jid != null && setInterval(() => { try { if (eng.status(jid) !== 'running') { stop = true; f.terminate(); } } catch (e) {} }, 1500);
    try { code = await f.exec(args); } catch (e) { ffLog.push(String(e)); code = 1; }
    finally { clearInterval(watch); f.off('log', onLog); }
    if (stop) { ff = null; ffIn = {}; return [1, 'stopped']; }
    for (const [name, real] of outs) {
      try { const data = await f.readFile(name); FS.mkdirTree(real.slice(0, real.lastIndexOf('/'))); FS.writeFile(real, data); await f.deleteFile(name); } catch (e) {}
    }
    return [code, ffLog.join('\n')];
  }

  /* the transcription service (Groq allows calls straight from a web page) */
  async function runHTTP(n, jid) {
    let st = 0, text = '', hd = {};
    try {
      const o = { method: n.method, headers: n.headers };
      if (n.method === 'POST') {
        const fd = new FormData();
        for (const [key, v] of n.data) fd.append(key, v);
        if (n.file) fd.append('file', new Blob([FS.readFile(n.file)], { type: n.mime }), n.name);
        o.body = fd;
      }
      const r = await fetch(n.url, o);
      st = r.status; text = await r.text(); r.headers.forEach((v, key) => hd[key] = v);
    } catch (e) { st = 0; text = String(e && e.message || e); }
    if (st === 429 || st === 0 || st >= 500) {           // wait before the engine asks again (as the normal app does)
      let wait = st === 429 ? Math.min(900, Math.max(3, +hd['retry-after'] || 30)) : 8;
      while (wait-- > 0) { if (jid != null && eng.status(jid) !== 'running') break; await sleep(1000); }
    }
    return [st, text, hd];
  }

  const ready = (async () => {
    if (!('serviceWorker' in navigator)) throw new Error('no service worker');
    const reg = await navigator.serviceWorker.register('./sw.js');
    if (!navigator.serviceWorker.controller) {          // the first visit: the worker takes over after one reload
      await new Promise(r => { if (reg.active) r(); else navigator.serviceWorker.addEventListener('controllerchange', r, { once: true }); setTimeout(r, 4000); });
      if (!navigator.serviceWorker.controller) { location.reload(); await new Promise(() => {}); }
    }
    await start();
  })();

  ready.then(() => {
    navigator.serviceWorker.controller.postMessage({ t: 'engine' });
    setInterval(() => navigator.serviceWorker.controller && navigator.serviceWorker.controller.postMessage({ t: 'engine' }), 20000);
    const s = document.createElement('script');
    s.src = './static/app.js?v=' + (window.MQ_V || '');
    s.onload = () => { const b = document.getElementById('boot'); if (b) { b.classList.add('gone'); setTimeout(() => b.remove(), 400); } };
    document.body.appendChild(s);
    runner();
  }).catch(e => {
    console.error(e);
    say('تعذّر تشغيل مقاطع على هذا المتصفح. استخدم Safari حديثًا ثم أعد فتح الصفحة.', 'Maqati could not start in this browser. Use an up-to-date Safari and open the page again.');
  });
})();
