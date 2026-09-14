const CACHE = "digiscore-shell-v2";
const SHELL = ["/", "/index.html", "/manifest.json", "/logo-alpha.svg"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.pathname.startsWith("/api") || url.pathname.startsWith("/src") || url.pathname.startsWith("/@") || url.pathname.startsWith("/node_modules")) {
    return;
  }
  event.respondWith(caches.match(req).then((cached) => cached || fetch(req).catch(() => cached)));
});
