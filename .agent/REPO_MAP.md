# REPO_MAP.md

Concise navigation map for agents. Add entries as application code lands.

## Governance
- `.agent/PROJECT_GOAL.md` — product SoT (companion organism core; chemistry optional/non-gating)
- `.agent/PROJECT_PROFILE.md` — identity, Mimir binding `7777645d52a91b49`, program status (D-001 active)
- `AGENTS.md` — agent governance (`CLAUDE.md` / `GEMINI.md` → symlink)
- `COMMANDMENTS_OF_THE_CODE.md` — ethical/execution principles
- `.cursor/rules/` — Cursor rules (incl. `04-umbra-architecture.mdc`)

## Program directives
- `docs/directives/UMBRA-D-000-prior-art-reproduction.md` — **closed** via D-000S
- `docs/directives/UMBRA-D-001-invariant-companion-core.md` — **active / authorized** foundation implementation
- `docs/architecture/` — frozen reference architecture (D-000S)
- `docs/evidence/d000-synthesis/` — Track6 seal, mechanism ledger, conflicts, audits, tests
- `docs/prior-art/SELECTION_LEDGER.md` — adopt/adapt/reference/reject ledger
- `docs/prior-art/micropsi2/` — Track 1
- `docs/prior-art/homeostatic-rl/` — Track 2
- `docs/prior-art/hexis/` — Track 3
- `docs/prior-art/aeros/` — Track 4
- `docs/prior-art/aera/` — Track 5
- `docs/prior-art/pepa/` — Track 6
- `docs/evidence/d000-track{2..6}/` — per-track seals and results

## Agent memory
- `.agent/CURRENT.md`, `DIRECTIVES.md`, `OUTCOMES.md`, `LEARNINGS.md`, `REPO_MAP.md`
- `.agent/RECORD.md` — operator-only (agents must not edit)

## Tooling
- MCP: `~/.cursor/mcp.json` (Mimir, Serena) — repo `.cursor/mcp.json` empty
- `.serena/project.yml` — Serena `UMBRA-CORE`
- Mimir SSH connection name `UMBRA-CORE` → `/home/sketch/Projects/UMBRA-CORE`

## Application / vendor
- No organism kernel tree yet (`src/` / `umbra/` / `kernel/` absent) — D-001 may create clean-room foundation only.
- Prior-art upstream clones under `docs/prior-art/*/upstream/` are local evaluation copies (gitignored); never treat as the companion.
