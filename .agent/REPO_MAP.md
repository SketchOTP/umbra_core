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
- `docs/directives/UMBRA-D-001-invariant-companion-core.md` — **closed** `UMBRA_D001_INVARIANT_COMPANION_CORE_QUALIFIED`
- `docs/architecture/` — frozen reference architecture (D-000S)
- `docs/evidence/d000-synthesis/` — Track6 seal, mechanism ledger, conflicts, audits, tests
- `docs/evidence/d001/` — D-001 tests, experiments C0–C9, soak Run A/B, final verdict
- `docs/prior-art/SELECTION_LEDGER.md` — adopt/adapt/reference/reject ledger

## Organism kernel (D-001 + D-002 + D-003)
- `umbra_core/self_model/` — sensorimotor body schema, prediction, attribution, adaptation
  - `engine.py` — BodySchema / SelfModel / Attribution
- `umbra_core/world_model/` — persistent entities, transitions, affordances, revision, planning
  - `engine.py` — WorldModel / TransitionModel / AffordanceBelief / PlanTrace
- D-002 evidence: `docs/evidence/d002/`
- D-002 experiments: `experiments/d002/`
- D-002 tests: `tests/test_d002.py`
- D-002V evidence: `docs/evidence/d002v/` (VmRSS method freeze, soak, event authority, replay)
- D-002V experiments: `experiments/d002v/`
- D-002V tests: `tests/test_d002v.py`
- D-002P evidence: `docs/evidence/d002p/` (memory audit, RUNTIME_READY soak, remediation)
- D-002P experiments: `experiments/d002p/`
- D-002P tests: `tests/test_d002p.py`
- D-003 evidence: `docs/evidence/d003/` (prediction, affordance, persistence, revision, planning, soak)
- D-003 experiments: `experiments/d003/`
- D-003 tests: `tests/test_d003.py`
- `umbra_core/util.py` — `current_rss_mib` (VmRSS), `ols_slope`, `BoundedRing`
- `umbra_core/events.py` — `SELF_MODEL_EVENT_AUTHORITY`; `world_model_supersede`; `runtime_ready`
- `umbra_core/runtime.py` — `emit_runtime_ready`; world_intervention I0–I10; world model loop
- `umbra_core/persistence.py` — `prune_snapshots(keep=2)`
- `umbra_core/embodiment.py` — habitat plant + `apply_world_intervention`

## Organism kernel (D-001)
- `umbra_core/` — clean-room invariant companion core (stdlib + SQLite)
  - `identity.py` — constitutional birth / commitment
  - `physiology.py` — energy/fatigue/integrity/stimulation
  - `perception.py` — uncertain observation membrane
  - `embodiment.py` — 2D habitat + body + primitives
  - `arbitration.py` — vector scoring, hysteresis, recovery
  - `governance.py` — admit → execute → verify
  - `persistence.py` — SQLite WAL ledger + snapshots
  - `events.py` — authoritative vs diagnostic retention policy
  - `runtime.py` — continuous loop; create/load organism
- `tests/test_d001.py` — required D-001 unit tests (33)
- `tests/test_d001c_closeout.py` — retention-v1 / closeout contracts
- `experiments/d001/run_experiment.py` — C0–C9 + recovery trials
- `experiments/d001/run_performance.py` — 100k ticks + soak sample
- `experiments/d001/run_soak_b.py` — Run B 6h soak (retention v1)
- `experiments/d001/closeout_run_a.py` / `closeout_run_b.py` — Gate9 closeout validators
- `.soak/` — local soak DBs (gitignored)

## Agent memory
- `.agent/CURRENT.md`, `DIRECTIVES.md`, `OUTCOMES.md`, `LEARNINGS.md`, `REPO_MAP.md`
- `.agent/RECORD.md` — operator-only (agents must not edit)

## Tooling
- MCP: `~/.cursor/mcp.json` (Mimir, Serena) — repo `.cursor/mcp.json` empty
- `.serena/project.yml` — Serena `UMBRA-CORE`
- Mimir SSH connection name `UMBRA-CORE` → `/home/sketch/Projects/UMBRA-CORE`
