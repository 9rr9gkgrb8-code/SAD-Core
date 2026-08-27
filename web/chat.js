"use strict";
(()=>{
  let currentSessionId=null;
  let initialized=false;

  const byId=id=>document.getElementById(id);
  const escapeText=value=>String(value).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const apiCall=(path,options={})=>window.api(path,options);

  function chatMarkup(){
    const section=document.createElement("section");
    section.id="chat";
    section.className="view card chat-view";
    section.hidden=true;
    section.innerHTML=`
      <div class="chat-heading">
        <div><p class="eyebrow">SAD CHAT</p><h2 tabindex="-1">Talk with SAD</h2><p class="muted">Free-form conversation stays separate from Forge quests and repair authority.</p></div>
        <button id="new-chat" class="secondary" type="button">New conversation</button>
      </div>
      <div class="chat-shell">
        <aside class="chat-history" aria-label="Conversation history">
          <div class="chat-history-title"><h3>Conversations</h3><span id="chat-history-count" class="muted"></span></div>
          <div id="chat-session-list" class="chat-session-list"></div>
        </aside>
        <div class="chat-main">
          <div class="chat-thread-header">
            <div><strong id="chat-title">New conversation</strong><span id="chat-engine" class="muted">Ready</span></div>
            <button id="archive-chat" class="secondary" type="button" disabled>Archive</button>
          </div>
          <div id="chat-messages" class="chat-messages" role="log" aria-live="polite" aria-relevant="additions text" aria-label="SAD conversation">
            <div class="chat-empty"><strong>Start anywhere.</strong><span>Ask a question, think something through, troubleshoot, plan, or just talk.</span></div>
          </div>
          <form id="chat-form" class="chat-composer">
            <label for="chat-input" class="chat-input-label">Message SAD</label>
            <textarea id="chat-input" name="message" rows="2" maxlength="50000" placeholder="Message SAD…" required></textarea>
            <button id="chat-send" type="submit">Send</button>
          </form>
          <p id="chat-status" class="muted" role="status" aria-live="polite"></p>
        </div>
      </div>`;
    document.querySelector("#app")?.appendChild(section);
  }

  function engineLabel(engine){return engine==="local_model"?"Local AI":"Built-in dialogue"}

  function renderMessages(session){
    const thread=byId("chat-messages");
    byId("chat-title").textContent=session.title||"Conversation";
    const messages=session.messages||[];
    if(!messages.length){
      thread.innerHTML='<div class="chat-empty"><strong>Start anywhere.</strong><span>Ask a question, think something through, troubleshoot, plan, or just talk.</span></div>';
    }else{
      thread.innerHTML=messages.map(item=>{
        const mine=item.role==="user";
        const engine=!mine&&item.engine?`<span class="chat-engine-tag">${escapeText(engineLabel(item.engine))}</span>`:"";
        return `<article class="chat-message ${mine?"chat-user":"chat-assistant"}"><div class="chat-message-meta"><strong>${mine?"You":"SAD"}</strong>${engine}</div><p>${escapeText(item.text)}</p></article>`;
      }).join("");
      const last=messages[messages.length-1];
      byId("chat-engine").textContent=last?.role==="assistant"?engineLabel(last.engine):"Ready";
    }
    byId("archive-chat").disabled=!currentSessionId;
    requestAnimationFrame(()=>{thread.scrollTop=thread.scrollHeight});
  }

  function renderSessionList(sessions){
    byId("chat-history-count").textContent=sessions.length?String(sessions.length):"";
    const list=byId("chat-session-list");
    if(!sessions.length){list.innerHTML='<p class="muted">No saved conversations yet.</p>';return}
    list.innerHTML=sessions.map(session=>`<button type="button" class="chat-session ${session.session_id===currentSessionId?"active":""}" data-session="${session.session_id}"><strong>${escapeText(session.title)}</strong><span>${escapeText(new Date(session.updated_at).toLocaleString())}</span></button>`).join("");
  }

  async function loadSessions(selectFirst=true){
    const data=await apiCall("/v1/chat/sessions");
    renderSessionList(data.sessions);
    if(selectFirst&&data.sessions.length&&!currentSessionId)await openSession(data.sessions[0].session_id,false);
    if(!data.sessions.length&&!currentSessionId)renderMessages({title:"New conversation",messages:[]});
    return data.sessions;
  }

  async function newConversation(){
    byId("chat-status").textContent="Starting a new conversation…";
    const session=await apiCall("/v1/chat/sessions",{method:"POST",body:"{}"});
    currentSessionId=session.session_id;
    renderMessages(session);
    await loadSessions(false);
    byId("chat-input").focus();
    byId("chat-status").textContent="New conversation ready.";
  }

  async function openSession(sessionId,refreshList=true){
    const session=await apiCall(`/v1/chat/sessions/${sessionId}`);
    currentSessionId=session.session_id;
    renderMessages(session);
    if(refreshList)await loadSessions(false);
  }

  async function ensureConversation(){
    if(currentSessionId)return currentSessionId;
    const sessions=await loadSessions(true);
    if(currentSessionId)return currentSessionId;
    if(!sessions.length)await newConversation();
    return currentSessionId;
  }

  async function sendMessage(event){
    event.preventDefault();
    const input=byId("chat-input"),send=byId("chat-send"),text=input.value.trim();
    if(!text)return;
    try{
      await ensureConversation();
      input.disabled=true;send.disabled=true;
      byId("chat-status").textContent="SAD is thinking…";
      const thread=byId("chat-messages");
      if(thread.querySelector(".chat-empty"))thread.replaceChildren();
      thread.insertAdjacentHTML("beforeend",`<article class="chat-message chat-user chat-pending"><div class="chat-message-meta"><strong>You</strong></div><p>${escapeText(text)}</p></article>`);
      thread.scrollTop=thread.scrollHeight;
      const data=await apiCall(`/v1/chat/sessions/${currentSessionId}/messages`,{method:"POST",body:JSON.stringify({message:text})});
      input.value="";
      renderMessages(data.session);
      byId("chat-engine").textContent=engineLabel(data.engine);
      byId("chat-status").textContent=data.engine==="local_model"?"Reply generated by your local AI.":"Local AI unavailable; SAD used its built-in dialogue layer.";
      await loadSessions(false);
    }catch(error){
      document.querySelector(".chat-pending")?.remove();
      byId("chat-status").textContent=error.message;
      window.message?.(error.message,true);
    }finally{
      input.disabled=false;send.disabled=false;input.focus();
    }
  }

  async function archiveConversation(){
    if(!currentSessionId)return;
    try{
      await apiCall(`/v1/chat/sessions/${currentSessionId}/archive`,{method:"POST",body:"{}"});
      currentSessionId=null;
      renderMessages({title:"New conversation",messages:[]});
      await loadSessions(true);
      byId("chat-status").textContent="Conversation archived.";
    }catch(error){byId("chat-status").textContent=error.message}
  }

  function ensureNav(){
    const nav=byId("nav");
    if(!nav||nav.querySelector('[data-view="chat"]'))return;
    const button=document.createElement("button");
    button.type="button";button.textContent="SAD Chat";button.dataset.view="chat";button.setAttribute("aria-controls","chat");
    button.onclick=async()=>{window.showView("chat");await loadSessions(true)};
    nav.prepend(button);
    if(!initialized){
      initialized=true;
      queueMicrotask(async()=>{window.showView("chat");try{await loadSessions(true)}catch(error){byId("chat-status").textContent=error.message}});
    }
  }

  function boot(){
    chatMarkup();
    byId("new-chat").addEventListener("click",()=>newConversation().catch(error=>byId("chat-status").textContent=error.message));
    byId("archive-chat").addEventListener("click",archiveConversation);
    byId("chat-form").addEventListener("submit",sendMessage);
    byId("chat-session-list").addEventListener("click",event=>{const button=event.target.closest(".chat-session");if(button)openSession(button.dataset.session).catch(error=>byId("chat-status").textContent=error.message)});
    byId("chat-input").addEventListener("keydown",event=>{if(event.key==="Enter"&&!event.shiftKey&&!event.isComposing){event.preventDefault();byId("chat-form").requestSubmit()}});
    const nav=byId("nav");
    if(nav)new MutationObserver(ensureNav).observe(nav,{childList:true});
    ensureNav();
  }

  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot,{once:true});else boot();
})();
