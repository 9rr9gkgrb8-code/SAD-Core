"use strict";

const legacyLoadDashboard = loadDashboard;
let ownerDashboardState = null;

function ownerJobForFailure(failureId) {
  return ownerDashboardState?.development?.find(item => item.failure_id === failureId) || null;
}

function ownerStateLabel(value) {
  return String(value || "unknown").replaceAll("_", " ");
}

function ownerEvidence(job) {
  if (!job) {
    return `<div class="repair-evidence pending"><strong>Forge evidence</strong><span>Not tested yet.</span></div>`;
  }
  const result = job.result || null;
  if (!result) {
    return `<div class="repair-evidence pending"><strong>Forge evidence</strong><span>${escapeText(ownerStateLabel(job.state))}</span></div>`;
  }
  const tests = Array.isArray(result.tests) ? result.tests : [];
  const passed = tests.filter(test => test.passed === true).length;
  const diagnostics = Array.isArray(result.diagnostics) ? result.diagnostics : [];
  const verdict = result.state === "succeeded" ? "Sandbox verification passed" : "Sandbox verification did not pass";
  return `<div class="repair-evidence ${result.state === "succeeded" ? "passed" : "failed"}"><strong>${escapeText(verdict)}</strong><span>${escapeText(passed)} of ${escapeText(tests.length)} reported tests passed${diagnostics.length ? ` • ${escapeText(diagnostics[0])}` : ""}</span></div>`;
}

function ownerAdvancedControls(failure, job) {
  const failureControl = failureActions(failure);
  const jobControl = job ? jobActions(job) : "—";
  if (failureControl === "—" && jobControl === "—") return "";
  return `<details class="advanced-workflow"><summary>Advanced workflow</summary><div class="advanced-actions">${failureControl !== "—" ? failureControl : ""}${jobControl !== "—" ? jobControl : ""}</div></details>`;
}

function ownerPrimaryActions(failure, job) {
  if (!job || ["triaged", "approved_for_isolated_work"].includes(job.state)) {
    return `<button class="owner-prepare" data-failure-id="${failure.failure_id}">Test proposed fix</button>`;
  }
  if (["in_forge", "verifying"].includes(job.state)) {
    return `<span class="repair-running" role="status">Forge sandbox is processing this repair.</span>`;
  }
  if (job.state === "awaiting_human_decision") {
    const passed = job.result?.state === "succeeded";
    return `<div class="owner-decision"><button class="owner-final yes" data-work-id="${job.work_item_id}" data-decision="approve" ${passed ? "" : "disabled title=\"Forge verification did not pass\""}>YES: Approve repair</button><button class="owner-final no secondary" data-work-id="${job.work_item_id}" data-decision="reject">NO: Reject repair</button></div><p class="decision-note">Your decision is recorded and the repair is closed. Alpha does not auto-merge changes into live code.</p>`;
  }
  if (["approved", "rejected"].includes(job.state)) {
    return `<p class="repair-running">Decision recorded: ${escapeText(job.human_decision || job.state)}. Use Advanced workflow if closure needs to be retried.</p>`;
  }
  if (job.state === "closed") {
    return `<p class="repair-running">Closed: ${escapeText(job.human_decision || "completed")}</p>`;
  }
  return `<button class="owner-prepare" data-failure-id="${failure.failure_id}">Resume repair test</button>`;
}

function ownerRepairCard(failure) {
  const job = ownerJobForFailure(failure.failure_id);
  const files = Array.isArray(failure.affected_files) && failure.affected_files.length ? failure.affected_files.join(", ") : "No file target supplied";
  return `<article class="repair-card"><div class="repair-card-head"><div><p class="eyebrow">${escapeText(failure.source || "SAD")} • ${escapeText(failure.category)}</p><h3>${escapeText(failure.summary)}</h3></div><span class="repair-state">${escapeText(ownerStateLabel(job?.state || failure.state))}</span></div><div class="repair-proposal"><span>Suggested fix</span><strong>${escapeText(failure.suggested_correction || "Review the evidence and propose a correction.")}</strong><small>Affected: ${escapeText(files)}</small></div>${ownerEvidence(job)}<div class="repair-actions">${ownerPrimaryActions(failure, job)}</div>${ownerAdvancedControls(failure, job)}</article>`;
}

async function ownerLoadDashboard() {
  if (account?.role !== "owner") return legacyLoadDashboard();
  try {
    ownerDashboardState = await api("/v1/dashboard");
    const failures = [...ownerDashboardState.failures].sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
    const open = failures.filter(failure => failure.state !== "closed");
    const closed = failures.filter(failure => failure.state === "closed");
    $("dashboard-output").innerHTML = `<div class="owner-inbox-head"><div><h3>Repair inbox</h3><p class="muted">SAD surfaces the failure. One click sends the proposed correction through Forge's isolated test path. You make the final decision.</p></div><div class="owner-inbox-count"><strong>${escapeText(open.length)}</strong><span>open</span></div></div>${open.length ? `<div class="repair-list">${open.map(ownerRepairCard).join("")}</div>` : `<div class="repair-empty"><strong>No open failures.</strong><span>New SAD or Forge failures will appear here.</span></div>`}${closed.length ? `<details class="repair-history"><summary>Closed repair history (${closed.length})</summary><div class="repair-list history">${closed.map(ownerRepairCard).join("")}</div></details>` : ""}`;
  } catch (err) {
    message(err.message, true);
  }
}

async function ownerPrepareFailure(failureId) {
  const failure = ownerDashboardState?.failures?.find(item => item.failure_id === failureId);
  let job = ownerJobForFailure(failureId);
  if (!failure) throw new Error("Failure is no longer available.");
  message("Sending the proposed repair through Forge isolation…");
  if (failure.state === "new") {
    await api(`/v1/failures/${failureId}/review`, {method: "POST", body: "{}"});
  }
  if (!job) {
    job = await api(`/v1/failures/${failureId}/push`, {method: "POST", body: JSON.stringify({approved: true})});
  }
  if (job.state === "triaged") {
    job = await api(`/v1/jobs/${job.work_item_id}/approve-isolated`, {method: "POST", body: JSON.stringify({source_snapshot: "owner-ui"})});
  }
  if (job.state === "approved_for_isolated_work") {
    job = await api(`/v1/jobs/${job.work_item_id}/execute`, {method: "POST", body: "{}"});
  }
  await ownerLoadDashboard();
  if (job.state === "awaiting_human_decision") {
    message(job.result?.state === "succeeded" ? "Forge finished the isolated test. Review the evidence and choose YES or NO." : "Forge finished, but verification did not pass. Review the evidence before deciding.", job.result?.state !== "succeeded");
  } else {
    message(`Repair workflow is ${ownerStateLabel(job.state)}.`);
  }
}

async function ownerFinalizeRepair(workId, decision) {
  message(decision === "approve" ? "Recording your approval…" : "Recording your rejection…");
  await api(`/v1/jobs/${workId}/decision`, {method: "POST", body: JSON.stringify({decision})});
  await api(`/v1/jobs/${workId}/close`, {method: "POST", body: "{}"});
  await ownerLoadDashboard();
  message(decision === "approve" ? "Repair approved and closed. No live-code merge was performed." : "Repair rejected and closed.");
}

loadDashboard = ownerLoadDashboard;
$("refresh-dashboard").onclick = loadDashboard;
$("dashboard-output").onclick = async event => {
  const prepare = event.target.closest(".owner-prepare");
  const final = event.target.closest(".owner-final");
  const advanced = event.target.closest(".dash-action");
  try {
    if (account?.role === "owner" && prepare) {
      prepare.disabled = true;
      await ownerPrepareFailure(prepare.dataset.failureId);
      return;
    }
    if (account?.role === "owner" && final) {
      final.disabled = true;
      await ownerFinalizeRepair(final.dataset.workId, final.dataset.decision);
      return;
    }
    if (advanced) {
      await api(advanced.dataset.path, {method: "POST", body: advanced.dataset.body});
      await loadDashboard();
      message("Workflow updated.");
    }
  } catch (err) {
    await loadDashboard();
    message(err.message, true);
  }
};
