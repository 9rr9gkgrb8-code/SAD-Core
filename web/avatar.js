"use strict";
// Sasha avatar: a local visual + audio presence for SAD Chat. No microphone capture and
// no third-party network. Reply audio comes from the loopback TTS service via the SAD API
// (/v1/voice/speak) when it is ready, otherwise from the browser's built-in speechSynthesis.
// The chat log stays the announced source of truth, so the SVG is aria-hidden.
(()=>{
  const STATES=["idle","listening","thinking","speaking"];
  const reducedMotion=window.matchMedia&&window.matchMedia("(prefers-reduced-motion:reduce)");
  let stage=null,mouth=null,statusEl=null,muteBtn=null;
  let state="idle",speaking=false,rafId=0,timer=0,blinkTimer=0,companionStage=0;
  let ttsReady=false,audioCtx=null,activeSource=null;

  const readMuted=()=>{try{return localStorage.getItem("sad_avatar_muted")==="1"}catch(_e){return false}};
  const writeMuted=value=>{try{localStorage.setItem("sad_avatar_muted",value?"1":"0")}catch(_e){}};
  const authToken=()=>{try{return sessionStorage.getItem("sad_token")||""}catch(_e){return ""}};
  let muted=readMuted();

  function estimateMs(text){return Math.min(12000,Math.max(600,String(text||"").trim().length*55))}
  function setMouth(open){if(mouth){const o=Math.max(0,Math.min(1,open));mouth.setAttribute("ry",String(1.4+o*5.6));mouth.setAttribute("rx",String(7-o*1.4))}}
  function reduced(){return !!(reducedMotion&&reducedMotion.matches)}

  function stopAnimation(){if(rafId)cancelAnimationFrame(rafId);if(timer)clearTimeout(timer);rafId=0;timer=0}
  function endSpeaking(){
    speaking=false;stopAnimation();setMouth(0);
    if(activeSource){try{activeSource.onended=null;activeSource.stop()}catch(_e){}activeSource=null}
    setState(document.activeElement&&document.activeElement.id==="chat-input"?"listening":"idle");
  }

  function oscillateFlap(startedAt){
    if(!speaking)return;
    const t=(performance.now()-startedAt)/140;
    setMouth(reduced()?0.5:0.5+0.45*Math.sin(t)+0.18*Math.sin(t*2.7));
    rafId=requestAnimationFrame(()=>oscillateFlap(startedAt));
  }
  function beginFlap(fallbackMs){speaking=true;oscillateFlap(performance.now());if(fallbackMs)timer=setTimeout(endSpeaking,fallbackMs)}

  function analyserFlap(analyser){
    if(!speaking)return;
    const buffer=new Uint8Array(analyser.fftSize);
    analyser.getByteTimeDomainData(buffer);
    let sum=0;
    for(let i=0;i<buffer.length;i++){const v=(buffer[i]-128)/128;sum+=v*v}
    setMouth(reduced()?0.5:Math.sqrt(sum/buffer.length)*3.4);
    rafId=requestAnimationFrame(()=>analyserFlap(analyser));
  }

  function setState(next){
    if(!STATES.includes(next))return;
    if(speaking&&next!=="speaking"&&next!=="idle")return;
    state=next;
    if(stage)stage.className="sasha-stage is-"+next+" stage-"+companionStage;
    if(statusEl)statusEl.textContent={idle:"Ready",listening:"Listening",thinking:"Thinking…",speaking:"Speaking"}[next];
  }

  function setCompanionStage(value){
    const n=Math.max(0,Math.min(4,Number(value)||0));
    if(n===companionStage)return;
    companionStage=n;
    if(stage)stage.className="sasha-stage is-"+state+" stage-"+companionStage;
  }

  async function speakViaService(text){
    const response=await fetch("/v1/voice/speak",{
      method:"POST",
      headers:{"Content-Type":"application/json","Authorization":"Bearer "+authToken()},
      body:JSON.stringify({text})
    });
    if(!response.ok)throw new Error("tts_unavailable");
    const bytes=await response.arrayBuffer();
    audioCtx=audioCtx||new (window.AudioContext||window.webkitAudioContext)();
    if(audioCtx.state==="suspended")await audioCtx.resume();
    const decoded=await audioCtx.decodeAudioData(bytes);
    const source=audioCtx.createBufferSource();source.buffer=decoded;
    const analyser=audioCtx.createAnalyser();analyser.fftSize=256;
    source.connect(analyser);analyser.connect(audioCtx.destination);
    stopAnimation();activeSource=source;speaking=true;
    source.onended=endSpeaking;
    source.start();
    analyserFlap(analyser);
  }

  function speakViaSynthesis(text){
    if(!("speechSynthesis" in window))throw new Error("no_speech");
    window.speechSynthesis.cancel();
    const utterance=new SpeechSynthesisUtterance(text.slice(0,4000));
    utterance.rate=1;utterance.pitch=1;
    utterance.onend=endSpeaking;utterance.onerror=endSpeaking;
    beginFlap(estimateMs(text)+1500);
    window.speechSynthesis.speak(utterance);
  }

  function speak(text){
    const clean=String(text||"").trim();
    stopAnimation();setState("speaking");
    if(muted||!clean){beginFlap(estimateMs(clean));return}
    const useService=ttsReady?speakViaService(clean):Promise.reject(new Error("skip"));
    Promise.resolve(useService).catch(()=>{
      try{speakViaSynthesis(clean)}catch(_e){beginFlap(estimateMs(clean))}
    });
  }

  function stop(){
    try{if("speechSynthesis" in window)window.speechSynthesis.cancel()}catch(_e){}
    endSpeaking();
  }

  function setMuted(value){
    muted=!!value;writeMuted(muted);
    if(muteBtn){muteBtn.setAttribute("aria-pressed",String(muted));muteBtn.textContent=muted?"Voice off":"Voice on"}
    if(muted)stop();
  }

  function scheduleBlink(){
    if(reduced())return;
    blinkTimer=setTimeout(()=>{
      const eyes=stage?stage.querySelectorAll(".sasha-eye"):[];
      eyes.forEach(eye=>eye.setAttribute("ry","0.6"));
      setTimeout(()=>eyes.forEach(eye=>eye.setAttribute("ry","3.6")),120);
      scheduleBlink();
    },2600+Math.random()*3200);
  }

  function refreshVoiceStatus(){
    fetch("/v1/voice/status",{headers:{"Authorization":"Bearer "+authToken()}})
      .then(response=>response.ok?response.json():null)
      .then(status=>{ttsReady=!!(status&&status.tts_ready)})
      .catch(()=>{ttsReady=false});
  }

  function build(host){
    if(document.getElementById("sasha-stage"))return;
    stage=document.createElement("div");
    stage.id="sasha-stage";stage.className="sasha-stage is-idle stage-0";stage.setAttribute("aria-hidden","true");
    stage.innerHTML=
      '<svg class="sasha-face" viewBox="0 0 64 64" focusable="false">'+
      '<circle class="sasha-ring" cx="32" cy="32" r="30"></circle>'+
      '<ellipse class="sasha-eye" cx="24" cy="27" rx="3" ry="3.6"></ellipse>'+
      '<ellipse class="sasha-eye" cx="40" cy="27" rx="3" ry="3.6"></ellipse>'+
      '<ellipse class="sasha-mouth" id="sasha-mouth" cx="32" cy="42" rx="7" ry="1.6"></ellipse>'+
      '</svg>'+
      '<span class="sasha-copy"><strong>Sasha</strong><span class="sasha-status" id="sasha-status">Ready</span></span>'+
      '<button type="button" class="sasha-mute" id="sasha-mute" aria-pressed="false">Voice on</button>';
    host.insertBefore(stage,host.firstChild);
    mouth=document.getElementById("sasha-mouth");
    statusEl=document.getElementById("sasha-status");
    muteBtn=document.getElementById("sasha-mute");
    muteBtn.addEventListener("click",()=>setMuted(!muted));
    setMuted(muted);
    const input=document.getElementById("chat-input");
    if(input){
      input.addEventListener("focus",()=>setState("listening"));
      input.addEventListener("blur",()=>{if(state==="listening")setState("idle")});
    }
    scheduleBlink();
    refreshVoiceStatus();
  }

  function mount(){
    const main=document.querySelector("#chat .chat-main");
    if(main){build(main);return true}
    return false;
  }

  window.SadAvatar={mount,setState,speak,stop,setMuted,setCompanionStage,isMuted:()=>muted,states:STATES.slice()};

  if(!mount()){
    const observer=new MutationObserver(()=>{if(mount())observer.disconnect()});
    observer.observe(document.documentElement,{childList:true,subtree:true});
  }
})();
