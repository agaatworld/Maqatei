/* Maqati for iPhone: keeps the app on the phone (works offline) and passes the app's api/media/export requests
   to the open Maqati page, where the engine runs (see boot.js). */
const V = 'mq-web-5.0.9-4e262048';
const BASE = new URL('./', self.location).pathname;          // e.g. /maqati/
const ENGINE = /^(api\/|media\/|export(\?|$))/;
let engineId = null;

self.addEventListener('install', e => e.waitUntil(self.skipWaiting()));
self.addEventListener('activate', e => e.waitUntil((async () => {
  for (const k of await caches.keys()) if (k !== V) await caches.delete(k);
  await self.clients.claim();
})()));
self.addEventListener('message', e => { if (e.data && e.data.t === 'engine' && e.source) engineId = e.source.id; });

async function engineClient(cid) {
  const all = await self.clients.matchAll({ type: 'window' });
  return all.find(c => c.id === engineId) || all.find(c => c.id === cid) || all[0] || null;
}

async function ask(req, path, cid) {
  const c = await engineClient(cid);
  if (!c) return new Response('<meta charset="utf-8"><p style="font:20px sans-serif;padding:30px">افتح تطبيق مقاطع أولًا ثم أعد المحاولة.<br>Open Maqati first, then try again.</p>',
    { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } });
  const body = ['GET', 'HEAD'].includes(req.method) ? null : await req.arrayBuffer();
  const ch = new MessageChannel();
  const got = new Promise(res => { ch.port1.onmessage = e => res(e.data); });
  c.postMessage({ t: 'req', method: req.method, url: req.url, path, range: req.headers.get('Range'), body }, [ch.port2].concat(body ? [body] : []));
  const r = await got;
  const h = { 'Content-Type': r.ctype || 'application/octet-stream', 'Cache-Control': 'no-store' };
  if (r.status === 206) { h['Content-Range'] = `bytes ${r.a}-${r.b}/${r.size}`; h['Accept-Ranges'] = 'bytes'; }
  else if (r.size != null) h['Accept-Ranges'] = 'bytes';
  if (r.status === 416) h['Content-Range'] = `bytes */${r.size}`;
  if (r.name) h['Content-Disposition'] = `attachment; filename*=UTF-8''${encodeURIComponent(r.name)}`;
  return new Response(req.method === 'HEAD' || [204, 304].includes(r.status) ? null : r.data, { status: r.status, headers: h });
}
self.addEventListener('fetch', e => {
  const u = new URL(e.request.url);
  if (u.origin !== self.location.origin || !u.pathname.startsWith(BASE)) return;
  const path = u.pathname.slice(BASE.length);
  if (ENGINE.test(path + (u.search ? '?' : ''))) {
    e.respondWith(ask(e.request, path, e.clientId));
    return;
  }
  // the app's own files: from the phone first, refreshed in the background (so it opens offline too)
  e.respondWith((async () => {
    const cache = await caches.open(V);
    const hit = await cache.match(e.request, { ignoreSearch: true });
    const net = fetch(e.request).then(r => { if (r.ok && e.request.method === 'GET') cache.put(e.request, r.clone()); return r; });
    if (hit) { e.waitUntil(net.catch(() => {})); return hit; }
    return net;
  })());
});
