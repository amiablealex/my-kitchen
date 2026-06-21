/* My Kitchen service worker.
   Served from /static/, so its scope is /static/ — it caches the app-shell
   assets (CSS, fonts, icons) for instant loads and offline asset availability.
   Asset URLs are RELATIVE to this file, so they resolve correctly behind a
   reverse proxy / HA ingress sub-path. Page navigations are left to the server
   (no stale-HTML risk). Note: service workers only run in a secure context
   (HTTPS or localhost) — on a plain-HTTP LAN address this registers as a no-op,
   which is fine; the manifest still makes the app installable where supported. */

const CACHE = "mykitchen-static-v1";
const ASSETS = [
  "css/app.css",
  "fonts/figtree-var.woff2",
  "fonts/grandstander-var.woff2",
  "icons/icon-192.png",
  "icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  event.respondWith(
    caches.match(req).then((hit) => {
      if (hit) return hit;
      return fetch(req).then((res) => {
        if (res && res.ok && new URL(req.url).origin === self.location.origin) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      }).catch(() => hit);
    })
  );
});
