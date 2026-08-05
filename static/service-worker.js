/* ==========================================================
   StudyHub PWA Service Worker
   Part 1 / 3
   Author : ChatGPT
   Version : v7
========================================================== */

const CACHE_VERSION = "studyhub-v8";

const STATIC_CACHE = `${CACHE_VERSION}-static`;
const PAGE_CACHE = `${CACHE_VERSION}-pages`;
const IMAGE_CACHE = `${CACHE_VERSION}-images`;
const PDF_CACHE = `${CACHE_VERSION}-pdfs`;
const FONT_CACHE = `${CACHE_VERSION}-fonts`;

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

    console.log("📦 Installing StudyHub PWA...");

    event.waitUntil(

        (async () => {

            const cache = await caches.open(STATIC_CACHE);

            await cache.addAll(APP_SHELL);

            console.log("✅ App Shell Cached");

        })()

    );

    self.skipWaiting();

});


/* ==========================================================
   ACTIVATE
========================================================== */

self.addEventListener("activate", event => {

    console.log("🚀 Activating Service Worker");

    event.waitUntil(

        (async () => {

            const keys = await caches.keys();

            await Promise.all(

                keys.map(key => {

                    if (

                        key !== STATIC_CACHE &&
                        key !== PAGE_CACHE &&
                        key !== IMAGE_CACHE &&
                        key !== PDF_CACHE &&
                        key !== FONT_CACHE

                    ) {

                        console.log("🗑 Removing old cache:", key);

                        return caches.delete(key);

                    }

                })

            );

            await self.clients.claim();

            console.log("✅ Ready");

        })()

    );

});


/* ==========================================================
   FETCH
========================================================== */

self.addEventListener("fetch", event => {

    const request = event.request;

    if (request.method !== "GET")
        return;

    const url = new URL(request.url);

    if (url.origin !== self.location.origin)
        return;


    /* ------------------------------------------
       Never Cache Authentication
    ------------------------------------------ */

    const blocked = NEVER_CACHE.some(route => {

        return url.pathname === route ||
               url.pathname.startsWith(route + "/");

    });

    if (blocked) {

        event.respondWith(

            fetch(request)

            .catch(() => offlinePage())

        );

        return;

    }


    /* ------------------------------------------
       HTML Pages
    ------------------------------------------ */
/* ------------------------------------------
   HTML Pages
------------------------------------------ */

if (request.mode === "navigate") {

    event.respondWith(

        cacheFirstPage(request)

    );

    return;

}

/* ==========================================================
   CACHE FIRST PAGE
========================================================== */

async function cacheFirstPage(request){

    const cache = await caches.open(PAGE_CACHE);


    const cached = await cache.match(request);


    if(cached){

        console.log(
            "📱 Offline page loaded:",
            request.url
        );

        return cached;

    }



    try{


        const response = await fetch(request);



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


    }

    catch(error){


        console.log(
            "No internet and no cache"
        );


        return offlinePage();


    }

}

    /* ------------------------------------------
       Images
    ------------------------------------------ */

    if (request.destination === "image") {

        event.respondWith(

            cacheFirst(

                request,

                IMAGE_CACHE

            )

        );

        return;

    }


    /* ------------------------------------------
       CSS
    ------------------------------------------ */

    if (request.destination === "style") {

        event.respondWith(

            staleWhileRevalidate(

                request,

                STATIC_CACHE

            )

        );

        return;

    }


    /* ------------------------------------------
       JavaScript
    ------------------------------------------ */

    if (request.destination === "script") {

        event.respondWith(

            staleWhileRevalidate(

                request,

                STATIC_CACHE

            )

        );

        return;

    }


    /* ------------------------------------------
       Fonts
    ------------------------------------------ */

    if (request.destination === "font") {

        event.respondWith(

            cacheFirst(

                request,

                FONT_CACHE

            )

        );

        return;

    }


    /* ------------------------------------------
       PDFs
    ------------------------------------------ */

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


    /* ------------------------------------------
       Other Static Files
    ------------------------------------------ */

    if (

        url.pathname.startsWith("/static/")

    ) {

        event.respondWith(

            cacheFirst(

                request,

                STATIC_CACHE

            )

        );

        return;

    }

});
/* ==========================================================
   PART 2
   CACHE STRATEGIES
========================================================== */


/* ==========================================================
   NETWORK FIRST
========================================================== */

async function networkFirstPage(request) {

    const cache = await caches.open(PAGE_CACHE);

    try {

        const networkResponse = await fetch(request);

        if (
            networkResponse &&
            networkResponse.ok &&
            !networkResponse.redirected
        ) {

          await  cache.put(
                request,
                networkResponse.clone()
            );

            console.log(
                "📄 Updated:",
                new URL(request.url).pathname
            );

        }

        return networkResponse;

    }

    catch (error) {

        console.log(
            "📡 Offline:",
            request.url
        );

        const cached = await cache.match(request);

        if (cached) {

            console.log(
                "✅ Cached page loaded"
            );

            return cached;

        }

        return offlinePage();

    }

}


/* ==========================================================
   CACHE FIRST
========================================================== */

async function cacheFirst(request, cacheName) {

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

            cache.put(
                request,
                response.clone()
            );

        }

        return response;

    }

    catch {

        if (request.destination === "image") {

            const logo = await caches.match(
                "/static/images/logo.png"
            );

            if (logo)
                return logo;

        }

        return new Response("", {
            status: 503
        });

    }

}


/* ==========================================================
   STALE WHILE REVALIDATE
========================================================== */

async function staleWhileRevalidate(
    request,
    cacheName
) {

    const cache = await caches.open(cacheName);

    const cached = await cache.match(request);

    const networkFetch = fetch(request)

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

    if (cached) {

        return cached;

    }

    const network = await networkFetch;

    if (network) {

        return network;

    }

    return new Response("", {
        status: 503
    });

}


/* ==========================================================
   BACKGROUND UPDATE
========================================================== */

async function updateCache(request) {

    try {

        const response = await fetch(request);

        if (
            response &&
            response.ok
        ) {

            const cache =
                await caches.open(PAGE_CACHE);

            await cache.put(
                request,
                response.clone()
            );

        }

    }

    catch (e) {

        console.log(
            "Background update skipped."
        );

    }

}


/* ==========================================================
   LIMIT CACHE SIZE
========================================================== */

async function limitCache(cacheName, maxItems) {

    const cache =
        await caches.open(cacheName);

    const keys =
        await cache.keys();

    if (
        keys.length <= maxItems
    )
        return;

    while (
        keys.length > maxItems
    ) {

        await cache.delete(keys[0]);

        keys.shift();

    }

}


/* ==========================================================
   CLEAN OLD FILES
========================================================== */

self.addEventListener(
    "message",
    event => {

        if (
            event.data === "cleanup"
        ) {

            limitCache(
                IMAGE_CACHE,
                80
            );

            limitCache(
                PAGE_CACHE,
                25
            );

            limitCache(
                PDF_CACHE,
                30
            );

        }

    }

);


/* ==========================================================
   ONLINE EVENT
========================================================== */

self.addEventListener(
    "sync",
    event => {

        if (
            event.tag ===
            "studyhub-sync"
        ) {

            console.log(
                "Background Sync"
            );

        }

    }

);
/* ==========================================================
   PART 3
   OFFLINE PAGE + FINAL
========================================================== */


/* ==========================================================
   OFFLINE PAGE
========================================================== */

function offlinePage() {

    return new Response(

`<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width,initial-scale=1">

<meta name="theme-color"
content="#4f46e5">

<title>StudyHub Offline</title>

<style>

*{
margin:0;
padding:0;
box-sizing:border-box;
}

body{

font-family:Arial,sans-serif;

background:#f8fafc;

display:flex;
align-items:center;
justify-content:center;

min-height:100vh;

padding:25px;

}

.card{

width:100%;
max-width:420px;

background:#fff;

border-radius:22px;

padding:35px;

text-align:center;

box-shadow:0 15px 45px rgba(0,0,0,.08);

}

.icon{

font-size:70px;

margin-bottom:20px;

}

h1{

color:#4f46e5;

margin-bottom:15px;

}

p{

color:#64748b;

line-height:1.7;

margin-bottom:25px;

}

button{

width:100%;

padding:15px;

border:none;

border-radius:12px;

background:#4f46e5;

color:#fff;

font-size:16px;

font-weight:bold;

cursor:pointer;

}

small{

display:block;

margin-top:18px;

color:#94a3b8;

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

This page isn't available offline yet.

Please connect to the internet once
to save this page.

</p>

<button onclick="location.reload()">

Try Again

</button>

<small>

StudyHub • Learn Anywhere 🚀

</small>

</div>

</body>

</html>`,

{

status:200,

headers:{

"Content-Type":"text/html"

}

}

);

}


/* ==========================================================
   PERIODIC CACHE CLEANUP
========================================================== */

setInterval(() => {

    limitCache(IMAGE_CACHE,80);

    limitCache(PAGE_CACHE,25);

    limitCache(PDF_CACHE,30);

},1000*60*30);


/* ==========================================================
   NOTIFY CLIENTS WHEN NEW SW IS ACTIVE
========================================================== */

async function notifyClients(){

    const clientsList=await self.clients.matchAll();

    clientsList.forEach(client=>{

        client.postMessage({

            type:"SW_UPDATED"

        });

    });

}

self.addEventListener("activate",event=>{

    event.waitUntil(

        notifyClients()

    );

});


/* ==========================================================
   OPTIONAL NAVIGATION PRELOAD
========================================================== */

self.addEventListener("activate",event=>{

event.waitUntil(

(async()=>{

if(self.registration.navigationPreload){

await self.registration.navigationPreload.enable();

}

})()

);

});


/* ==========================================================
   INSTALL COMPLETE
========================================================== */

console.log(
"🚀 StudyHub Service Worker Ready."
);