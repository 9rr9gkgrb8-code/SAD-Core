"use strict";
const CACHE_NAME="sad-forge-shell-v6";
const SHELL=["/","/manifest.webmanifest","/ui/styles.css","/ui/owner_dashboard.css","/ui/chat.css","/ui/avatar.css","/ui/developer_workspace.css","/ui/platform.css","/ui/memory_tools.css","/ui/app.js","/ui/owner_dashboard.js","/ui/mobile.js","/ui/chat.js","/ui/avatar.js","/ui/developer_workspace.js","/ui/platform.js","/ui/memory_tools.js","/ui/icon.svg"];
self.addEventListener("install",event=>{event.waitUntil(caches.open(CACHE_NAME).then(cache=>cache.addAll(SHELL)).then(()=>self.skipWaiting()))});
self.addEventListener("activate",event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==CACHE_NAME).map(key=>caches.delete(key)))).then(()=>self.clients.claim()))});
self.addEventListener("fetch",event=>{
  const request=event.request;
  if(request.method!=="GET")return;
  const url=new URL(request.url);
  if(url.origin!==self.location.origin)return;
  if(url.pathname.startsWith("/v1/")||url.pathname.startsWith("/mobile/"))return;
  event.respondWith(fetch(request).then(response=>{
    if(response.ok){const copy=response.clone();caches.open(CACHE_NAME).then(cache=>cache.put(request,copy))}
    return response;
  }).catch(()=>caches.match(request).then(hit=>hit||caches.match("/"))));
});
