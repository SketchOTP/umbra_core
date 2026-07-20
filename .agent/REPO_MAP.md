# REPO_MAP.md

Concise navigation map for agents. Add entries as application code lands.

## Governance
- `.agent/PROJECT_GOAL.md` — product and architecture source of truth (digital lifeform end goal)
- `.agent/PROJECT_PROFILE.md` — repo identity, Mimir binding, program status, constraints
- `AGENTS.md` — agent governance and Mimir V2 lifecycle (`CLAUDE.md` / `GEMINI.md` symlink here)
- `COMMANDMENTS_OF_THE_CODE.md` — ethical and execution principles for coding agents
- `.cursor/rules/` — Cursor rule adapters (governance, memory, Mimir, Serena, UMBRA architecture, directives)

## Program directives
- `docs/directives/UMBRA-D-000-prior-art-reproduction.md` — **active / blocks D-001**; prior-art audit + foundation selection
- `docs/prior-art/` — reproduction/audit evidence + `SELECTION_LEDGER.md`
- UMBRA-D-001 — **not started**; revise only after D-000 closes

## Agent memory
- `.agent/CURRENT.md` — mutable working state
- `.agent/DIRECTIVES.md` — append-only task-start log
- `.agent/OUTCOMES.md` — append-only task-end log
- `.agent/LEARNINGS.md` — append-only repo-specific lessons
- `.agent/REPO_MAP.md` — this file
- `.agent/RECORD.md` — operator-only architect instruction log (agents must not edit)

## Tooling
- MCP: configure globally in `~/.cursor/mcp.json` (Mimir, Serena, GitHub) — do not duplicate in-repo
- `.serena/project.yml` — Serena project name `UMBRA-CORE`
- `.cursor/skills/mimir/SKILL.md` — Mimir V2 session workflow skill

## Application / vendor code
- No UMBRA organism kernel yet (blocked on D-000).
- Prior-art checkouts (when added) should live under an explicit path recorded in `docs/prior-art/` — never silently become “the creature.”
