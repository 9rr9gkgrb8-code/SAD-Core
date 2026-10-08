# MCP Python SDK 2.3 compatibility security gate

Status: PROPOSED; not yet implemented or tested. Do not upgrade runtime dependencies based on this document alone.

## Scope
- Confirm current SDK pin, transport adapters, tool registry and execution-time authorization path.
- Ensure tool visibility/list filtering is never used as the authorization boundary. Authorization must run on every tools/call.
- Bind authorization to principal, tool, canonical argument digest, effect class, expiry and single-use operation identity.
- Reserve operation identity durably before effect execution; replay must return original receipt or reject without a second side effect.
- Treat HeaderMismatch (-32020) and subsequent automatic list/retry as one logical operation, not a new approval.
- Reject mismatched Mcp-Param-* headers, invalid x-mcp-header schema annotations and untrusted tool names.
- Accept omitted _meta, params and experimental fields on legacy protocol connections without treating missing data as authorization.
- Bound SSE event size; reject oversized events safely.
- Verify behavior on protocol 2026-07-28 and supported legacy versions.

## Mandatory regression matrix
1. Hidden tool called directly: DENY without valid execution authorization.
2. Listed tool with revoked permission: DENY at execution.
3. HeaderMismatch then SDK retry with identical operation ID: at most one effect.
4. Concurrent duplicate requests: at most one effect, one durable receipt.
5. Crash between reservation and side effect: recover safely, never blind replay.
6. Changed argument digest or principal on retry: DENY.
7. Expired or consumed approval: DENY.
8. Missing _meta / params / experimental: parse safely, never elevate authority.
9. Invalid x-mcp-header annotation: fail registration or reject safely.
10. Oversized SSE event: bounded rejection without tool execution.
11. Existing legacy client journey: no authorization regression.
12. Tool listing middleware bypass attempt: execution permission remains enforced.

## Promotion gate
- Add automated tests at the actual gateway and durable-operation layer, not mocked policy-only tests.
- Run complete security and integration suites on the review branch.
- Record command, environment, commit SHA, pass/fail count and any untested scenarios.
- Obtain Owner approval before merge or SDK dependency upgrade.

References:
- https://newreleases.io/project/github/modelcontextprotocol/python-sdk/release/v2.3.0
- https://py.sdk.modelcontextprotocol.io/v2/advanced/header-parameters/
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/changelog.mdx
