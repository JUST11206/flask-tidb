const CACHE_NAME = "studyhub-v6";

const APP_SHELL = [
    "/static/manifest.json",

    "/static/images/logo.png",
    "/static/images/icon-192.png",
    "/static/images/icon-512.png"
];


// =====================================================
// INSTALL
// =====================================================

self.addEventListener("install", event => {

    console.log("📦 StudyHub Service Worker Installing...");

    event.waitUntil(

        caches.open(CACHE_NAME)
        .then(cache => {

            console.log("Caching StudyHub App Shell");

            return cache.addAll(APP_SHELL);

        })

    );

    self.skipWaiting();

});


// =====================================================
// ACTIVATE
// =====================================================

self.addEventListener("activate", event => {

    console.log("🚀 StudyHub Service Worker Activated");

    event.waitUntil(

        caches.keys()

        .then(cacheNames => {

            return Promise.all(

                cacheNames

                .filter(cacheName => {

                    return cacheName !== CACHE_NAME;

                })

                .map(cacheName => {

                    console.log(
                        "Deleting old cache:",
                        cacheName
                    );

                    return caches.delete(cacheName);

                })

            );

        })

        .then(() => self.clients.claim())

    );

});


// =====================================================
// FETCH
// =====================================================

self.addEventListener("fetch", event => {

    const request = event.request;


    // ONLY GET REQUEST

    if(request.method !== "GET"){
        return;
    }


    const url = new URL(request.url);


    // =================================================
    // EXTERNAL REQUEST
    // =================================================

    if(url.origin !== self.location.origin){

        return;

    }


    // =================================================
    // NEVER CACHE AUTH / ADMIN PAGES
    // =================================================

    const noCacheRoutes = [

        "/",
        "/login",
        "/signup",
        "/verify-otp",
        "/logout",

        "/admin",
        "/admin_login",
        "/admin_logout",

        "/add_lecture",
        "/manage_lectures",

        "/add_pdf",
        "/manage_pdfs",

        "/add_note",
        "/manage_notes"

    ];


    const shouldNotCache = noCacheRoutes.some(route => {

        return url.pathname === route ||
               url.pathname.startsWith(route + "/");

    });


    if(shouldNotCache){

        event.respondWith(

            fetch(request)

            .catch(() => {

                return offlinePage();

            })

        );

        return;

    }


    // =================================================
    // HTML / PAGE NAVIGATION
    // NETWORK FIRST
    // =================================================

    if(request.mode === "navigate"){

        event.respondWith(

            networkFirstPage(request)

        );

        return;

    }


    // =================================================
    // IMAGES
    // CACHE FIRST
    // =================================================

    if(request.destination === "image"){

        event.respondWith(

            cacheFirst(request)

        );

        return;

    }


    // =================================================
    // CSS
    // =================================================

    if(request.destination === "style"){

        event.respondWith(

            staleWhileRevalidate(request)

        );

        return;

    }


    // =================================================
    // JAVASCRIPT
    // =================================================

    if(request.destination === "script"){

        event.respondWith(

            staleWhileRevalidate(request)

        );

        return;

    }


    // =================================================
    // PDF FILES
    // =================================================

    if(
        url.pathname.startsWith("/static/pdfs/") ||
        url.pathname.endsWith(".pdf")
    ){

        event.respondWith(

            cacheFirst(request)

        );

        return;

    }


    // =================================================
    // OTHER STATIC FILES
    // =================================================

    if(url.pathname.startsWith("/static/")){

        event.respondWith(

            cacheFirst(request)

        );

        return;

    }

});


// =====================================================
// NETWORK FIRST PAGE
// =====================================================

async function networkFirstPage(request){

    try{

        const response = await fetch(request);


        if(
            !response ||
            !response.ok ||
            response.redirected
        ){

            return response;

        }


        const cache = await caches.open(CACHE_NAME);


        await cache.put(

            request,

            response.clone()

        );


        console.log(

            "📄 Page saved offline:",

            new URL(request.url).pathname

        );


        return response;

    }

    catch(error){

        console.log(

            "📡 Offline page request:",

            request.url

        );


        const cachedPage = await caches.match(request);


        if(cachedPage){

            console.log("✅ Opening cached page");

            return cachedPage;

        }


        return offlinePage();

    }

}


// =====================================================
// CACHE FIRST
// =====================================================

async function cacheFirst(request){

    const cachedResponse = await caches.match(request);


    if(cachedResponse){

        return cachedResponse;

    }


    try{

        const response = await fetch(request);


        if(
            response &&
            response.ok
        ){

            const cache = await caches.open(CACHE_NAME);


            await cache.put(

                request,

                response.clone()

            );


            console.log(

                "💾 Resource cached:",

                request.url

            );

        }


        return response;

    }

    catch(error){

        console.log(

            "Resource unavailable offline:",

            request.url

        );


        return new Response(

            "",

            {
                status: 503,
                statusText: "Offline"
            }

        );

    }

}


// =====================================================
// STALE WHILE REVALIDATE
// =====================================================

async function staleWhileRevalidate(request){

    const cache = await caches.open(CACHE_NAME);


    const cachedResponse = await cache.match(request);


    const networkResponse = fetch(request)

    .then(response => {

        if(
            response &&
            response.ok
        ){

            cache.put(

                request,

                response.clone()

            );

        }


        return response;

    })

    .catch(() => null);


    if(cachedResponse){

        return cachedResponse;

    }


    const response = await networkResponse;


    if(response){

        return response;

    }


    return new Response(

        "",

        {
            status: 503,
            statusText: "Offline"
        }

    );

}


// =====================================================
// OFFLINE PAGE
// =====================================================

function offlinePage(){

    return new Response(

        `
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta
name="viewport"
content="width=device-width, initial-scale=1">

<meta
name="theme-color"
content="#4f46e5">

<title>StudyHub • Offline</title>


<style>

*{
    margin:0;
    padding:0;
    box-sizing:border-box;
}

body{

    min-height:100vh;

    display:flex;
    align-items:center;
    justify-content:center;

    padding:25px;

    font-family:Arial,sans-serif;

    background:#f8fafc;

    color:#0f172a;

}

.offline-card{

    width:100%;
    max-width:420px;

    padding:40px 25px;

    background:white;

    border-radius:25px;

    text-align:center;

    box-shadow:
    0 20px 50px rgba(15,23,42,.10);

}

.offline-icon{

    width:90px;
    height:90px;

    display:flex;
    align-items:center;
    justify-content:center;

    margin:auto;

    border-radius:25px;

    background:#eef2ff;

    font-size:48px;

}

h1{

    margin-top:25px;

    color:#4f46e5;

    font-size:28px;

}

p{

    margin-top:12px;

    color:#64748b;

    font-size:15px;

    line-height:1.6;

}

button{

    width:100%;

    margin-top:25px;

    padding:15px;

    border:none;
    border-radius:12px;

    background:#4f46e5;

    color:white;

    font-size:15px;
    font-weight:700;

    cursor:pointer;

}

button:active{

    transform:scale(.98);

}

.offline-info{

    margin-top:18px;

    color:#94a3b8;

    font-size:12px;

}

</style>

</head>


<body>


<div class="offline-card">


    <div class="offline-icon">

        📡

    </div>


    <h1>

        You're Offline

    </h1>


    <p>

        This StudyHub page has not been
        saved for offline use yet.

        Open the page once while connected
        to the internet.

    </p>


    <button onclick="location.reload()">

        Try Again

    </button>


    <div class="offline-info">

        StudyHub • Learn Anywhere 🚀

    </div>


</div>


</body>

</html>
        `,

        {

            status: 200,

            headers: {

                "Content-Type":
                "text/html; charset=UTF-8"

            }

        }

    );

}