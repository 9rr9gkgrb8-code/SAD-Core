"use strict";
(()=>{
  let initialized=false;
  const byId=id=>document.getElementById(id);
  const escapeText=value=>String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const apiCall=(path,options={})=>window.api(path,options);

  function markup(){
    const section=document.createElement("section");
    section.id="platform";
    section.className="view card platform-view";
    section.hidden=true;
    section.innerHTML=`
      <div class="platform-heading">
        <div><p class="eyebrow">SAD PLATFORM</p><h2 tabindex="-1">Platform Core</h2><p class="muted">One governed capability catalog for SAD Chat, Study, Forge, Mobile, Repair, Coding, accounts, and future clients.</p></div>
        <button id="refresh-platform" class="secondary" type="button">Refresh</button>
      </div>
      <div id="platform-summary" class="platform-summary" aria-live="polite"></div>
      <div class="platform-boundary"><strong>Authority boundary</strong><span>Platform discovery is descriptive only. It never grants permissions, executes plugins, or gives AI Git authority.</span></div>
      <div id="platform-modules" class="platform-modules"></div>
      <p id="platform-status" class="muted" role="status" aria-live="polite"></p>`;
    document.querySelector("#app")?.appendChild(section);
  }

  function role(){return (byId("role")?.textContent||"").trim().toLowerCase()}
  function canSeePlatform(){return ["owner","developer","reviewer","viewer"].includes(role())}

  function capabilityMarkup(capability){
    const tags=[];
    if(capability.permission)tags.push(`<span class="platform-tag">${escapeText(capability.permission)}</span>`);
    if(capability.mutates_state)tags.push('<span class="platform-tag">state-changing</span>');
    if(capability.human_approval_boundary)tags.push('<span class="platform-tag platform-approval">human approval</span>');
    return `<li class="platform-capability"><div><strong>${escapeText(capability.title)}</strong><p>${escapeText(capability.description)}</p></div><div class="platform-tags">${tags.join("")}</div></li>`;
  }

  function moduleMarkup(module){
    return `<article class="platform-module"><div class="platform-module-head"><div><p class="eyebrow">${escapeText(module.kind)}</p><h3>${escapeText(module.name)}</h3></div><span class="pill">${escapeText(module.status)}</span></div><p class="muted">${escapeText(module.description)}</p><ul>${(module.capabilities||[]).map(capabilityMarkup).join("")}</ul></article>`;
  }

  function render(data){
    byId("platform-summary").innerHTML=`<div><strong>${escapeText(data.platform_version)}</strong><span>Platform version</span></div><div><strong>${escapeText(data.module_count)}</strong><span>Visible modules</span></div><div><strong>${escapeText(data.capability_count)}</strong><span>Your capabilities</span></div><div><strong>${escapeText(data.api_version)}</strong><span>API contract</span></div>`;
    byId("platform-modules").innerHTML=(data.modules||[]).map(moduleMarkup).join("")||'<p class="muted">No platform modules are visible to this role.</p>';
    byId("platform-status").textContent=`Catalog loaded for ${data.role}. Git authority: ${data.authority_model?.git_authority||"human host only"}.`;
  }

  async function loadPlatform(){
    try{byId("platform-status").textContent="Reading platform catalog…";render(await apiCall("/v1/platform"))}
    catch(error){byId("platform-status").textContent=error.message}
  }

  function ensureNav(){
    const nav=byId("nav");if(!nav||nav.querySelector('[data-view="platform"]')||!canSeePlatform())return;
    const settings=[...nav.querySelectorAll("button")].find(button=>button.dataset.view==="settings");
    const button=document.createElement("button");button.type="button";button.textContent="SAD Platform";button.dataset.view="platform";button.setAttribute("aria-controls","platform");
    button.onclick=async()=>{window.showView("platform");await loadPlatform()};
    if(settings)settings.insertAdjacentElement("beforebegin",button);else nav.appendChild(button);
    initialized=true;
  }

  function boot(){
    markup();
    byId("refresh-platform").addEventListener("click",loadPlatform);
    const nav=byId("nav");if(nav)new MutationObserver(ensureNav).observe(nav,{childList:true});
    ensureNav();
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot,{once:true});else boot();
})();
