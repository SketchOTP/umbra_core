# UMBRA-D-009: Persistent Digital Habitat and Autonomous Environmental Agency

**Status:** IN PROGRESS  
**Agent Memory Directive:** `D-20260723-umbra-d009-persistent-habitat-agency`  
**Starting Commit:** `b230790df1cab1580ea650a348eb0576e2e4599e`  
**D-008 Seal Commit:** `ce777adda2d38daa3037411c5a88688c51cb3122`  
**Prerequisite Verdict:** `UMBRA_D008_COHERENT_DIGITAL_EMBODIMENT_QUALIFIED`  
**Design Status:** `79a00f2` (amendments A1–A6 on `da60f20`)  
**Mimir Project:** `7777645d52a91b49`  
**Mimir Task:** `06b5b59709864e11bddb8c1da56dd66e`

Canonical operator text for this directive is the project directive issued 2026-07-23. This file is the in-repo copy for navigation and seal hashing. Where the frozen design spec (`docs/superpowers/specs/2026-07-23-umbra-d009-persistent-habitat-agency-design.md`) amends operator text, the design spec governs implementation.

## Objective

Implement and validate a persistent digital habitat with governed environmental affordances. UMBRA must autonomously explore zones, inspect objects, manipulate supported objects, activate environmental affordances, develop non-authored environmental preferences and routines, leave inspectable habitat history, and continue acting when no user is present — through the qualified D-001…D-008 organism architecture, not scripted pet-game behavior.

## Authorized claim

> UMBRA demonstrates bounded autonomous environmental agency in a persistent digital habitat, including governed object interaction, history-dependent habitat use, learned environmental routines, and continuity of organism and habitat state across restart and replay.

Not authorized: consciousness; sentience; subjective experience; genuine emotion; biological life; unrestricted agency; human-equivalent planning; complete companion capability; physical-world competence; general-purpose object manipulation.

## Packaging

```text
umbra_core/habitat/
umbra_core/habitat_affordances/
umbra_core/embodiment_adapters/   # validate_manipulation; D-009 profile versions
umbra_core/arbitration.py         # MANIPULATE candidates (address-only)
umbra_core/governance.py
umbra_core/runtime.py
umbra_core/persistence.py
umbra_core/expression/habitat_read_model.py
experiments/d009/
tests/test_d009.py
docs/evidence/d009/
```

## Forbidden

LLM-as-controller; scripted virtual-pet game; animation scheduler; dialogue system; engagement grind; chemistry/protocell prerequisites; camera/microphone/robotics prerequisites; level-editor or decorative-room substitute; UI as habitat truth; WorldModel as habitat truth; direct commands to play, sleep, explore, collect, or organize; inventing personality or goal scripts in habitat objects; `BODY_CAPABILITY_UNSUPPORTED` (use `UNSUPPORTED_BODY_CAPABILITY`).

## Architecture (own-and-delegate)

**Locked decisions (design A1–A6):**

1. `HabitatEngine` is sole habitat authority, mutator, and event source. `Embodiment.habitat` is a read-only compatibility projection rebuilt from committed HabitatEngine state.
2. Continuous 2D plane + non-overlapping axis-aligned zone overlays; zone membership derived from position.
3. `HabitatObject` is the sole spatial entity model; `HabitatFeature` is projection vocabulary only.
4. `HELD_BY` location mode lives only in HabitatEngine; production `hold_slot_count = 1`.
5. `AffordanceDefinition` + `HabitatAffordanceEngine` = world truth; D-003 WorldModel = uncertain expectations for proposal scoring only.
6. `MANIPULATE` is a candidate type on the existing scorer — no EnvironmentalAgency controller.
7. Split packages `umbra_core/habitat/` and `umbra_core/habitat_affordances/`; runtime orchestrates only.
8. AffordanceEngine returns immutable validation/effect plans; never mutates habitat.
9. Habitat mutation, habitat events, approved organism effects, and VerifiedOutcome commit atomically or not at all.
10. Habitat payloads/apply in `umbra_core/habitat/events.py`; registered through existing AUTHORITATIVE ledger.
11. Adapter `validate_manipulation` only; runtime coordinates commit.
12. Exactly-once execution: one terminal VerifiedOutcome per `execution_id`; PREPARED → COMMITTED_SUCCESS | COMMITTED_FAILURE journal.
13. P0 performance mode on the same D-009 commit: HabitatEngine active; MANIPULATE/routines/D-009 dynamics disabled.
14. `umbra_core` / `experiments` never import `ui/`.
15. Dynamic `object_version` + `object_state_hash` per HabitatObject.
16. Policy candidates are address-only; arbitration never sees authoritative `target_object_id`.
17. Body occupancy from immutable Embodiment views; Habitat does not persist a second body-position authority.
18. Gate summaries recompute from `raw-results.jsonl` + seed/hash manifests.
19. Two-stage preregistration freeze: implement definitions → compute hashes → commit complete freeze → formal experiments.

### Authority pipeline

```text
arbitration (ManipulationCandidate — address-only)
  → governance admit
  → trusted resolve: address → ResolvedManipulationTarget
  → EmbodimentAdapter.validate_manipulation → AdapterValidatedManipulation
  → HabitatAffordanceEngine.validate → AffordanceValidationResult + effect_plan
  → HabitatEngine consequence validation (same HabitatSnapshot)
  → execution journal PREPARED
  → shared persistence transaction (habitat + organism effects + events + VerifiedOutcome)
  → WorldModel / Memory / Individuality from committed outcome only
  → ExpressionEngine.derive from coherent post-commit bindings
```

### Ownership

| Layer | Owns | Must not |
|-------|------|----------|
| HabitatEngine | zones, objects, locations, dynamics, habitat events | goals, personality, memory writes, Embodiment mutation |
| HabitatAffordanceEngine | definition truth, preconditions, effect calculation | mutate habitat; write WM/memory; write physiology |
| WorldModel | uncertain expectations | habitat truth; authorize execution |
| Memory | episodes, procedural routines | mutate habitat directly |
| Individuality | bounded scoring modifiers | move objects; grant affordances |
| Expression | derived presentation | invent object motion; write habitat |
| Embodiment | body pose, collision, MOVE/… | object inventory; habitat writes |
| Embodiment.habitat | read-only projection | independent mutation; authority decisions |

## Capability: MANIPULATE

Add one governed capability: `MANIPULATE`. Operations: `PICK_UP`, `PLACE`, `PUSH`, `ACTIVATE`, `DEACTIVATE`, `USE`. Version D-008 production body profiles for MANIPULATE support; preserve sealed D-008 definitions and hashes. Idempotent D-008→D-009 profile migration with `embodiment_body_profile_swapped` and `habitat_held_binding_rebased` when held objects exist. `habitat_profile_capability_migrated` is not authoritative for profile migration.

## Experimental conditions (C0–C13)

| Condition | Description |
|-----------|-------------|
| C0 | Full persistent habitat and environmental agency |
| C1 | Static non-persistent habitat |
| C2 | Scripted object movement independent of organism action |
| C3 | Random object manipulation |
| C4 | WorldModel environmental predictions disabled |
| C5 | Episodic environmental memory disabled |
| C6 | Procedural environmental routines disabled |
| C7 | Individuality contribution to environmental behavior disabled |
| C8 | Habitat state reset on restart |
| C9 | UI projection treated as habitat truth |
| C10 | Governance bypass attempt |
| C11 | Action-frequency-only preference learning |
| C12 | Habitat events temporally shuffled during replay |
| C13 | Core-only performance baseline (P0 compatibility mode) |

C2, C3, C9, C10 isolated controls. C13 is performance baseline only.

## Scenarios (S0–S16)

| Scenario | Description |
|----------|-------------|
| S0 | Baseline autonomous habitat activity |
| S1 | Explore an unfamiliar zone |
| S2 | Inspect unfamiliar objects |
| S3 | Successfully activate a supported affordance |
| S4 | Attempt an unsupported or invalid affordance |
| S5 | Pick up, transport and place a portable object |
| S6 | Use rest, recovery or charging location |
| S7 | Develop a repeated object-use routine |
| S8 | Object moved unexpectedly, requiring prediction revision |
| S9 | Preferred object temporarily unavailable |
| S10 | Restart during manipulation |
| S11 | Snapshot and birth replay after habitat changes |
| S12 | Compatible D-008 to D-009 body-profile migration |
| S13 | Extended no-user autonomous operation |
| S14 | Contrasting D-007 individuals in identical habitats |
| S15 | Habitat capacity, clutter and boundedness stress |
| S16 | Reversal of a previously useful affordance |

Scenarios manipulate environmental opportunities only — never preferences, habits, personality, choices, routines, beliefs, or presentation state.

## Design / preregistration

- Design: `docs/superpowers/specs/2026-07-23-umbra-d009-persistent-habitat-agency-design.md`
- Plan: `docs/superpowers/plans/2026-07-23-umbra-d009-persistent-habitat-agency.md`
- Stage A: implement definitions; compute hashes (no formal experiments)
- Stage B freeze (before formal experiments):
  - `experiments/d009/thresholds.json`
  - `experiments/d009/experiment-matrix.json`
  - `experiments/d009/scenario-suite.json`
  - `experiments/d009/habitat-definition.json`
  - `experiments/d009/affordance-definitions.json`
- Gate-critical comparisons: ≥100 paired seeds
- Harness refuses placeholder hashes, dirty frozen files, definition mismatches, uncommitted source changes, unknown failure codes, insufficient seeds

## Acceptance gates (summary)

| Gate | Pass when |
|------|-----------|
| 0 | D-001…D-008 seals validate unchanged; D-008 profiles recoverable; no authority regression |
| 1 | HabitatEngine sole truth; WM uncertain; UI read-only; C9 rejected |
| 2 | Valid MANIPULATE commits; invalid → durable fail + zero mutation; C2/C3/C10 worse/rejected; C0 unauthorized_mutation_rate=0 |
| 3 | Held-out environmental predictions; C4/C5 weaker; C11 not consequence learning; hidden-object leakage = 0 |
| 4 | No-user autonomous environmental behavior; not scripted schedule |
| 5 | Organism-caused habitat change survives restart/snapshot/birth/UI/migration; C1/C8 weaker |
| 6 | Non-authored interruptible routine from multiple episodes; C6 weaker; safe failure on stale/missing objects |
| 7 | Contrasting D-007 histories separate habitat use; C7 reduces separation |
| 8 | Revision under environmental change; single anomaly does not erase learning |
| 9 | D-008→D-009 migration preserves organism+habitat; held rebinding atomic; unknown fails closed |
| 10 | No capability grant/self-auth/bypass/memory write/identity fabricate; C10 rejected |
| 11 | ≥100 restarts; snapshot/birth match; idempotent events; exactly-one terminal outcome per execution_id; atomic commits; prepared recovery deterministic |
| 12 | Bounded objects/zones/pending/routines/cooldowns/read models; event storage within budget |
| 13 | ≥100k accelerated ticks; adaptive P0/P1/P2 (S3 pattern); RSS/CPU absolute + Tkinter incremental limits |
| 14 | Habitat supports persistent organism — not game/decorative/LLM/chemistry/robotics substitute |
| 15 | All modules present; zero skipped tests; evidence hashes validate; Mimir closed; clean worktree; allowed verdict only |

Full gate definitions, failure codes, minimum tests, and evidence paths: design spec §§3–8 and operator directive §§16–18.

### Adaptive performance (Gate 13)

```text
warm-up: 300 s
initial measurement: 1800 s
extension: +900 s when ambiguous
maximum: 3600 s per mode

P0  HabitatEngine compatibility (MANIPULATE/routines/D-009 dynamics off)
P1  Full D-009 + HeadlessRenderer
P2  Full D-009 + TkinterRenderer

RSS p95 ≤ 180 MiB; slope ≤ 1 MiB/h
CPU mean ≤ 5% of one logical core
Tkinter incremental RSS p95 ≤ 128 MiB; slope ≤ 1 MiB/h; CPU ≤ 5%
```

## Minimum tests

`tests/test_d009.py` — operator directive §17 minimum list plus design amendment tests (own-and-delegate, address-only candidates, execution journal, object versioning, body occupancy view, raw evidence reproducibility). Final sealed suite: zero skips.

## Evidence

```text
docs/evidence/d009/prior-seals.json
docs/evidence/d009/schema-manifest.json
docs/evidence/d009/*-results.json
docs/evidence/d009/raw-results.jsonl
docs/evidence/d009/seed-manifest.json
docs/evidence/d009/evidence-validation.json
docs/evidence/d009/evidence-hashes.json
docs/evidence/d009/final-verdict.md
```

## Allowed verdicts (§21)

```text
UMBRA_D009_PERSISTENT_HABITAT_AGENCY_QUALIFIED
UMBRA_D009_PARTIAL_FOUNDATION
UMBRA_D009_HABITAT_AUTHORITY_FAIL
UMBRA_D009_MANIPULATION_FAIL
UMBRA_D009_ENVIRONMENTAL_LEARNING_FAIL
UMBRA_D009_AUTONOMY_FAIL
UMBRA_D009_HABITAT_PERSISTENCE_FAIL
UMBRA_D009_ENVIRONMENTAL_ROUTINE_FAIL
UMBRA_D009_INDIVIDUALITY_HABITAT_FAIL
UMBRA_D009_REVISION_FAIL
UMBRA_D009_PROFILE_MIGRATION_FAIL
UMBRA_D009_GOVERNANCE_FAIL
UMBRA_D009_REPLAY_FAIL
UMBRA_D009_BOUNDEDNESS_FAIL
UMBRA_D009_REGRESSION_FAIL
UMBRA_D009_PERFORMANCE_FAIL
```

D-010 authorized only under `UMBRA_D009_PERSISTENT_HABITAT_AGENCY_QUALIFIED`.

## Completion condition

D-009 is complete only when evidence demonstrates that the qualified UMBRA individual autonomously perceives, learns, uses, and persistently modifies a bounded digital habitat through governed environmental affordances; develops non-authored environmental preferences and routines; preserves organism and habitat continuity across restart, replay, and compatible body-capability migration; and remains measurably dependent on accumulated history rather than scripted environmental behavior.

The result must be a persistent creature inhabiting a world, not an animation moving through a decorative scene.
