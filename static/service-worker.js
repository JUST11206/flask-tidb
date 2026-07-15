const CACHE_NAME = "studyhub-v4";

const STATIC_FILES = [
    "/static/manifest.json",
    "/static/images/logo.png",
    "/static/images/icon-192.png",
    "/static/images/icon-512.png"
];


// ================= INSTALL =================

self.addEventListener("install", event => {

    console.log("StudyHub SW Installing...");

    event.waitUntil(
        caches.open(CACHE_NAME)
        .then(cache => cache.addAll(STATIC_FILES))
    );

    self.skipWaiting();

});


// ================= ACTIVATE =================

self.addEventListener("activate", event => {

    console.log("StudyHub SW Activated");

    event.waitUntil(

        caches.keys()
        .then(cacheNames => {

            return Promise.all(

                cacheNames
                .filter(name => name !== CACHE_NAME)
                .map(name => caches.delete(name))

            );

        })
        .then(() => self.clients.claim())

    );

});


// ================= FETCH =================

self.addEventListener("fetch", event => {

    const request = event.request;

    if(request.method !== "GET"){
        return;
    }


    const url = new URL(request.url);


    // ================= EXTERNAL =================

    if(url.origin !== self.location.origin){
        return;
    }


    // ================= NAVIGATION =================

    if(request.mode === "navigate"){

        event.respondWith(

            fetch(request)

            .then(async response => {

                const responseURL = new URL(response.url);


                // AUTH PAGES CACHE NAHI HONGE

                const authPages = [
                    "/",
                    "/login",
                    "/signup",
                    "/verify-otp",
                    "/logout"
                ];


                if(
                    response.redirected ||
                    authPages.includes(responseURL.pathname) ||
                    !response.ok
                ){

                    return response;

                }


                const cache =
                    await caches.open(CACHE_NAME);


                await cache.put(
                    request,
                    response.clone()
                );


                console.log(
                    "Page cached:",
                    url.pathname
                );


                return response;

            })


            .catch(async () => {

                console.log(
                    "Offline:",
                    url.pathname
                );


                // SAME PAGE CACHE

                const cachedPage =
                    await caches.match(request);


                if(cachedPage){

                    return cachedPage;

                }


                // ONLY DASHBOARD REQUEST GET DASHBOARD CACHE

                if(url.pathname === "/dashboard"){

                    const dashboard =
                        await caches.match("/dashboard");


                    if(dashboard){

                        return dashboard;

                    }

                }


                return offlinePage();

            })

        );


        return;

    }


    // ================= STATIC CACHE =================

    if(url.pathname.startsWith("/static/")){

        event.respondWith(

            caches.match(request)

            .then(cachedResponse => {

                if(cachedResponse){

                    return cachedResponse;

                }


                return fetch(request)

                .then(async response => {

                    if(!response || !response.ok){

                        return response;

                    }


                    const cache =
                        await caches.open(CACHE_NAME);


                    await cache.put(
                        request,
                        response.clone()
                    );


                    return response;

                });

            })

        );

    }

});


// ================= OFFLINE PAGE =================

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

        <title>StudyHub Offline</title>


        <style>

        *{
            box-sizing:border-box;
        }

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
            width:100%;
            max-width:400px;

            padding:35px 25px;

            background:white;

            border-radius:22px;

            box-shadow:
            0 15px 40px rgba(15,23,42,.08);
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
            width:100%;

            margin-top:20px;

            padding:14px;

            border:none;
            border-radius:11px;

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
                This page hasn't been saved
                for offline use yet.
            </p>

            <button onclick="location.reload()">
                Try Again
            </button>

        </div>

        </body>

        </html>
        `,

        {
            status:200,

            headers:{
                "Content-Type":
                "text/html; charset=UTF-8"
            }
        }

    );

}