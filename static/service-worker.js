const CACHE_NAME = "studyhub-v1";

const urlsToCache = [
    "/",
    "/dashboard",
    "/static/images/logo.png",
    "/static/images/icon-192.png",
    "/static/images/icon-512.png"
];

self.addEventListener("install", event => {

    event.waitUntil(
        caches.open(CACHE_NAME)
        .then(cache => cache.addAll(urlsToCache))
    );

});

self.addEventListener("activate", event => {

    event.waitUntil(
        caches.keys().then(keys => {

            return Promise.all(
                keys
                .filter(key => key !== CACHE_NAME)
                .map(key => caches.delete(key))
            );

        })
    );

});

self.addEventListener("fetch", event => {

    event.respondWith(

        fetch(event.request)
        .catch(() => caches.match(event.request))

    );

});