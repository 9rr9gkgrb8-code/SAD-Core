"use strict";
(()=>{
  const byId=id=>document.getElementById(id);
  const escapeText=value=>String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const apiCall=(path,options={})=>window.api(path,options);
  const MACHINE_CAPABILITIES=["platform:discover","platform:catalog","platform:modules","platform:compatibility","platform:events"];
  const EVENT_TYPES=["chat.session.created","chat.message.created","chat.session.archived","development.workspace.created","development.workspace.executed","development.workspace.applied","development.workspace.rolled_back","failure.created","forge.quest.created","forge.quest.completed","memory.created","memory.updated","memory.deleted","platform.client.created","platform.client.rotated","platform.client.revoked","tool.action.created","tool.action.decided","tool.action.completed","voice.turn.completed"];

  function markup(){
    const section=document.createElement("section");
    section.id="platform";
    section.className="view card platform-view";
    section.hidden=true;
    section.innerHTML=`
      <div class="platform-heading">
        <div><p class="eyebrow">SAD PLATFORM</p><h2 tabindex="-1">Platform Core</h2><p class="muted">One governed capability catalog for Chat, Memory, Tools, Study, Forge, Voice, Mobile, Coding, Repair, accounts, and local apps.</p></div>
        <button id="refresh-platform" class="secondary" type="button">Refresh</button>
      </div>
      <div id="platform-summary" class="platform-summary" aria-live="polite"></div>
      <div class="platform-boundary"><strong>Authority boundary</strong><span>Platform discovery is descriptive only. It never grants permissions, executes plugins, impersonates a person, or gives AI Git authority.</span></div>
      <div id="platform-modules" class="platform-modules"></div>
      <section id="platform-app-admin" class="platform-admin" hidden aria-labelledby="platform-app-title">
        <div class="platform-admin-head"><div><p class="eyebrow">OWNER CONTROL</p><h3 id="platform-app-title">Local app credentials</h3><p class="muted">Create loopback-only machine credentials with explicit read-only platform scopes. App secrets cannot become user sessions.</p></div><button id="refresh-platform-apps" class="secondary" type="button">Refresh apps</button></div>
        <form id="platform-app-form" class="platform-app-form">
          <label>App name<input id="platform-app-name" name="name" maxlength="80" required placeholder="Workshop status panel"></label>
          <fieldset><legend>Machine scopes</legend><div id="platform-capability-options" class="platform-check-grid"></div></fieldset>
          <fieldset><legend>Event subscriptions</legend><p class="muted">Subscriptions work only when <code>platform:events</code> is selected. Memory/tool events expose metadata only, never private content or arguments.</p><div id="platform-event-options" class="platform-check-grid platform-events-grid"></div></fieldset>
          <button type="submit">Create local app credential</button>
        </form>
        <div id="platform-secret-panel" class="platform-secret" hidden role="status" aria-live="polite"><strong>Copy this secret now</strong><p>SAD stores only a hash. This value cannot be retrieved later.</p><code id="platform-secret"></code></div>
        <div id="platform-client-list" class="platform-client-list"></div>
        <div class="platform-event-head"><h3>Recent platform events</h3><button id="load-platform-events" class="secondary" type="button">Load events</button></div>
        <div id="platform-event-list" class="platform-event-list"></div>
      </section>
      <p id="platform-status" class="muted" role="status" aria-live="polite"></p>`;
    document.querySelector("#app")?.appendChild(section);
  }

  function role(){return (byId("role")?.textContent||"").trim().toLowerCase()}
  function canSeePlatform(){return ["owner","developer","reviewer","viewer"].includes(role())}
  function isOwner(){return role()==="owner"}

  function capabilityMarkup(capability){
    const tags=[];
    if(capability.permission)tags.push(`<span class="platform-tag">${escapeText(capability.permission)}</span>`);
    if(capability.capability_version)tags.push(`<span class="platform-tag">v${escapeText(capability.capability_version)}</span>`);
    if(capability.lifecycle)tags.push(`<span class="platform-tag">${escapeText(capability.lifecycle)}</span>`);
    if(capability.mutates_state)tags.push('<span class="platform-tag">state-changing</span>');
    if(capability.human_approval_boundary)tags.push('<span class="platform-tag platform-approval">human approval</span>');
    return `<li class="platform-capability"><div><strong>${escapeText(capability.title)}</strong><p>${escapeText(capability.description)}</p></div><div class="platform-tags">${tags.join("")}</div></li>`;
  }

  function moduleMarkup(module){
    return `<article class="platform-module"><div class="platform-module-head"><div><p class="eyebrow">${escapeText(module.kind)}</p><h3>${escapeText(module.name)}</h3></div><span class="pill">${escapeText(module.status)}</span></div><p class="muted">${escapeText(module.description)}</p><p class="muted">Module v${escapeText(module.module_version||"1.0.0")}</p><ul>${(module.capabilities||[]).map(capabilityMarkup).join("")}</ul></article>`;
  }

  function render(data){
    byId("platform-summary").innerHTML=`<div><strong>${escapeText(data.platform_version)}</strong><span>Platform version</span></div><div><strong>${escapeText(data.module_count)}</strong><span>Visible modules</span></div><div><strong>${escapeText(data.capability_count)}</strong><span>Your capabilities</span></div><div><strong>${escapeText(data.api_version)}</strong><span>API contract</span></div>`;
    byId("platform-modules").innerHTML=(data.modules||[]).map(moduleMarkup).join("")||'<p class="muted">No platform modules are visible to this role.</p>';
    byId("platform-app-admin").hidden=!isOwner();
    byId("platform-status").textContent=`Catalog loaded for ${data.role}. Git authority: ${data.authority_model?.git_authority||"human host only"}.`;
  }

  function buildAdminOptions(){
    byId("platform-capability-options").innerHTML=MACHINE_CAPABILITIES.map((item,index)=>`<label><input type="checkbox" name="machine-capability" value="${item}" ${index===0?"checked":""}> <code>${item}</code></label>`).join("");
    byId("platform-event-options").innerHTML=EVENT_TYPES.map(item=>`<label><input type="checkbox" name="event-type" value="${item}"> <code>${item}</code></label>`).join("");
  }

  function checkedValues(name){return [...document.querySelectorAll(`input[name="${name}"]:checked`)].map(input=>input.value)}

  async function loadClients(){
    if(!isOwner())return;
    const data=await apiCall("/v1/platform/clients");
    const out=byId("platform-client-list");
    if(!data.clients.length){out.innerHTML='<p class="muted">No local app credentials yet.</p>';return}
    out.innerHTML=data.clients.map(client=>`<article class="platform-client"><div><strong>${escapeText(client.name)}</strong><p class="muted"><code>${escapeText(client.client_id)}</code></p><p>${(client.capability_ids||[]).map(item=>`<span class="platform-tag">${escapeText(item)}</span>`).join(" ")}</p></div><div><span class="pill">${client.active?"active":"revoked"}</span>${client.active?`<button class="secondary platform-client-action" type="button" data-id="${client.client_id}" data-action="rotate">Rotate secret</button><button class="secondary platform-client-action" type="button" data-id="${client.client_id}" data-action="revoke">Revoke</button>`:""}</div></article>`).join("");
  }

  async function createClient(event){
    event.preventDefault();
    const name=byId("platform-app-name").value.trim();
    const capability_ids=checkedValues("machine-capability"),event_types=checkedValues("event-type");
    try{
      byId("platform-status").textContent="Creating scoped local app credential…";
      const client=await apiCall("/v1/platform/clients",{method:"POST",body:JSON.stringify({name,capability_ids,event_types})});
      byId("platform-secret").textContent=`${client.client_id}.${client.client_secret}`;
      byId("platform-secret-panel").hidden=false;
      byId("platform-app-form").reset();
      await loadClients();
      byId("platform-status").textContent="Local app created. Copy the one-time secret now.";
    }catch(error){byId("platform-status").textContent=error.message}
  }

  async function clientAction(button){
    const id=button.dataset.id,action=button.dataset.action;
    try{
      const client=await apiCall(`/v1/platform/clients/${id}/${action}`,{method:"POST",body:"{}"});
      if(action==="rotate"){
        byId("platform-secret").textContent=`${client.client_id}.${client.client_secret}`;
        byId("platform-secret-panel").hidden=false;
        byId("platform-status").textContent="Secret rotated. The previous secret is invalid. Copy the new value now.";
      }else{
        byId("platform-secret-panel").hidden=true;
        byId("platform-status").textContent="Local app credential revoked.";
      }
      await loadClients();
    }catch(error){byId("platform-status").textContent=error.message}
  }

  async function loadEvents(){
    if(!isOwner())return;
    try{
      const data=await apiCall("/v1/platform/events/read",{method:"POST",body:JSON.stringify({after_seq:0,limit:50})});
      const events=(data.events||[]).slice().reverse();
      byId("platform-event-list").innerHTML=events.length?events.map(item=>`<article><strong>${escapeText(item.event_type)}</strong><span>#${escapeText(item.seq)} · ${escapeText(new Date(item.created_at).toLocaleString())}</span><code>${escapeText(item.subject_id||"platform")}</code></article>`).join(""):'<p class="muted">No platform events yet.</p>';
    }catch(error){byId("platform-status").textContent=error.message}
  }

  async function loadPlatform(){
    try{
      byId("platform-status").textContent="Reading platform catalog…";
      render(await apiCall("/v1/platform"));
      if(isOwner())await loadClients();
    }catch(error){byId("platform-status").textContent=error.message}
  }

  function ensureNav(){
    const nav=byId("nav");if(!nav||nav.querySelector('[data-view="platform"]')||!canSeePlatform())return;
    const settings=[...nav.querySelectorAll("button")].find(button=>button.dataset.view==="settings");
    const button=document.createElement("button");button.type="button";button.textContent="SAD Platform";button.dataset.view="platform";button.setAttribute("aria-controls","platform");
    button.onclick=async()=>{window.showView("platform");await loadPlatform()};
    if(settings)settings.insertAdjacentElement("beforebegin",button);else nav.appendChild(button);
  }

  function boot(){
    markup();buildAdminOptions();
    byId("refresh-platform").addEventListener("click",loadPlatform);
    byId("refresh-platform-apps").addEventListener("click",()=>loadClients().catch(error=>byId("platform-status").textContent=error.message));
    byId("platform-app-form").addEventListener("submit",createClient);
    byId("platform-client-list").addEventListener("click",event=>{const button=event.target.closest(".platform-client-action");if(button)clientAction(button)});
    byId("load-platform-events").addEventListener("click",loadEvents);
    const nav=byId("nav");if(nav)new MutationObserver(ensureNav).observe(nav,{childList:true});ensureNav();
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot,{once:true});else boot();
})();