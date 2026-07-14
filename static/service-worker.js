const CACHE_NAME = "studyhub-v2";

const STATIC_FILES = [
    "/",
    "/static/manifest.json",
    "/static/images/logo.png",
    "/static/images/icon-192.png",
    "/static/images/icon-512.png"
];


// ================= INSTALL =================

self.addEventListener("install", event => {

    console.log("StudyHub Service Worker Installing...");

    event.waitUntil(

        caches.open(CACHE_NAME)
        .then(cache => {

            return cache.addAll(STATIC_FILES);

        })

    );

    self.skipWaiting();

});


// ================= ACTIVATE =================

self.addEventListener("activate", event => {

    console.log("StudyHub Service Worker Activated");

    event.waitUntil(

        caches.keys().then(cacheNames => {

            return Promise.all(

                cacheNames
                .filter(name => name !== CACHE_NAME)
                .map(name => caches.delete(name))

            );

        })

    );

    self.clients.claim();

});


// ================= FETCH =================

self.addEventListener("fetch", event => {

    const request = event.request;

    if(request.method !== "GET"){
        return;
    }


    const url = new URL(request.url);


    // ================= YOUTUBE =================

    if(
        url.hostname.includes("youtube.com") ||
        url.hostname.includes("googlevideo.com")
    ){

        return;

    }


    // ================= PAGE NAVIGATION =================

    if(request.mode === "navigate"){

        event.respondWith(

            fetch(request)

            .then(response => {

                // Redirect/login response should not be cached

                if(response.redirected){

                    return response;

                }


                const responseClone =
                    response.clone();


                caches.open(CACHE_NAME)
                .then(cache => {

                    cache.put(
                        request,
                        responseClone
                    );

                });


                return response;

            })

            .catch(async () => {

                const cachedPage =
                    await caches.match(request);


                if(cachedPage){

                    return cachedPage;

                }


                const dashboard =
                    await caches.match("/dashboard");


                if(dashboard){

                    return dashboard;

                }


                return new Response(

                    `
                    <!DOCTYPE html>

                    <html>

                    <head>

                    <meta
                    name="viewport"
                    content="width=device-width, initial-scale=1">

                    <title>StudyHub Offline</title>

                    <style>

                    body{
                        min-height:100vh;

                        margin:0;

                        display:flex;
                        align-items:center;
                        justify-content:center;

                        padding:25px;

                        font-family:Arial,sans-serif;

                        background:#f8fafc;

                        color:#0f172a;

                        text-align:center;
                    }

                    .offline{
                        max-width:400px;
                    }

                    .icon{
                        font-size:65px;
                    }

                    h1{
                        margin:20px 0 10px;

                        color:#4f46e5;
                    }

                    p{
                        color:#64748b;

                        line-height:1.6;
                    }

                    button{
                        margin-top:20px;

                        padding:13px 22px;

                        border:none;
                        border-radius:10px;

                        background:#4f46e5;

                        color:white;

                        font-size:15px;
                        font-weight:bold;

                        cursor:pointer;
                    }

                    </style>

                    </head>


                    <body>

                    <div class="offline">

                        <div class="icon">
                            📡
                        </div>

                        <h1>
                            You're Offline
                        </h1>

                        <p>
                            Connect to the internet to access
                            this StudyHub page.
                        </p>

                        <button onclick="location.reload()">
                            Try Again
                        </button>

                    </div>

                    </body>

                    </html>
                    `,

                    {
                        headers:{
                            "Content-Type":"text/html"
                        }
                    }

                );

            })

        );

        return;

    }


    // ================= STATIC FILES =================

    if(url.pathname.startsWith("/static/")){

        event.respondWith(

            caches.match(request)

            .then(cachedResponse => {

                if(cachedResponse){

                    return cachedResponse;

                }


                return fetch(request)

                .then(networkResponse => {

                    if(
                        !networkResponse ||
                        networkResponse.status !== 200
                    ){

                        return networkResponse;

                    }


                    const responseClone =
                        networkResponse.clone();


                    caches.open(CACHE_NAME)

                    .then(cache => {

                        cache.put(
                            request,
                            responseClone
                        );

                    });


                    return networkResponse;

                });

            })

        );

    }

});