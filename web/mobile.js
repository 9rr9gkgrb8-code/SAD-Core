"use strict";
(()=>{
  const LOOPBACK=new Set(["127.0.0.1","localhost","::1"]);
  const remote=!LOOPBACK.has(location.hostname);
  let pairedMarker=localStorage.getItem("sad_device_paired")==="1";
  let installPrompt=null;
  const byId=id=>document.getElementById(id);
  const SURFACE_ASSETS={
    chat:{css:"/ui/chat.css",js:"/ui/chat.js"},
    developer_workspace:{css:"/ui/developer_workspace.css",js:"/ui/developer_workspace.js"},
    platform:{css:"/ui/platform.css",js:"/ui/platform.js"},
  };

  function headers(){return {}}
  function showPairing(error=""){
    const pairing=byId("pairing"),login=byId("login"),app=byId("app");
    if(pairing)pairing.hidden=false;
    if(login)login.hidden=true;
    if(app)app.hidden=true;
    const out=byId("pairing-error");if(out)out.textContent=error;
  }
  function showLogin(){
    const pairing=byId("pairing"),login=byId("login");
    if(pairing)pairing.hidden=true;
    if(login)login.hidden=false;
  }
  async function forgetDevice(){
    try{if(remote)await fetch("/mobile/forget",{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"})}catch(_error){}
    pairedMarker=false;
    localStorage.removeItem("sad_device_paired");
    sessionStorage.removeItem("sad_token");
    location.reload();
  }
  function verifyPairingCookie(){
    if(!remote||!pairedMarker)return;
    fetch("/mobile/status",{cache:"no-store"}).then(response=>{
      if(response.ok)return;
      pairedMarker=false;localStorage.removeItem("sad_device_paired");showPairing("This phone needs to be paired again.");
    }).catch(()=>{});
  }
  function ensurePaired(){
    if(!remote){showLogin();return true}
    if(!pairedMarker){showPairing();return false}
    showLogin();verifyPairingCookie();return true;
  }
  function handleApiError(text){
    if(remote&&/device_pairing_required|not paired|access has expired/i.test(String(text))){
      pairedMarker=false;localStorage.removeItem("sad_device_paired");showPairing("This phone needs to be paired again.");return true;
    }
    return false;
  }

  const pairingForm=byId("pairing-form");
  if(pairingForm)pairingForm.addEventListener("submit",async event=>{
    event.preventDefault();
    const body=Object.fromEntries(new FormData(pairingForm));
    try{
      const response=await fetch("/mobile/pair",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
      const data=await response.json();
      if(!response.ok)throw new Error(data.error||"Pairing failed");
      pairedMarker=true;localStorage.setItem("sad_device_paired","1");
      byId("paired-device").textContent=`Paired: ${data.device.label} (${data.device.mode.replaceAll("_"," ")})`;
      pairingForm.reset();showLogin();
    }catch(error){byId("pairing-error").textContent=error.message}
  });

  const forget=byId("forget-device");
  if(forget){forget.hidden=!remote;forget.addEventListener("click",forgetDevice)}

  const state=byId("connection-state");
  function updateConnection(){if(state){state.textContent=navigator.onLine?"Online":"Offline";state.classList.toggle("offline",!navigator.onLine)}}
  addEventListener("online",updateConnection);addEventListener("offline",updateConnection);updateConnection();

  const install=byId("install-app");
  addEventListener("beforeinstallprompt",event=>{event.preventDefault();installPrompt=event;if(install)install.hidden=false});
  if(install)install.addEventListener("click",async()=>{
    if(!installPrompt)return;
    installPrompt.prompt();await installPrompt.userChoice;installPrompt=null;install.hidden=true;
  });
  addEventListener("appinstalled",()=>{if(install)install.hidden=true});

  if("serviceWorker" in navigator&&window.isSecureContext){
    addEventListener("load",()=>navigator.serviceWorker.register("/sw.js").catch(()=>{}));
  }

  function loadSurface(name){
    const asset=SURFACE_ASSETS[name];if(!asset)return;
    if(!document.querySelector(`link[href="${asset.css}"]`)){
      const style=document.createElement("link");style.rel="stylesheet";style.href=asset.css;document.head.appendChild(style);
    }
    if(!document.querySelector(`script[src="${asset.js}"]`)){
      const script=document.createElement("script");script.src=asset.js;script.async=false;document.head.appendChild(script);
    }
  }
  loadSurface("chat");
  loadSurface("developer_workspace");
  loadSurface("platform");

  window.SADMobile={remote,headers,ensurePaired,handleApiError,forgetDevice};
})();
