# REPO_MAP.md

Concise navigation map for agents. Add entries as application code lands.

## Governance
- `.agent/PROJECT_GOAL.md` — product SoT (companion organism core; chemistry optional/non-gating)
- `.agent/PROJECT_PROFILE.md` — identity, Mimir binding `7777645d52a91b49`, program status (D-006 active)
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

## Organism kernel (D-001 + D-002 + D-003 + D-004 + D-005)
- `umbra_core/self_model/` — sensorimotor body schema, prediction, attribution, adaptation
  - `engine.py` — BodySchema / SelfModel / Attribution
- `umbra_core/world_model/` — persistent entities, transitions, affordances, revision, planning
  - `engine.py` — WorldModel / TransitionModel / AffordanceBelief / PlanTrace
- `umbra_core/development/` — intrinsic practice goals, competence/learning-progress, play, skills
  - `engine.py` — DevelopmentEngine / PracticeGoal / SkillRecord / GoalStatus
- `umbra_core/memory/` — selective episodic memory, offline consolidation, semantic/procedural
  - `engine.py` — MemoryEngine / Episode / SemanticBelief / ProceduralMemory
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
- D-004 evidence: `docs/evidence/d004/`
- D-004 experiments: `experiments/d004/`
- D-004 tests: `tests/test_d004.py`
- D-005 evidence: `docs/evidence/d005/`
- D-005 experiments: `experiments/d005/`
- D-005 tests: `tests/test_d005.py`
- D-006 design: `docs/superpowers/specs/2026-07-22-umbra-d006-social-contingency-design.md`
- D-006 directive: `docs/directives/UMBRA-D-006-social-contingency.md`
- D-006 preregistration: `experiments/d006/thresholds.json`, `experiments/d006/experiment-matrix.json`
- D-006 evidence (pending): `docs/evidence/d006/`
- D-006 tests: `tests/test_d006.py` (Task 2: signals; Task 3: partner entities + noisy cues)
- D-006 social engine (pending): `umbra_core/social/`
- `umbra_core/perception.py` — habitat + partner cue membrane (`partner_cues` in policy_view)
- `umbra_core/embodiment.py` — habitat plant + `SIGNAL_*` + `PartnerEntity`/`apply_social_history`/`hidden_partner_truth_for_eval`

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
