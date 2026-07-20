# REPO_MAP.md

Concise navigation map for agents. Add entries as application code lands.

## Governance
- `.agent/PROJECT_GOAL.md` — product SoT (companion organism core; chemistry optional/non-gating)
- `.agent/PROJECT_PROFILE.md` — identity, Mimir binding `7777645d52a91b49`, program status
- `AGENTS.md` — agent governance (`CLAUDE.md` / `GEMINI.md` → symlink)
- `COMMANDMENTS_OF_THE_CODE.md` — ethical/execution principles
- `.cursor/rules/` — Cursor rules (incl. `04-umbra-architecture.mdc`)

## Program directives
- `docs/directives/UMBRA-D-000-prior-art-reproduction.md` — **active / blocks D-001**; **D-000A rejected**
- `docs/prior-art/SELECTION_LEDGER.md` — adopt/adapt/reference/reject ledger
- `docs/prior-art/micropsi2/` — Track 1 evidence (`NOTES.md`, `reproduce_modulators.py`); label=INDEPENDENT_MECHANISM_REPRODUCTION
- `docs/prior-art/homeostatic-rl/` — Track 2 HRRL formal repro + mechanism matrix
- `docs/evidence/d000-track2/` — Track 2 manifests, causal/ablation JSON, final verdict
- `docs/prior-art/hexis/` — Track 3 Hexis continuity/memory prior-art + independent_reproduction
- `docs/evidence/d000-track3/` — Track 3 seal, manifests, classifications, final verdict
- `docs/prior-art/aeros/` — Track 4 AEROS identity/governance prior-art + independent_reproduction
- `docs/evidence/d000-track4/` — Track 4 seal, manifests, classifications, final verdict
- `docs/prior-art/aera/` — Track 5 AERA causal learning prior-art + independent_reproduction
- `docs/evidence/d000-track5/` — Track 5 seal, manifests, causal/ablation JSON, final verdict
- `docs/prior-art/pepa/` — Track 6 PEPA persistent autonomy prior-art + independent_reproduction
- `docs/evidence/d000-track6/` — Track 6 seal, manifests, autonomy/history/ablation JSON, final verdict
- UMBRA-D-001 — **blocked** until D-000 closes

## Agent memory
- `.agent/CURRENT.md`, `DIRECTIVES.md`, `OUTCOMES.md`, `LEARNINGS.md`, `REPO_MAP.md`
- `.agent/RECORD.md` — operator-only (agents must not edit)

## Tooling
- MCP: `~/.cursor/mcp.json` (Mimir, Serena) — repo `.cursor/mcp.json` empty
- `.serena/project.yml` — Serena `UMBRA-CORE`
- Mimir SSH connection name `UMBRA-CORE` → `/home/sketch/Projects/UMBRA-CORE`

## Application / vendor
- No UMBRA organism kernel yet (D-001 blocked).
- Prior-art upstream clones under `docs/prior-art/*/upstream/` are local evaluation copies (gitignored); never treat as the companion.
