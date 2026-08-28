# SAD Platform Tier 3 UAT — Memory & Governed Tools

Tier 3 adds explicit personal Memory and governed internal Tool Actions to the SAD-as-platform Alpha. Do not claim Tier 3 operational on a deployment host until these scenarios pass with representative accounts and, where mobile is claimed, a paired phone.

## Entry gate

- `python -m unittest -v` passes.
- `python release_gate.py` passes.
- `python alpha_doctor.py` reports the expected Alpha core state.
- The candidate commit is clean and corresponds to the build under test.

## Memory ownership

1. Sign in as Account A and create memories in `fact`, `preference`, `goal`, `project`, and `note` categories.
2. Confirm Account A can list and search them.
3. Sign in as Account B and confirm none of Account A's memories are visible.
4. Attempt to update/delete an Account A memory using Account B and confirm denial/not-found.
5. Confirm `memory.json` remains local and Git-ignored.

## Memory context controls

1. Create one enabled memory and one disabled memory.
2. With the intended local model healthy, send a Chat turn with memory enabled for the request.
3. Confirm the response reports `memory_used: true` only when the Local AI engine was used and enabled memory existed.
4. Send another turn with `use_memory: false`; confirm `memory_used: false` and the saved memory is not supplied to model context.
5. Disable the memory and repeat; confirm it is not supplied.
6. Create an expiring memory, pass its expiry, and confirm it is no longer supplied to model context.
7. Confirm the built-in dialogue fallback never reports that memory was used.

## Memory edit/delete

1. Edit category/title/content/enable state on an owned memory and verify persistence after restart.
2. Delete an owned memory and confirm it cannot be read or searched afterward.
3. Confirm invalid categories, oversized content, malformed expiry timestamps, and unsupported update fields fail closed.

## Tool catalog

1. Open **Memory & Tools** and verify only registered built-in tools are shown.
2. Confirm the current Tier 3 catalog contains `platform.status`, `memory.search`, `memory.remember`, and `memory.forget`.
3. Confirm there is no generic shell, arbitrary URL/network, dynamic Python/plugin, package-install, filesystem, or Git execution tool.

## Read-only tool execution

1. Create a `platform.status` action.
2. Confirm it enters `ready` without a mutation approval because it is read-only.
3. Execute it and confirm it returns platform metadata only.
4. Create `memory.search`; confirm it can see only memories owned by the signed-in account.

## State-changing tool approval

1. Create `memory.remember`.
2. Confirm its initial state is `awaiting_approval`.
3. Attempt execution before approval; it must fail.
4. Reject it; confirm execution remains impossible and no memory is created.
5. Create another `memory.remember`, approve it explicitly, then execute it.
6. Confirm exactly one memory is created from the approved arguments.
7. Repeat with `memory.forget`; confirm deletion requires the same explicit approve → execute sequence.

## Tool ownership

1. Create an action as Account A.
2. Attempt to read, approve, reject, or execute it as Account B.
3. Every cross-account operation must fail/not-found.
4. Restart SAD and confirm action state persists locally without widening ownership.

## Event privacy

1. Perform memory create/update/delete and tool create/decision/execute actions.
2. Inspect Owner platform events.
3. Confirm event metadata records type, sequence, subject ID, and small status/category metadata only.
4. Confirm memory content, memory title, tool arguments, tool output payloads, passwords, sessions, and secrets do not appear in platform events.

## Mobile learning mode

On a paired `learning` phone:

- Memory list/create/search/update/delete works only for the signed-in account.
- Governed personal tools work through exact routes.
- State-changing tools still require account approval before execution.
- SAD Chat and Voice may use enabled personal memory with the same controls as desktop.
- Dashboard, account administration, Developer Workspace, repair governance, and `SAD-App` machine routes remain blocked.

## PWA privacy

1. Install/open the PWA.
2. Confirm Memory & Tools static JS/CSS can load from the shell cache.
3. Confirm `/v1/memory*` and `/v1/tools*` responses are never written into the service-worker cache.
4. Confirm private memory/tool data is unavailable offline without a live authenticated SAD host.

## Accessibility/manual UI

- Keyboard through Memory & Tools without a mouse.
- Visible focus on all controls.
- Labels are announced for category, title, memory content, search, tool selector, and JSON arguments.
- Status changes are announced through a live status region.
- 200% zoom remains usable.
- Narrow phone viewport does not force horizontal page scrolling.
- Touch controls remain at least 44px high.

## Stop conditions

Stop Tier 3 pilot expansion if any of these occur:

- one account can read/change another account's memory or tool action;
- disabled/expired memory reaches the model;
- built-in dialogue claims memory usage it did not perform;
- a mutating tool executes without explicit approval;
- an unknown/dynamic tool can be invoked;
- memory/tool private data is committed, cached by the PWA, or leaked into event metadata;
- Learning mode reaches privileged development/admin routes through a broad-prefix bypass.

## Exit evidence

Record the tested commit SHA, host, browser/device, local-model state, pass/fail for every scenario, and any deviations. Tier 3 is code-complete when automated gates pass; it is operationally accepted only after this host/device UAT is complete.
