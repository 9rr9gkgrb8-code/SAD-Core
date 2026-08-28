"use strict";
(()=>{
  const byId=id=>document.getElementById(id);
  const escapeText=value=>String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const apiCall=(path,options={})=>window.api(path,options);

  function markup(){
    const section=document.createElement("section");
    section.id="memory-tools";
    section.className="view card memory-tools-view";
    section.hidden=true;
    section.innerHTML=`
      <div class="memory-tools-heading"><div><p class="eyebrow">SAD PERSONAL CORE</p><h2 tabindex="-1">Memory & Tools</h2><p class="muted">Memory is explicit and yours. State-changing tools require your approval before execution.</p></div><button id="refresh-memory-tools" class="secondary" type="button">Refresh</button></div>
      <div class="memory-tools-grid">
        <section class="memory-panel" aria-labelledby="memory-heading">
          <div class="memory-panel-head"><div><h3 id="memory-heading">Saved memory</h3><p class="muted">Enabled memories may be supplied to Local AI Chat and Voice. Built-in dialogue does not claim to use them.</p></div></div>
          <form id="memory-form" class="memory-form">
            <label>Category<select id="memory-category" name="category"><option>fact</option><option>preference</option><option>goal</option><option>project</option><option selected>note</option></select></label>
            <label>Title<input id="memory-title" name="title" maxlength="120" required placeholder="What should SAD remember?"></label>
            <label class="memory-wide">Memory<textarea id="memory-content" name="content" maxlength="8000" rows="3" required></textarea></label>
            <label class="memory-check"><input id="memory-enabled" name="enabled" type="checkbox" checked> Use in Local AI context</label>
            <button type="submit">Save memory</button>
          </form>
          <form id="memory-search-form" class="memory-search"><label>Search memories<input id="memory-search" maxlength="500" placeholder="Search your saved memory"></label><button class="secondary" type="submit">Search</button></form>
          <div id="memory-list" class="memory-list"></div>
        </section>
        <section class="tools-panel" aria-labelledby="tools-heading">
          <div><h3 id="tools-heading">Governed tools</h3><p class="muted">Only reviewed built-in tools are available. No shell, dynamic plugin, arbitrary network, or Git execution.</p></div>
          <form id="tool-form" class="tool-form">
            <label>Tool<select id="tool-id" name="tool_id"></select></label>
            <label>Arguments (JSON)<textarea id="tool-args" rows="4">{}</textarea></label>
            <button type="submit">Create tool action</button>
          </form>
          <div id="tool-list" class="tool-list"></div>
        </section>
      </div>
      <p id="memory-tools-status" class="muted" role="status" aria-live="polite"></p>`;
    document.querySelector("#app")?.appendChild(section);
  }

  function memoryCard(item){
    const active=item.enabled?"enabled":"disabled";
    const expiry=item.expires_at?` · expires ${escapeText(new Date(item.expires_at).toLocaleString())}`:"";
    return `<article class="memory-item"><div><div class="memory-meta"><span class="pill">${escapeText(item.category)}</span><span class="muted">${active}${expiry}</span></div><strong>${escapeText(item.title)}</strong><p>${escapeText(item.content)}</p></div><div class="memory-actions"><button class="secondary memory-toggle" type="button" data-id="${item.memory_id}" data-enabled="${item.enabled?"false":"true"}">${item.enabled?"Disable":"Enable"}</button><button class="secondary memory-delete" type="button" data-id="${item.memory_id}">Delete</button></div></article>`;
  }

  function actionCard(item){
    const controls=[];
    if(item.state==="awaiting_approval"){
      controls.push(`<button class="tool-decision" data-id="${item.action_id}" data-decision="approve" type="button">Approve</button>`);
      controls.push(`<button class="secondary tool-decision" data-id="${item.action_id}" data-decision="reject" type="button">Reject</button>`);
    }else if(item.state==="ready"){
      controls.push(`<button class="tool-execute" data-id="${item.action_id}" type="button">Execute</button>`);
    }
    const output=item.output?`<pre>${escapeText(JSON.stringify(item.output,null,2))}</pre>`:"";
    const error=item.error?`<p class="error">${escapeText(item.error)}</p>`:"";
    return `<article class="tool-item"><div><strong>${escapeText(item.tool_id)}</strong><span class="pill">${escapeText(item.state)}</span><code>${escapeText(item.action_id)}</code>${output}${error}</div><div class="tool-actions">${controls.join("")}</div></article>`;
  }

  async function loadMemories(query=""){
    const data=query
      ?await apiCall("/v1/memory/search",{method:"POST",body:JSON.stringify({query,limit:100})})
      :await apiCall("/v1/memory");
    byId("memory-list").innerHTML=(data.memories||[]).map(memoryCard).join("")||'<p class="muted">No saved memories yet.</p>';
  }

  async function loadTools(){
    const [tools,actions]=await Promise.all([apiCall("/v1/tools"),apiCall("/v1/tools/actions")]);
    byId("tool-id").innerHTML=(tools.tools||[]).map(tool=>`<option value="${escapeText(tool.tool_id)}">${escapeText(tool.title)}${tool.approval_required?" · approval required":""}</option>`).join("");
    byId("tool-list").innerHTML=(actions.actions||[]).map(actionCard).join("")||'<p class="muted">No tool actions yet.</p>';
  }

  async function refresh(){
    try{byId("memory-tools-status").textContent="Refreshing personal memory and tools…";await Promise.all([loadMemories(),loadTools()]);byId("memory-tools-status").textContent="Ready."}
    catch(error){byId("memory-tools-status").textContent=error.message}
  }

  async function saveMemory(event){
    event.preventDefault();
    const body={category:byId("memory-category").value,title:byId("memory-title").value.trim(),content:byId("memory-content").value.trim(),enabled:byId("memory-enabled").checked};
    try{await apiCall("/v1/memory",{method:"POST",body:JSON.stringify(body)});event.target.reset();byId("memory-enabled").checked=true;await loadMemories();byId("memory-tools-status").textContent="Memory saved explicitly."}
    catch(error){byId("memory-tools-status").textContent=error.message}
  }

  async function memoryAction(button){
    const id=button.dataset.id;
    try{
      if(button.classList.contains("memory-delete"))await apiCall(`/v1/memory/${id}/delete`,{method:"POST",body:"{}"});
      else await apiCall(`/v1/memory/${id}`,{method:"POST",body:JSON.stringify({enabled:button.dataset.enabled==="true"})});
      await loadMemories();byId("memory-tools-status").textContent=button.classList.contains("memory-delete")?"Memory deleted.":"Memory context setting updated.";
    }catch(error){byId("memory-tools-status").textContent=error.message}
  }

  async function createTool(event){
    event.preventDefault();
    try{
      const args=JSON.parse(byId("tool-args").value||"{}");
      const action=await apiCall("/v1/tools/actions",{method:"POST",body:JSON.stringify({tool_id:byId("tool-id").value,args})});
      await loadTools();
      byId("memory-tools-status").textContent=action.approval_required?"Tool action created. Review and approve it before execution.":"Read-only tool action is ready to execute.";
    }catch(error){byId("memory-tools-status").textContent=error.message}
  }

  async function toolAction(button){
    const id=button.dataset.id;
    try{
      if(button.classList.contains("tool-decision")){
        await apiCall(`/v1/tools/actions/${id}/decision`,{method:"POST",body:JSON.stringify({decision:button.dataset.decision})});
      }else{
        await apiCall(`/v1/tools/actions/${id}/execute`,{method:"POST",body:"{}"});
      }
      await Promise.all([loadTools(),loadMemories()]);byId("memory-tools-status").textContent="Tool action updated.";
    }catch(error){byId("memory-tools-status").textContent=error.message}
  }

  function ensureNav(){
    const nav=byId("nav");if(!nav||nav.querySelector('[data-view="memory-tools"]'))return;
    const settings=[...nav.querySelectorAll("button")].find(button=>button.dataset.view==="settings");
    const button=document.createElement("button");button.type="button";button.textContent="Memory & Tools";button.dataset.view="memory-tools";button.setAttribute("aria-controls","memory-tools");
    button.onclick=async()=>{window.showView("memory-tools");await refresh()};
    if(settings)settings.insertAdjacentElement("beforebegin",button);else nav.appendChild(button);
  }

  function boot(){
    markup();
    byId("refresh-memory-tools").addEventListener("click",refresh);
    byId("memory-form").addEventListener("submit",saveMemory);
    byId("memory-search-form").addEventListener("submit",event=>{event.preventDefault();loadMemories(byId("memory-search").value.trim()).catch(error=>byId("memory-tools-status").textContent=error.message)});
    byId("memory-list").addEventListener("click",event=>{const button=event.target.closest(".memory-toggle,.memory-delete");if(button)memoryAction(button)});
    byId("tool-form").addEventListener("submit",createTool);
    byId("tool-list").addEventListener("click",event=>{const button=event.target.closest(".tool-decision,.tool-execute");if(button)toolAction(button)});
    const nav=byId("nav");if(nav)new MutationObserver(ensureNav).observe(nav,{childList:true});ensureNav();
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot,{once:true});else boot();
})();
