"use strict";
(()=>{
  let currentWorkspaceId=null;
  let initialized=false;
  const byId=id=>document.getElementById(id);
  const escapeText=value=>String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const apiCall=(path,options={})=>window.api(path,options);

  function markup(){
    const section=document.createElement("section");
    section.id="code-workspace";
    section.className="view card dev-workspace-view";
    section.hidden=true;
    section.innerHTML=`
      <div class="dev-heading">
        <div><p class="eyebrow">SAD DEVELOPER WORKSPACE</p><h2 tabindex="-1">Build in isolation</h2><p class="muted">Plan the file scope, generate multi-file code, run the full suite in Docker, inspect the exact diff, then let Owner decide whether tested files cross into the live project.</p></div>
        <button id="refresh-dev-workspaces" type="button" class="secondary">Refresh</button>
      </div>
      <div id="dev-builder" class="dev-builder">
        <label>Coding task<textarea id="dev-task" rows="5" maxlength="20000" placeholder="Build the feature, fix the bug, or refactor the component…"></textarea></label>
        <div class="dev-scope-actions"><button id="plan-dev-scope" type="button" class="secondary">Plan file scope</button><span class="muted">SAD suggests files only. Nothing is edited yet.</span></div>
        <label>Approved files, one per line<textarea id="dev-paths" rows="7" placeholder="api.py\nweb/app.js\ntest_feature.py"></textarea></label>
        <button id="create-dev-workspace" type="button">Create isolated workspace</button>
        <p id="dev-builder-status" class="muted" role="status" aria-live="polite"></p>
      </div>
      <div class="dev-grid">
        <aside class="dev-list-panel" aria-label="Developer workspaces"><h3>Workspaces</h3><div id="dev-workspace-list" class="dev-workspace-list"></div></aside>
        <section class="dev-detail" aria-labelledby="dev-detail-title">
          <div class="dev-detail-head"><div><p class="eyebrow">SELECTED WORKSPACE</p><h3 id="dev-detail-title">Choose a workspace</h3></div><span id="dev-state" class="pill">—</span></div>
          <p id="dev-summary" class="muted">Create or open an isolated coding workspace.</p>
          <div id="dev-scope" class="dev-scope"></div>
          <div id="dev-actions" class="dev-actions"></div>
          <section id="dev-diff-section" hidden><h4>Exact tested diff</h4><pre id="dev-diff" class="dev-code"></pre></section>
          <section id="dev-test-section" hidden><h4>Test output</h4><pre id="dev-tests" class="dev-code"></pre></section>
          <p id="dev-detail-status" class="muted" role="status" aria-live="polite"></p>
        </section>
      </div>`;
    document.querySelector("#app")?.appendChild(section);
  }

  function role(){return (byId("role")?.textContent||"").trim().toLowerCase()}
  function canWork(){return ["owner","developer"].includes(role())}
  function isOwner(){return role()==="owner"}

  function pathsFromInput(){
    return byId("dev-paths").value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
  }

  async function planScope(){
    const task=byId("dev-task").value.trim();
    if(!task)return byId("dev-builder-status").textContent="Enter a coding task first.";
    try{
      byId("dev-builder-status").textContent="SAD is planning the smallest file scope…";
      const plan=await apiCall("/v1/dev/workspaces/scope",{method:"POST",body:JSON.stringify({task})});
      byId("dev-paths").value=plan.paths.join("\n");
      byId("dev-builder-status").textContent=plan.summary||"Scope suggested. Review the file list before creating the workspace.";
    }catch(error){byId("dev-builder-status").textContent=error.message}
  }

  async function createWorkspace(){
    const task=byId("dev-task").value.trim(),allowed_paths=pathsFromInput();
    if(!task||!allowed_paths.length)return byId("dev-builder-status").textContent="Task and at least one approved file are required.";
    try{
      byId("dev-builder-status").textContent="Creating private isolated copy…";
      const workspace=await apiCall("/v1/dev/workspaces",{method:"POST",body:JSON.stringify({task,allowed_paths})});
      currentWorkspaceId=workspace.workspace_id;
      await refreshList();await openWorkspace(currentWorkspaceId,false);
      byId("dev-builder-status").textContent="Workspace created. Review the approved scope, then run isolated coding.";
    }catch(error){byId("dev-builder-status").textContent=error.message}
  }

  function stateLabel(value){return String(value||"unknown").replaceAll("_"," ")}

  function renderList(items){
    const out=byId("dev-workspace-list");
    if(!items.length){out.innerHTML='<p class="muted">No coding workspaces yet.</p>';return}
    out.innerHTML=items.map(item=>`<button type="button" class="dev-workspace-item ${item.workspace_id===currentWorkspaceId?"active":""}" data-id="${item.workspace_id}"><strong>${escapeText(item.task)}</strong><span>${escapeText(stateLabel(item.state))}</span><small>${escapeText(new Date(item.updated_at).toLocaleString())}</small></button>`).join("");
  }

  async function refreshList(){
    const data=await apiCall("/v1/dev/workspaces");renderList(data.workspaces);return data.workspaces;
  }

  function actionButton(label,action,primary=false){return `<button type="button" class="dev-action ${primary?"":"secondary"}" data-action="${action}">${escapeText(label)}</button>`}

  function renderDetail(item){
    currentWorkspaceId=item.workspace_id;
    byId("dev-detail-title").textContent=item.task;
    byId("dev-state").textContent=stateLabel(item.state);
    byId("dev-summary").textContent=item.summary||"Scope approved. No code generated yet.";
    byId("dev-scope").innerHTML=`<strong>Approved scope</strong><ul>${(item.allowed_paths||[]).map(path=>`<li>${escapeText(path)}</li>`).join("")}</ul>${item.changed_paths?.length?`<strong>Changed by SAD</strong><ul>${item.changed_paths.map(path=>`<li>${escapeText(path)}</li>`).join("")}</ul>`:""}`;
    let actions="";
    if(item.state==="scope_approved"&&canWork())actions+=actionButton("Generate code + run Docker tests","execute",true);
    if(item.state==="tests_passed"&&isOwner())actions+=actionButton("YES: Apply tested workspace","apply",true);
    if(item.state==="applied"&&isOwner())actions+=actionButton("Rollback applied workspace","rollback");
    byId("dev-actions").innerHTML=actions||'<span class="muted">No action available for this role/state.</span>';
    const diff=String(item.diff||"");byId("dev-diff-section").hidden=!diff;byId("dev-diff").textContent=diff;
    const tests=String(item.test_output||"");byId("dev-test-section").hidden=!tests;byId("dev-tests").textContent=tests;
    byId("dev-detail-status").textContent=item.tests?`Tests: ${item.tests.passed?"PASS":"FAIL"} (exit ${item.tests.returncode})`:"";
    renderListHighlight();
  }

  function renderListHighlight(){document.querySelectorAll(".dev-workspace-item").forEach(button=>button.classList.toggle("active",button.dataset.id===currentWorkspaceId))}

  async function openWorkspace(id,refresh=true){
    try{const item=await apiCall(`/v1/dev/workspaces/${id}`);renderDetail(item);if(refresh)await refreshList()}catch(error){byId("dev-detail-status").textContent=error.message}
  }

  async function runAction(action){
    if(!currentWorkspaceId)return;
    const labels={execute:"SAD is generating code and running the isolated full test suite…",apply:"Applying only the exact tested files…",rollback:"Restoring the pre-application files…"};
    try{
      byId("dev-detail-status").textContent=labels[action]||"Working…";
      const item=await apiCall(`/v1/dev/workspaces/${currentWorkspaceId}/${action}`,{method:"POST",body:"{}"});
      renderDetail(item);await refreshList();
      byId("dev-detail-status").textContent=action==="execute"?(item.tests?.passed?"Isolated coding passed. Review the exact diff before Owner approval.":"Isolated coding did not pass. Live code remains unchanged."):action==="apply"?"Tested workspace applied locally. Git was not changed.":"Workspace rolled back and verified.";
    }catch(error){byId("dev-detail-status").textContent=error.message}
  }

  function ensureNav(){
    const nav=byId("nav");if(!nav||nav.querySelector('[data-view="code-workspace"]'))return;
    const dashboard=[...nav.querySelectorAll("button")].find(button=>button.dataset.view==="dashboard");
    if(!dashboard)return;
    const button=document.createElement("button");button.type="button";button.textContent="Code Workspace";button.dataset.view="code-workspace";button.setAttribute("aria-controls","code-workspace");
    button.onclick=async()=>{window.showView("code-workspace");try{await refreshList()}catch(error){byId("dev-detail-status").textContent=error.message}};
    dashboard.insertAdjacentElement("afterend",button);
    const builder=byId("dev-builder");if(builder)builder.hidden=!canWork();
    if(!initialized)initialized=true;
  }

  function boot(){
    markup();
    byId("plan-dev-scope").addEventListener("click",planScope);
    byId("create-dev-workspace").addEventListener("click",createWorkspace);
    byId("refresh-dev-workspaces").addEventListener("click",()=>refreshList().catch(error=>byId("dev-detail-status").textContent=error.message));
    byId("dev-workspace-list").addEventListener("click",event=>{const button=event.target.closest(".dev-workspace-item");if(button)openWorkspace(button.dataset.id)});
    byId("dev-actions").addEventListener("click",event=>{const button=event.target.closest(".dev-action");if(button)runAction(button.dataset.action)});
    const nav=byId("nav");if(nav)new MutationObserver(ensureNav).observe(nav,{childList:true});ensureNav();
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot,{once:true});else boot();
})();
