"use strict";
(()=>{
  const LOOPBACK=new Set(["127.0.0.1","localhost","::1"]);
  const remote=!LOOPBACK.has(location.hostname);
  let deviceToken=localStorage.getItem("sad_device_token")||"";
  let installPrompt=null;
  const byId=id=>document.getElementById(id);

  function headers(){return deviceToken?{"X-SAD-Device":deviceToken}:{}}
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
  function forgetDevice(){
    deviceToken="";
    localStorage.removeItem("sad_device_token");
    sessionStorage.removeItem("sad_token");
    location.reload();
  }
  function ensurePaired(){
    if(remote&&!deviceToken){showPairing();return false}
    showLogin();return true;
  }
  function handleApiError(text){
    if(remote&&/device_pairing_required|not paired|access has expired/i.test(String(text))){
      deviceToken="";localStorage.removeItem("sad_device_token");showPairing("This phone needs to be paired again.");return true;
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
      deviceToken=data.device_token;
      localStorage.setItem("sad_device_token",deviceToken);
      byId("paired-device").textContent=`Paired: ${data.device.label} (${data.device.mode.replaceAll("_"," ")})`;
      pairingForm.reset();showLogin();
    }catch(error){byId("pairing-error").textContent=error.message}
  });

  const forget=byId("forget-device");
  if(forget)forget.addEventListener("click",forgetDevice);

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

  window.SADMobile={remote,headers,ensurePaired,handleApiError,forgetDevice};
})();
