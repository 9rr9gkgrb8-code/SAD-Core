const CACHE_NAME = "sad-forge-shell-v1";
const SHELL = ["/", "/health"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL)));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/v1/") || url.pathname === "/health") {
    event.respondWith(fetch(event.request));
    return;
  }
  event.respondWith(fetch(event.request).catch(() => caches.match(event.request).then((cached) => cached || caches.match("/"))));
});
