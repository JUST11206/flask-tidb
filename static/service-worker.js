
/* ==========================================================
   StudyHub PWA Service Worker
   Offline + Online Support
   Strategy:

   HTML Pages:
   ONLINE  -> Network First -> Update Cache
   OFFLINE -> Cache

   CSS/JS:
   Stale While Revalidate

   Images:
   Cache First

   PDFs:
   Cache First

   Videos:
   Network First + Cache fallback
========================================================== */

const CACHE_VERSION = "studyhub-v9";

const STATIC_CACHE = `${CACHE_VERSION}-static`;
const PAGE_CACHE = `${CACHE_VERSION}-pages`;
const IMAGE_CACHE = `${CACHE_VERSION}-images`;
const PDF_CACHE = `${CACHE_VERSION}-pdfs`;
const VIDEO_CACHE = `${CACHE_VERSION}-videos`;
const FONT_CACHE = `${CACHE_VERSION}-fonts`;


/* ==========================================================
   APP SHELL
========================================================== */

const APP_SHELL = [
    "/dashboard",
    "/notes",
    "/lectures",
    "/pdfs",
    "/profile",

    "/static/manifest.json",

    "/static/images/logo.png",
    "/static/images/icon-192.png",
    "/static/images/icon-512.png"
];


/* ==========================================================
   NEVER CACHE
   Authentication / Admin / POST-like pages
========================================================== */

const NEVER_CACHE = [
    "/",
    "/login",
    "/signup",
    "/verify-otp",
    "/logout",

    "/admin",
    "/admin_login",
    "/admin_logout",

    "/add_note",
    "/manage_notes",

    "/add_pdf",
    "/manage_pdfs",

    "/add_lecture",
    "/manage_lectures"
];


/* ==========================================================
   INSTALL
========================================================== */

self.addEventListener("install", event => {

    console.log("📦 Installing StudyHub Service Worker...");

    event.waitUntil(
        (async () => {

            const cache = await caches.open(STATIC_CACHE);

            try {

                await cache.addAll(APP_SHELL);

                console.log("✅ App shell cached");

            } catch (error) {

                console.error(
                    "❌ App shell cache error:",
                    error
                );

            }

        })()
    );

    /*
       Activate new service worker immediately
    */
    self.skipWaiting();
});


/* ==========================================================
   ACTIVATE
========================================================== */

self.addEventListener("activate", event => {

    event.waitUntil(
        (async () => {

            const cacheNames = await caches.keys();

            await Promise.all(

                cacheNames.map(cacheName => {

                    const validCaches = [
                        STATIC_CACHE,
                        PAGE_CACHE,
                        IMAGE_CACHE,
                        PDF_CACHE,
                        VIDEO_CACHE,
                        FONT_CACHE
                    ];

                    if (!validCaches.includes(cacheName)) {

                        console.log(
                            "🗑 Removing old cache:",
                            cacheName
                        );

                        return caches.delete(cacheName);
                    }

                })

            );

            /*
               Take control of all open pages
            */
            await self.clients.claim();

            console.log(
                "🚀 StudyHub Service Worker activated"
            );

        })()
    );
});


/* ==========================================================
   FETCH
========================================================== */

self.addEventListener("fetch", event => {

    const request = event.request;

    /*
       Only GET requests can be cached
    */
    if (request.method !== "GET") {
        return;
    }

    const url = new URL(request.url);

    /*
       Only handle our own domain
    */
    if (url.origin !== self.location.origin) {
        return;
    }


    /* ======================================================
       NEVER CACHE
    ====================================================== */

    const blocked = NEVER_CACHE.some(route => {

        return (
            url.pathname === route ||
            url.pathname.startsWith(route + "/")
        );

    });


    if (blocked) {

        event.respondWith(

            fetch(request)
                .catch(() => offlinePage())

        );

        return;
    }


    /* ======================================================
       HTML PAGES
       NETWORK FIRST

       ONLINE:
       Server -> User
       Server -> Cache

       OFFLINE:
       Cache -> User
       ====================================================== */

    if (request.mode === "navigate") {

        event.respondWith(
            networkFirstPage(request)
        );

        return;
    }


    /* ======================================================
       IMAGES
       CACHE FIRST

       Fast offline images.
       If not cached -> network.
    ====================================================== */

    if (request.destination === "image") {

        event.respondWith(

            cacheFirst(
                request,
                IMAGE_CACHE
            )

        );

        return;
    }


    /* ======================================================
       CSS
       STALE WHILE REVALIDATE
    ====================================================== */

    if (request.destination === "style") {

        event.respondWith(

            staleWhileRevalidate(
                request,
                STATIC_CACHE
            )

        );

        return;
    }


    /* ======================================================
       JAVASCRIPT
       STALE WHILE REVALIDATE
    ====================================================== */

    if (request.destination === "script") {

        event.respondWith(

            staleWhileRevalidate(
                request,
                STATIC_CACHE
            )

        );

        return;
    }


    /* ======================================================
       FONTS
       CACHE FIRST
    ====================================================== */

    if (request.destination === "font") {

        event.respondWith(

            cacheFirst(
                request,
                FONT_CACHE
            )

        );

        return;
    }


    /* ======================================================
       PDF
    ====================================================== */

    if (
        url.pathname.endsWith(".pdf") ||
        url.pathname.startsWith("/static/pdfs/")
    ) {

        event.respondWith(

            cacheFirst(
                request,
                PDF_CACHE
            )

        );

        return;
    }


    /* ======================================================
       VIDEO
       NETWORK FIRST

       Important:
       Video files can be large.
       Network is preferred when online.

       If offline and previously cached,
       cached video can be used.
    ====================================================== */

    if (
        request.destination === "video" ||
        url.pathname.endsWith(".mp4") ||
        url.pathname.endsWith(".webm") ||
        url.pathname.endsWith(".mov")
    ) {

        event.respondWith(
            networkFirstVideo(request)
        );

        return;
    }


    /* ======================================================
       OTHER STATIC FILES
    ====================================================== */

    if (url.pathname.startsWith("/static/")) {

        event.respondWith(

            staleWhileRevalidate(
                request,
                STATIC_CACHE
            )

        );

        return;
    }

});


/* ==========================================================
   NETWORK FIRST PAGE
========================================================== */

async function networkFirstPage(request) {

    const cache = await caches.open(PAGE_CACHE);

    try {

        console.log(
            "🌐 Checking latest page:",
            request.url
        );

        const response = await fetch(request, {
            cache: "no-store"
        });


        if (
            response &&
            response.ok
        ) {

            /*
               Save latest server response
               into page cache.
            */

            await cache.put(
                request,
                response.clone()
            );

            console.log(
                "✅ Fresh page received:",
                new URL(request.url).pathname
            );

            return response;
        }


        throw new Error(
            "Network response was not OK"
        );

    }

    catch (error) {

        console.log(
            "📴 Offline / network failed:",
            request.url
        );

        /*
           Internet unavailable.
           Try cached page.
        */

        const cached = await cache.match(request);

        if (cached) {

            console.log(
                "📦 Loading cached page"
            );

            return cached;
        }


        /*
           Nothing cached either.
        */

        return offlinePage();
    }
}


/* ==========================================================
   NETWORK FIRST VIDEO
========================================================== */

async function networkFirstVideo(request) {

    const cache = await caches.open(VIDEO_CACHE);

    try {

        console.log(
            "🎥 Loading video from network:",
            request.url
        );

        const response = await fetch(request);

        if (
            response &&
            response.ok
        ) {

            /*
               Save video for offline use.
               WARNING:
               Large videos can consume a lot of storage.
            */

            await cache.put(
                request,
                response.clone()
            );

        }

        return response;

    }

    catch (error) {

        console.log(
            "📴 Video offline:",
            request.url
        );

        const cached = await cache.match(request);

        if (cached) {

            return cached;

        }

        return new Response(
            "Video is not available offline.",
            {
                status: 503,
                headers: {
                    "Content-Type":
                        "text/plain"
                }
            }
        );

    }
}


/* ==========================================================
   CACHE FIRST
========================================================== */

async function cacheFirst(
    request,
    cacheName
) {

    const cache = await caches.open(cacheName);

    const cached = await cache.match(request);

    if (cached) {

        return cached;
    }


    try {

        const response = await fetch(request);

        if (
            response &&
            response.ok
        ) {

            await cache.put(
                request,
                response.clone()
            );

        }

        return response;

    }

    catch (error) {

        /*
           Image fallback
        */

        if (
            request.destination === "image"
        ) {

            const logo = await caches.match(
                "/static/images/logo.png"
            );

            if (logo) {

                return logo;
            }
        }


        return new Response(
            "",
            {
                status: 503
            }
        );
    }
}


/* ==========================================================
   STALE WHILE REVALIDATE
========================================================== */

async function staleWhileRevalidate(
    request,
    cacheName
) {

    const cache = await caches.open(
        cacheName
    );

    const cached = await cache.match(
        request
    );


    const networkFetch = fetch(
        request,
        {
            cache: "no-cache"
        }
    )
        .then(response => {

            if (
                response &&
                response.ok
            ) {

                cache.put(
                    request,
                    response.clone()
                );
            }

            return response;

        })
        .catch(() => null);


    /*
       If cached version exists,
       return it immediately.

       Network runs in background
       and updates cache.
    */

    if (cached) {

        return cached;
    }


    /*
       Nothing cached.
       Wait for network.
    */

    const network = await networkFetch;

    if (network) {

        return network;
    }


    return new Response(
        "",
        {
            status: 503
        }
    );
}


/* ==========================================================
   MESSAGE HANDLER
========================================================== */

self.addEventListener(
    "message",
    event => {

        if (
            event.data ===
            "SKIP_WAITING"
        ) {

            self.skipWaiting();

        }


        if (
            event.data ===
            "cleanup"
        ) {

            event.waitUntil(

                cleanupCaches()

            );

        }

    }
);


/* ==========================================================
   CACHE CLEANUP
========================================================== */

async function cleanupCaches() {

    await limitCache(
        IMAGE_CACHE,
        80
    );

    await limitCache(
        PAGE_CACHE,
        25
    );

    await limitCache(
        PDF_CACHE,
        30
    );

    await limitCache(
        VIDEO_CACHE,
        10
    );

}


/* ==========================================================
   LIMIT CACHE SIZE
========================================================== */

async function limitCache(
    cacheName,
    maxItems
) {

    const cache = await caches.open(
        cacheName
    );

    const keys = await cache.keys();

    while (
        keys.length > maxItems
    ) {

        await cache.delete(
            keys.shift()
        );

    }
}


/* ==========================================================
   OFFLINE PAGE
========================================================== */

function offlinePage() {

    return new Response(

        `<!DOCTYPE html>

        <html lang="en">

        <head>

            <meta charset="UTF-8">

            <meta
                name="viewport"
                content="width=device-width,
                         initial-scale=1"
            >

            <meta
                name="theme-color"
                content="#4f46e5"
            >

            <title>
                StudyHub Offline
            </title>

            <style>

                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }

                body {

                    font-family:
                        Arial,
                        sans-serif;

                    background: #f8fafc;

                    display: flex;

                    align-items: center;

                    justify-content: center;

                    min-height: 100vh;

                    padding: 25px;
                }

                .card {

                    width: 100%;

                    max-width: 420px;

                    background: white;

                    border-radius: 22px;

                    padding: 35px;

                    text-align: center;

                    box-shadow:
                        0 15px 45px
                        rgba(0,0,0,.08);
                }

                .icon {

                    font-size: 70px;

                    margin-bottom: 20px;
                }

                h1 {

                    color: #4f46e5;

                    margin-bottom: 15px;
                }

                p {

                    color: #64748b;

                    line-height: 1.7;

                    margin-bottom: 25px;
                }

                button {

                    width: 100%;

                    padding: 15px;

                    border: none;

                    border-radius: 12px;

                    background: #4f46e5;

                    color: white;

                    font-size: 16px;

                    font-weight: bold;

                    cursor: pointer;
                }

                small {

                    display: block;

                    margin-top: 18px;

                    color: #94a3b8;
                }

            </style>

        </head>

        <body>

            <div class="card">

                <div class="icon">
                    📡
                </div>

                <h1>
                    You're Offline
                </h1>

                <p>
                    This page isn't available
                    offline yet.
                    <br><br>
                    Please connect to the
                    internet and try again.
                </p>

                <button
                    onclick="location.reload()"
                >
                    Try Again
                </button>

                <small>
                    StudyHub • Learn Anywhere 🚀
                </small>

            </div>

        </body>

        </html>`,

        {
            status: 200,

            headers: {
                "Content-Type":
                    "text/html"
            }
        }

    );
}


/* ==========================================================
   PERIODIC CLEANUP
========================================================== */

setInterval(
    () => {

        cleanupCaches();

    },
    30 * 60 * 1000
);


/* ==========================================================
   SERVICE WORKER UPDATED
========================================================== */

async function notifyClients() {

    const clientsList =
        await self.clients.matchAll();

    clientsList.forEach(client => {

        client.postMessage({

            type: "SW_UPDATED"

        });

    });

}
