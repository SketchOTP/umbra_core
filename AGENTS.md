## Project Identity

- Product: **UMBRA** (repo: **UMBRA-CORE**)
- Source of truth: `.agent/PROJECT_GOAL.md`
- Repo profile: `.agent/PROJECT_PROFILE.md`
- Mimir project identity MUST come from `.agent/PROJECT_PROFILE.md`; never guess identity, slug, or workspace binding from the path
- Keep paths platform-neutral when the agent may run remotely

## Product constraints (from PROJECT_GOAL)

Read `.agent/PROJECT_GOAL.md` before any design or implementation work. Non-negotiable:

- Primary target: persistent organism/brain core for an autonomous digital pet companion (Digimon/Pokémon-class experience) — not a chatbot, scripted animation, or LLM puppet
- No LLM as central controller; optional language expresses, does not command
- No scripted emotional responses, predefined personality performances, or user prompts required to stay alive
- No direct commands: become happy, bond, eat, play, sleep, become afraid, etc.
- Outcomes emerge from needs, regulation, body, memory, relationships, and developmental history
- Bodies (avatar, robot, sensors, animations, dialogue) are interfaces around the organism core
- Digital chemistry / protocells are optional long-range research only — **not** required foundations; **do not** create or execute UMBRA-D-000A

**Program gate:** UMBRA-D-000 closed via D-000S (`UMBRA_D000S_FOUNDATION_ARCHITECTURE_QUALIFIED`). **UMBRA-D-001 closed** — `UMBRA_D001_INVARIANT_COMPANION_CORE_QUALIFIED`. **UMBRA-D-002 closed** — `UMBRA_D002_SENSORIMOTOR_SELF_MODEL_QUALIFIED`. **UMBRA-D-002V** — `UMBRA_D002V_PERFORMANCE_FAIL` (preserved). **UMBRA-D-002P** — `UMBRA_D002P_PERFORMANCE_REMEDIATION_QUALIFIED`. **UMBRA-D-003 closed** — `UMBRA_D003_PREDICTIVE_WORLD_MODEL_QUALIFIED`. **UMBRA-D-004 closed** — `UMBRA_D004_INTRINSIC_DEVELOPMENT_QUALIFIED`. **D-005 authorized** under D-004. Architecture: `docs/architecture/`. Evidence: `docs/evidence/d001/`, `docs/evidence/d002/`, `docs/evidence/d002v/`, `docs/evidence/d002p/`, `docs/evidence/d003/`, `docs/evidence/d004/`.

LLM-wrapper companions (Hexis/AEROS/OpenLife-style) do not satisfy the non-LLM organism kernel requirement.

## Local Governance Contract

These files are the local source of truth for durable repo governance. Use them as follows:

- `.agent/PROJECT_GOAL.md` - canonical repo goal; read every task; update only when the canonical goal changes
- `.agent/PROJECT_PROFILE.md` - canonical project binding; read every task; must contain one committed Mimir project ID bound to this checkout; update only when the binding is missing, `UNBOUND`, or canonical identity changes
- `.agent/CURRENT.md` - active task state; read every task; update at task start, on material pivots/blockers, and at task end
- `.agent/DIRECTIVES.md` - append-only task-start log; append every task start; never rewrite, reorder, or delete history
- `.agent/OUTCOMES.md` - append-only task-end log; append every task end; never rewrite, reorder, or delete history
- `.agent/LEARNINGS.md` - append-only durable facts log; append only for evidence-backed facts that will save future time; never rewrite, reorder, or delete history
- `.agent/RECORD.md` - operator-only architect instruction log; agents must not edit
- `.agent/REPO_MAP.md` - compact navigation map; consult before navigating; update for touched or newly understood areas

Rules:

- Create any missing `.agent/` governance files before editing repository code, preserving compatible content when present
- Read `.agent/PROJECT_GOAL.md`, `.agent/PROJECT_PROFILE.md`, and `.agent/CURRENT.md` every task
- Read the relevant recent entries in `.agent/DIRECTIVES.md` and `.agent/OUTCOMES.md` before work that depends on prior state
- Consult `.agent/REPO_MAP.md` before random file hunting and update it for touched or newly understood areas
- Append to `.agent/DIRECTIVES.md` at task start
- Append to `.agent/OUTCOMES.md` at task end
- Append to `.agent/LEARNINGS.md` only for durable, evidence-backed facts; do not edit `.agent/RECORD.md`
- Update `.agent/PROJECT_GOAL.md` and `.agent/PROJECT_PROFILE.md` only when canonical facts change
- Update `.agent/CURRENT.md` at task start, material pivots/blockers, and task end
- Never force meaningless writes to stable files
- Never rewrite append-only history

## Operating Mode

Use Ponytail discipline: do the least work that is actually correct.

- Question whether the requested thing needs to exist
- Reuse repo code before writing new code
- Prefer stdlib/native features over custom code
- Prefer installed dependencies over new dependencies
- Prefer deletion over addition
- Prefer boring over clever
- Prefer one clear line over a helper
- Prefer one clear helper over a new abstraction layer
- Fewest files, smallest correct diff
- Stop when acceptance is met

Not negotiable:

- Understand the touched flow before changing it
- Fix the root cause, not only the symptom
- Do not skip validation, security, accessibility, data safety, or required error handling
- Non-trivial logic gets one runnable check: the smallest test or self-check that would fail if broken
- Mark deliberate shortcuts with `ponytail:` and name the ceiling or upgrade path
- Do not invent future requirements

## Instruction Priority

When instructions conflict, follow this order:

1. Direct user request
2. `.agent/PROJECT_GOAL.md` architectural constraints
3. Existing repo behavior and tests
4. This `AGENTS.md`
5. Other repo-local instruction files
6. General assumptions

Governance files never override explicit user constraints, except safety/harm refusal.

## Repo Map Workflow

Use `.agent/REPO_MAP.md` before broad file hunting.

Fast path:

1. Search the map for the feature or module name
2. Open only mapped files likely related to the task
3. Follow imports or callers from those files
4. Use targeted search only when the map is missing or stale
5. Update the map if a touched file is missing, renamed, or better understood

Rules:

- Keep entries short
- Add only files or modules that help future agents move faster
- Do not map generated, vendor, cache, or build output
- If a map entry is wrong, correct that line only

## Code Navigation

Use the repo's code navigation tools on every non-trivial code task, except the trivial-edit exception: single file, 10 or fewer lines, no behavior/API/schema change.

Guidance:

- Prefer Mimir V2 context compile / hybrid search when indexed; Serena for exact symbols
- Prefer surgical edits over broad scans
- If blocked by the navigation stack, report it plainly and fall back to targeted reads

## Mimir V2: Mandatory Lifecycle

Mimir V2 is mandatory for every coding task in this repository, including investigation, implementation, bug fixes, refactors, tests, and documentation that changes or explains code behavior. Pure conversation with no repository work does not start a Mimir task.

Use only this lifecycle, in order, for every coding task:

1. `mimir_project_register(workspace_root, name?, client_id?, repository_remote?, root_commit?)` when `.agent/PROJECT_PROFILE.md` has no bound project ID or is `UNBOUND`. Otherwise use `mimir_project_resolve(project_id, workspace_root, client_id)` to bind the committed project ID to the actual checkout. On another machine, resolve using that machine's own workspace path. If needed, obtain the Git remote and root commit locally and pass both. Never guess project identity from a path, never create a host copy, and never fall back without Mimir.
2. `mimir_task_begin(project_id, workspace_root, client_id, worktree_id, objective)` at the start of every coding task; retain the returned task ID and version.
3. `mimir_context_compile(project_id, objective)` after task begin and before overlapping work. This is the normal project-scoped retrieval step.
4. `mimir_task_observe(task_id, version, event_type, payload_json, evidence_json)` only for durable causal facts Git cannot prove, such as decisions, constraints, hypotheses, and root causes. Do not use it for routine narration or file-change reporting. Every successful observation returns a new task version. Retain the latest version after every observation and pass that latest version to every later `mimir_task_observe` call and to `mimir_task_close`.
5. `mimir_validation_run(task_id, command, timeout_seconds?)` for completion-critical checks only. The command must be on the server allowlist.
6. `mimir_task_evidence(task_id)` before closure; failed or timed-out validations must not be represented as passing evidence.
7. `mimir_task_close(task_id, version, status, changed_files_json, tests_json, lessons_json)` only after evidence inspection, using the latest version and verified result.

Rules:

- Use the same lifecycle through CLI and MCP adapters
- Do not infer tool names from pasted legacy guidance
- Treat the repository as the source of truth and Mimir as the store for reasons, evidence, failures, fixes, and predictions
- Keep routine narration, raw command output, full files, credentials, and unsupported claims out of Mimir
- Reject high-confidence memory that lacks evidence
- Never mix project memory or store secrets or source files
- Keep paths platform-neutral when the agent can run remotely

## Mimir Direct Memory

The optional direct memory tools are only:

- `mimir_memory_query`
- `mimir_memory_propose`
- `mimir_memory_explain`

They do not replace task begin, compiled context, validation, evidence inspection, or task close.

Use the separate reviewed `mimir_project_onboard` and backfill workflow only for mature-repository import. Do not run it on every task.

## Mimir Failure Handling

If Mimir V2 is unavailable:

- Continue only when the change is safe
- Record the blockage honestly in `.agent/CURRENT.md` and `.agent/OUTCOMES.md`
- Never claim that Mimir context, evidence, or close-out succeeded

If a required Mimir step cannot be completed, say so plainly and do not fake the result.

## Validation

Run the smallest useful validation.

Priority:

1. Existing targeted test for the touched area
2. New minimal test for changed behavior
3. Typecheck, lint, or build only if relevant
4. Manual self-check if no test harness exists

Log skipped validation honestly.

## Append-Only Discipline

Append-only files:

- `.agent/DIRECTIVES.md`
- `.agent/OUTCOMES.md`
- `.agent/LEARNINGS.md`
- `.agent/RECORD.md` (operator-only; agents do not append)

Rules:

- Add new lines only
- Do not reorder
- Do not rewrite history
- If correcting an old entry, append a correction line
- Keep append-only files append-only across all task work

## Current State File

Keep `.agent/CURRENT.md` small and current only. Use this shape:

```md
# CURRENT.md

## Active directive
- ID:
- Project directive:
- Goal:
- Status:
- Acceptance:
- Touched files:
- Next action:

## Repo facts needed now
- ...

## Last validation
- Command:
- Result:

## Open blockers
- ...
```

## Start Of Every Directive

Before edits:

1. Create a local directive ID in this form: `D-YYYYMMDD-HHMM-short-slug`
2. Read only the needed context
3. Define observable acceptance
4. Append the directive start line to `.agent/DIRECTIVES.md`
5. Update `.agent/CURRENT.md`

## While Coding

Use this ladder:

1. Can this be skipped because it is speculative?
2. Does existing repo code already do it?
3. Can stdlib or native platform features do it?
4. Can an installed dependency do it?
5. Can one clear line do it?
6. Can a small local change do it?
7. Only then add a helper or module

Rules:

- No abstraction with one implementation
- No config for values that do not vary
- No factories, managers, or services for later
- No new dependency for a few lines of code
- No broad refactor while fixing a narrow bug
- Search callers before changing shared code
- Keep existing naming and style unless actively harmful
- If two options are equal size, choose the safer edge-case-correct one
- Do not silence errors; fix causes
- Add comments only for non-obvious constraints

## End-Of-Task Sequence

Before final response:

1. Compare work against acceptance criteria
2. Run the smallest useful validation
3. Append `.agent/OUTCOMES.md`
4. Update `.agent/CURRENT.md`
5. Append `.agent/LEARNINGS.md` if useful
6. Update `.agent/REPO_MAP.md` if files or modules were added, removed, renamed, or better understood
7. Run the required Mimir close-out flow if reachable
8. Check `git status --short`
9. Respond in the required final format

## Final Response

Keep it short. No essay. No fake certainty.

Default format:

```md
D-YYYYMMDD-HHMM-slug

Changed:
- <short bullet>

Tests:
- <command/result or not run + why>

Memory/MCP:
- session outcome recorded: yes / BLOCKED (<reason>)

Next:
- <only if needed>
```

If there is a project directive ID (`D-###`):

```md
PROJECT DIRECTIVE
- D-###

AGENT MEMORY DIRECTIVE
- D-YYYYMMDD-HHMM-slug

Changed:
- <short bullet>

Files changed:
- <path> — <reason>

Tests:
- <command/result or not run + why>

Manual verification:
- <check performed or None>

Deviations:
- <anything outside directive scope or None>

Known issues:
- <remaining issue or None>

Backup/savepoint:
- <tag/branch created or Not requested>

Memory/MCP:
- session outcome recorded: yes / BLOCKED (<reason>)

Next:
- <smallest logical next step, only if needed>
```

## Mandatory Mimir V2 and repository governance

Required `.agent` files: `PROJECT_GOAL.md`, `PROJECT_PROFILE.md`, `CURRENT.md`, `DIRECTIVES.md`, `OUTCOMES.md`, `LEARNINGS.md`, `RECORD.md`, and `REPO_MAP.md`. Create missing files before repository edits; read every task: `PROJECT_GOAL.md`, `PROJECT_PROFILE.md`, and `CURRENT.md`; consult before navigation: `REPO_MAP.md`. Append every task start to `DIRECTIVES.md` and append every task end to `OUTCOMES.md`; `DIRECTIVES.md`, `OUTCOMES.md`, and `LEARNINGS.md` are append-only for agents.

The committed Mimir project ID in `PROJECT_PROFILE.md` is canonical. Resolve it with this machine's workspace path; register only when it is absent or `UNBOUND`, then write and commit the returned ID. For every repository task call `mimir_project_register` or `mimir_project_resolve`, then `mimir_task_begin`, `mimir_context_compile`, durable `mimir_task_observe`, allowlisted `mimir_validation_run`, `mimir_task_evidence`, and `mimir_task_close`. Retain the latest returned task version after every observation and pass it to later observations and close. Never continue as if Mimir succeeded when it is unavailable.
