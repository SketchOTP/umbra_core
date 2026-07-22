# PROJECT_PROFILE.md

## Identity
- Product: UMBRA — persistent organism/brain core for an autonomous digital pet companion
- Repo: UMBRA-CORE
- Mimir slug: umbra-core
- Serena project: UMBRA-CORE (`.serena/project.yml`)
- Source of truth: `.agent/PROJECT_GOAL.md`
- Github repo: TBD
- Github username: SketchOTP
- Github email: sketchotp@gmail.com

## What we are building
The persistent internal life of a believable digital companion (Digimon/Pokémon-class experience): identity, homeostasis, endogenous action, learning, development, memory, habits, relationships, temperament-from-history, embodied expression, and body transfer — without an LLM as the central controller and without scripted personality performance.

See `.agent/PROJECT_GOAL.md` for the full end-goal statement and success criteria.

## Architectural constraints (from PROJECT_GOAL)
- No LLM as central controller; optional language expresses, does not command
- No scripted emotional responses or predefined personality performances
- No user prompts required to remain active
- No direct commands: become happy, bond, eat, play, sleep, become afraid, etc.
- Behavior emerges from needs, regulation, body, memory, relationships, developmental history
- Must remain autonomous when no observer is present
- Bodies (avatar, robot, sensors, animations, dialogue) are interfaces around the organism core
- Digital chemistry / protocell research is optional and non-gating

## Program status
- **UMBRA-D-007 in progress** — lived individuality / history-shaped temperament (Mimir `4bcd3653644446979291482242536ddc`)
- **UMBRA-D-006 closed** — `UMBRA_D006_SOCIAL_CONTINGENCY_QUALIFIED` (Task 13 perf seal: 100k + 2h RUNTIME_READY VmRSS soak; zero-skip suite)
- **D-007 authorized** under `UMBRA_D006_SOCIAL_CONTINGENCY_QUALIFIED`
- **UMBRA-D-005 closed** — `UMBRA_D005_MEMORY_CONSOLIDATION_QUALIFIED`
- **UMBRA-D-004 closed** — `UMBRA_D004_INTRINSIC_DEVELOPMENT_QUALIFIED`
- **UMBRA-D-003 closed** — `UMBRA_D003_PREDICTIVE_WORLD_MODEL_QUALIFIED`
- **UMBRA-D-002P** — `UMBRA_D002P_PERFORMANCE_REMEDIATION_QUALIFIED`
- **UMBRA-D-002V** — `UMBRA_D002V_PERFORMANCE_FAIL` (preserved; not waived)
- **UMBRA-D-002** — `UMBRA_D002_SENSORIMOTOR_SELF_MODEL_QUALIFIED` (performance seal via D-002P)
- **UMBRA-D-001 closed** — `UMBRA_D001_INVARIANT_COMPANION_CORE_QUALIFIED` (Run B 6h soak)
- **UMBRA-D-000 closed** via **UMBRA-D-000S** — `UMBRA_D000S_FOUNDATION_ARCHITECTURE_QUALIFIED`
- **UMBRA-D-000A rejected** — do not create or execute artificial-life/protocell substrate reframes
- Architecture freeze: `docs/architecture/`
- Synthesis evidence: `docs/evidence/d000-synthesis/`
- D-001 evidence: `docs/evidence/d001/`
- D-002 evidence: `docs/evidence/d002/`
- D-002V evidence: `docs/evidence/d002v/`
- D-002P evidence: `docs/evidence/d002p/` (QUALIFIED)
- D-003 evidence: `docs/evidence/d003/` (QUALIFIED)
- D-004 evidence: `docs/evidence/d004/` (QUALIFIED)
- D-005 evidence: `docs/evidence/d005/` (QUALIFIED)
- D-006 evidence: `docs/evidence/d006/` (QUALIFIED)
- D-006 preregistration: `experiments/d006/thresholds.json`, `experiments/d006/experiment-matrix.json`
- D-006 directive: `docs/directives/UMBRA-D-006-social-contingency.md`
- D-006 design: `docs/superpowers/specs/2026-07-22-umbra-d006-social-contingency-design.md`
- Prior-art lab notebook: `docs/prior-art/` (Tracks 1–6 complete; Soar/Hyperon not required)
- Stance: informed reuse for the **companion organism core**; chemistry/protocell deferred

## Stack
- Target platform: Linux
- Persistence: SQLite WAL event/state authority (`HYBRID_PRIMARY`); optional Postgres scale tier
- Core loop: deterministic non-LLM (see architecture freeze)
- Organism kernel: D-001 QUALIFIED (`umbra_core/`); D-002 QUALIFIED self-model (`umbra_core/self_model/`); D-003 QUALIFIED world model (`umbra_core/world_model/`); D-004 QUALIFIED development (`umbra_core/development/`); D-005 QUALIFIED memory (`umbra_core/memory/`); D-006 QUALIFIED social (`umbra_core/social/`); D-007 individuality (`umbra_core/individuality/`) in progress
- Agent/tooling docs: Markdown, Cursor rules, Mimir V2, Serena

## Common commands
- Tests / build / CLI: stand up per-project as D-000 reproductions require
- Code navigation: Mimir V2 + Serena when code exists

<!-- MIMIR_PROJECT_BINDING_START -->
## Mimir binding
- Mimir project ID: 7777645d52a91b49
- Project name: UMBRA-CORE
- On every machine, call mimir_project_resolve with this ID and that machine's workspace path.
- Register only when this binding is absent; never create a host path or map a drive.
<!-- MIMIR_PROJECT_BINDING_END -->
