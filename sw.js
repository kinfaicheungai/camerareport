/* Camera Report - offline service worker
   Strategy: cache-first for everything in this app's own folder, with a
   background refresh when online (stale-while-revalidate) so the next visit
   with signal picks up any redeploy without ever blocking an offline open.
   Bump CACHE_NAME whenever you redeploy so old caches get cleared out. */
const CACHE_NAME = 'camreport-cache-v16';
const CORE_ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './icon.png',
  './icon-192.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(CORE_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  // Only handle GET requests within this app's own origin/scope.
  if (event.request.method !== 'GET') return;

  event.respondWith(
    caches.match(event.request).then((cached) => {
      const networkFetch = fetch(event.request)
        .then((resp) => {
          if (resp && resp.status === 200) {
            const copy = resp.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          }
          return resp;
        })
        .catch(() => cached); // offline: fall back to whatever is cached

      // Serve cached immediately if we have it (instant + offline-safe);
      // otherwise wait on the network.
      return cached || networkFetch;
    })
  );
});
