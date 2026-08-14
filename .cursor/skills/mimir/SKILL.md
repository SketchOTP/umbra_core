---
name: mimir
description: Mimir V2 lifecycle — resolve/register, task begin, context compile, observe, validate, evidence, close
---

# Mimir V2 Workflow (UMBRA-CORE)

## Inputs

- Bound project identity from `.agent/PROJECT_PROFILE.md`.
- The current workspace root, repository state, and the task objective.
- Mimir availability as verified from the configured MCP/CLI adapter.

## Ordered steps

1. Resolve or register the bound project without guessing from a path.
2. Begin the task and retain the returned task ID and version.
3. Compile project context before overlapping work.
4. Observe only durable causal facts Git cannot prove.
5. Run allowlisted completion-critical validation.
6. Inspect evidence, then close with the latest task version.

## Outputs

- A retained task ID/version and honest validation/evidence status.
- `.agent/CURRENT.md` and append-only outcome records when repository work occurs.

## Failure handling

If Mimir is unavailable, record the exact blockage locally and do not claim
context, evidence, or close-out succeeded.

## Verification

Verify the resolved project identity, validation result, evidence inspection,
and final task status before reporting completion.

**Canonical rules:** `.cursor/rules/02-mimir-v2.mdc`, `AGENTS.md`  
**Project binding:** `.agent/PROJECT_PROFILE.md` (never guess from path)

Use when Mimir MCP is available (server key `mimir` / `user-mimir` in `~/.cursor/mcp.json`).

## Start (required for coding tasks)

1. If binding is absent/`UNBOUND`: `mimir_project_register` → write returned ID into `.agent/PROJECT_PROFILE.md`
2. Else: `mimir_project_resolve(project_id, workspace_root, client_id)`
3. `mimir_task_begin` — retain `task_id` and `version`
4. `mimir_context_compile(project_id, objective)` before overlapping work
5. Read `.agent/CURRENT.md` / recent directives as local continuity

## During

- `mimir_task_observe` only for durable causal facts Git cannot prove (decisions, constraints, root causes)
- Retain every returned version; always pass the latest version next
- Optional: `mimir_memory_query` / `mimir_memory_propose` / `mimir_memory_explain` — never replace the lifecycle

## End (required)

1. Run relevant verification (`mimir_validation_run` when allowlisted)
2. `mimir_task_evidence` — do not treat failed/timed-out checks as passing
3. `mimir_task_close` with latest version + verified changed files/tests/lessons
4. Append `.agent/OUTCOMES.md` and update `.agent/CURRENT.md`
5. Final response must include `Memory/MCP: session outcome recorded: yes` or `BLOCKED (<reason>)`

## If BLOCKED

- Report `BLOCKED: Mimir MCP unavailable: <reason>` (or the exact failed step)
- Fall back to `.agent/OUTCOMES.md` + `.agent/CURRENT.md`
- Never claim context, evidence, or close-out succeeded

## Never store

Secrets, credentials, `.env`, API keys, raw dumps, full files, private user data, noisy temporary details, unsupported high-confidence claims.
