# SAD Developer Workspace

The Developer Workspace is SAD's governed general-purpose coding lane. It is separate from Forge Student and from the narrow self-repair workflow.

## Goal

Allow a signed-in Owner or Developer to give SAD a real software task, let the configured local model plan and edit multiple files in an isolated project copy, run the complete test suite inside the existing Docker security boundary, inspect the exact resulting diff, and then require Owner authorization before any tested file reaches the live project.

## Workflow

1. **Describe the coding task.**
2. **Plan file scope.** SAD may suggest the smallest set of source paths, but this step writes no code.
3. **Human approves the scope.** The user can edit the suggested list before creating the workspace.
4. **Create private workspace.** SAD copies the project into `.sad_dev/<workspace-id>/worktree` without Git/repository-control metadata or private runtime data.
5. **Generate code.** The local model may write/delete only paths on the approved scope list. It returns complete final file contents in a strict JSON plan.
6. **Run Docker verification.** The same digest-pinned, networkless, non-root Docker boundary used by repair verification runs the full Python unit suite against the copied project.
7. **Review evidence.** SAD shows changed paths, exact unified diff, test result/output, and integrity evidence.
8. **Owner decision.** Only Owner may select **YES: Apply tested workspace**.
9. **Host-controlled apply.** SAD rechecks every live source hash and every tested worktree hash, backs up every existing target, then applies the exact tested file set.
10. **Rollback.** Owner may restore the preserved pre-application file set if live files still match the application receipt.

## Roles

- **Owner:** plan, create, execute, inspect, apply, rollback.
- **Developer:** plan, create, execute, inspect. Cannot apply or rollback live code.
- **Reviewer / Viewer:** inspect workspace list, diff, tests, and state. Cannot generate or apply code.
- **Student / Teacher:** no Developer Workspace access.

The API enforces these rules through the existing `development:view`, `development:work`, and Owner-only `development:govern` permissions.

## Scope boundary

Automatic coding accepts at most 20 explicitly approved source paths per workspace. The coding model cannot target paths outside that list.

Protected from automatic coding and omitted from the coding worktree:

- `.git/`
- `.github/`
- `.sad_sandbox/`
- `.sad_dev/`
- `local_data/`
- Python cache directories
- account/session/progress/failure runtime JSON
- `.env` and environment-secret files

Hidden repository paths and unsupported/binary file types are also rejected as automatic coding targets.

The worktree is a source/test copy, not a repository checkout. If a future project requires control-plane files merely as test fixtures, that will need an explicit separate read-only-fixture design rather than silently adding them to the coding workspace.

## Allowed automatic file types

Current Alpha scope accepts text source/document assets with these suffixes:

- `.py`
- `.js`
- `.css`
- `.html`
- `.md`
- `.json`
- `.yml` / `.yaml`
- `.ps1`
- `.svg`
- `.webmanifest`
- `.txt`

This is an allow-list, not a promise that every project type is fully supported yet.

## Model contract

### Scope planning

The local model receives the coding task and a list of eligible project file names. It returns JSON only:

```json
{
  "summary": "Short scope explanation",
  "paths": ["api.py", "web/app.js", "test_feature.py"]
}
```

No source is edited during this step.

### Implementation

After the scope is approved, the local model receives only the approved files' source context and returns JSON only:

```json
{
  "summary": "Implemented the feature and tests",
  "edits": [
    {"path": "api.py", "action": "write", "content": "complete final file contents"},
    {"path": "test_feature.py", "action": "write", "content": "complete final file contents"}
  ]
}
```

`write` replaces/creates the complete file inside the private worktree. `delete` may remove only an existing approved file. Duplicate paths, unapproved paths, no-op edits, malformed JSON, oversized output, and unsupported actions fail closed.

## Application integrity

Before Owner application, SAD verifies:

- Docker tests passed.
- Live/Git integrity stayed unchanged during isolated execution.
- Every changed path belongs to the approved scope.
- Each live file still matches the hash captured when the workspace was created.
- Each worktree file still matches the exact hash recorded after Docker verification.
- New files are still absent from the live project.
- Deleted files still match their recorded live source.

If any check fails, no live file is changed.

Application backs up all existing changed files before the first live write. If any write fails, SAD restores and verifies the entire original file set. Successful application records both base and applied manifests.

## Git boundary

Developer Workspace application does **not** run Git commands. It does not commit, push, fetch, rebase, merge, change branches, alter remotes, or use repository credentials.

Git publication remains a separate host/human-controlled workflow. This keeps a coding model from becoming its own reviewer and publisher.

## Mobile

A `full_role` paired phone may reach Developer Workspace routes, but the signed-in account keeps its normal SAD permissions. A Developer phone still cannot apply live code; Owner remains required.

`learning` paired phones are blocked from all Developer Workspace routes at the mobile gateway.

## Alpha limitations

- The Docker verifier currently runs the repository's Python `unittest` suite as the universal automated gate.
- There is no automatic package installation or internet dependency download inside the workspace.
- The local model must fit the approved source context and generated files within configured size limits.
- Git commits / pull requests are intentionally not part of automatic application.
- Human UAT on the deployment machine remains required before claiming the workspace as operational Alpha capability.
