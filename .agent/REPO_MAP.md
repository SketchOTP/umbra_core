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
- D-006 experiment harness: `experiments/d006/run_experiment.py` (paired-seed ProcessPool over frozen matrix; drives SocialEngine directly with synthetic cues + `response_policy_for_history`; asserts gates 1-9 numerically; probes: `_two_partner_separation` gate2, `_single_failure_preserved` gate4, `_viability_ok` gate6 survival-critical only, `_c3_no_leak`/`_governance_cooldown_denies`/`_replay_determinism`/`_event_authority_map` gate9/evidence), `experiments/d006/run_closeout.py` (pytest dump + interim verdict `UMBRA_D006_EXPERIMENT_GATES_1_9_PASS` + `evidence-hashes.json`)
- D-006 evidence (Task 12, gates 1-9 sealed; Gate 12 perf → Task 13): `docs/evidence/d006/` — experiment-summary + recognition/contingency/history/reliability/satiation/absence/routine/governance/manipulation/replay/event-authority-results.json, final-verdict.md, evidence-hashes.json, test-results.txt
- D-006 tests: `tests/test_d006.py` (Task 2–8: merge/split provenance, swap detection, reliability revision, soft proposals, shared routine promotion; Task 11: full directive+design §8 minimum-test-list coverage — satiation decline, absence non-escalation/non-frequency/non-viability-damage/non-punishment, different-histories behavior, `pytest.mark.skip`'d pre-soak Gate 12 placeholder for Task 13)
- D-006 social engine: `umbra_core/social/` — `engine.py`: `SocialEngine`/`PartnerHypothesis`/`ContingencyCell`/`PendingInteraction`/`RoutineHandle`/`ResponseClass`/`condition_to_social_config` (C0–C9 complete: C1 familiarity-only, C2 pooled partner, C3 baseline/no production affection, C4 no persist+reset, C5 no satiation, C6 no recognition, C7 random actions, C8 scripted routine, C9 randomized timing; recognition, derived satiation/expected_response_latency; `create_pending`/`classify_response`/`observe_outcome`/`resolve_pending` atomic commit; `resume_pending`/`reconstruct_pending` restart+fail-closed; Task 6: merge/split provenance, swap detection, reliability revision; Task 8: routine promotion; Task 9: `experiments/d006/affection_controller.py` C3-only `AffectionController`; Task 10: `accepted_state()` for birth/snapshot replay equality (excludes non-deterministic Governance-sourced `execution_id`); `MAX_ROUTINE_HANDLES` cap + `_prune_routine_handles()` FIFO eviction, `_prune_hypotheses()` now interrupts routines of evicted hypotheses so `routine_handles` stays bounded across the full hypothesis lifetime, not just the active set)
- D-006 Task 10 (persistence/restart/replay, Gate 11): snapshot already carried `social` via `Organism.authoritative_state()`/`load_organism()` (prior tasks) — `umbra_core/runtime.py`'s `resimulate()` now also compares `social_accepted`; tests: `tests/test_d006.py::test_restart_preserves_partner_models`, `test_birth_and_snapshot_replay_match`, `test_partner_and_routine_counts_are_bounded`, `test_prior_seals_validate` (adds d005 seal), `test_prior_regressions_pass`, `test_no_deferred_modules_added`
- D-006 atomic commit: `umbra_core/persistence.py` — `Store.atomic_social_outcome` + `social_evidence_links` + `social_hypothesis_provenance_links`; `umbra_core/memory/engine.py` — `finalize_social_episode`/`attach_episode`/`promote_social_routine`/`select_social_routine`/`SocialRoutineSpec`; `umbra_core/events.py` — social lifecycle + `social_partner_swap_detected` + `social_routine_promoted`/`social_routine_deactivated` AUTHORITATIVE
- `umbra_core/perception.py` — habitat + partner cue membrane (`partner_cues` in policy_view); identity-signature noise floor `_PARTNER_IDENTITY_NOISE_SIGMA=0.14` < spatial noise so distinct partners stay separable (Task 12 Critical fix)
- `umbra_core/embodiment.py` — habitat plant + `SIGNAL_*` + `PartnerEntity`/`apply_social_history`/`hidden_partner_truth_for_eval`; `PartnerTrueCues.for_history` uses antipodal per-index identity basis (`_identity_offsets`, noise-free inter-partner cue distance ~0.69; ambiguous H9 tiny amplitude) — Task 12 Critical fix, frozen threshold unchanged
- D-006 organism recognition (real-path Gate 3): `experiments/d006/run_experiment.py::_organism_recognition` + `tests/test_d006.py::test_organism_h8_distinct_partners_do_not_silently_merge`/`test_organism_h9_ambiguous_partners_are_not_split_into_distinct_identities`

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
