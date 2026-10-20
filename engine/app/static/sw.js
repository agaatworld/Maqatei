/* Makes Maqati installable as an app, and shows a friendly page while the engine is starting. */
const OFF = '/static/offline.html';
self.addEventListener('install', e => e.waitUntil(caches.open('mq-v3').then(c => c.addAll([OFF, '/static/icon-192.png'])).then(() => self.skipWaiting())));
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', e => {
  if (e.request.mode !== 'navigate') return;
  e.respondWith(fetch(e.request).catch(() => caches.match(OFF)));
});
