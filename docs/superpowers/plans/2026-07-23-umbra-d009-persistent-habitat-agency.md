# UMBRA-D-009 Persistent Habitat Agency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Qualify bounded autonomous environmental agency in a persistent digital habitat — governed MANIPULATE affordances, history-dependent habitat use, learned environmental routines, and organism+habitat continuity across restart, replay, and D-008→D-009 profile migration.

**Architecture:** Own-and-delegate. `HabitatEngine` is sole habitat authority/mutator/event source; `Embodiment.habitat` is a deeply immutable compatibility projection. Continuous 2D space with non-overlapping axis-aligned zone overlays. `HabitatAffordanceEngine` is pure (effect plans only). Runtime orchestrates trusted address resolution, adapter validation, affordance validation, and shared-persistence atomic commits with a PREPARED→COMMITTED_SUCCESS|COMMITTED_FAILURE execution journal. MANIPULATE candidates are address-only (no authoritative object IDs in arbitration). Expression projects from coherent HabitatEngine + body pose bindings.

**Tech Stack:** Python 3 stdlib + SQLite WAL (`umbra_core`), `tkinter` + Xvfb for P2 soak only, pytest. No new third-party dependencies.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-23-umbra-d009-persistent-habitat-agency-design.md` (commits `da60f20`, amendments `79a00f2`)
- Directive (create in Task 0): `docs/directives/UMBRA-D-009-persistent-habitat-agency.md`
- Starting commit: `b230790df1cab1580ea650a348eb0576e2e4599e`
- Design commits: `da60f2037cf898f7109798f6fc43514223b35ce0`, `79a00f24a1a9cc3f81464e4ba1ee4776cbffa17d`
- Mimir project: `7777645d52a91b49`; task: `06b5b59709864e11bddb8c1da56dd66e`; agent directive: `D-20260723-umbra-d009-persistent-habitat-agency`
- Preserve sealed D-008 profile definitions/hashes; version profiles for MANIPULATE
- Capability names: existing D-008 set **plus** `MANIPULATE` — never invent personality commands
- `umbra_core` / `experiments` never import `ui/`
- C2/C3/C9/C10 isolated; C13 = performance baseline
- Formal experiments only after Stage B freeze (no placeholder hashes)
- Final sealed suite: zero skips
- Do not edit `.agent/RECORD.md`
- Ponytail: smallest correct diff; reuse D-006/D-007/D-008 harness patterns
- Failure code `UNSUPPORTED_BODY_CAPABILITY` (not `BODY_CAPABILITY_UNSUPPORTED`)

## File map

| Path | Responsibility |
|------|----------------|
| `docs/directives/UMBRA-D-009-persistent-habitat-agency.md` | Canonical project directive text |
| `umbra_core/habitat/__init__.py` | Public exports |
| `umbra_core/habitat/state.py` | HabitatState, Zone, HabitatObject, FREE/HELD_BY, typed ObjectState, hashing |
| `umbra_core/habitat/engine.py` | HabitatEngine queries + mutate under persistence |
| `umbra_core/habitat/projection.py` | Deeply immutable HabitatFeature projection |
| `umbra_core/habitat/events.py` | Habitat event payloads + apply helpers |
| `umbra_core/habitat/migration.py` | Feature→object + definition migrations |
| `umbra_core/habitat/execution_journal.py` | PREPARED / COMMITTED_* records |
| `umbra_core/habitat_affordances/__init__.py` | Public exports |
| `umbra_core/habitat_affordances/definitions.py` | AffordanceDefinition load/hash |
| `umbra_core/habitat_affordances/engine.py` | Pure HabitatAffordanceEngine |
| `umbra_core/embodiment_adapters/profiles.py` | D-009 profile versions + hold constraints |
| `umbra_core/embodiment_adapters/adapter.py` | `validate_manipulation` |
| `umbra_core/arbitration.py` | ManipulationCandidate generation (address-only) |
| `umbra_core/governance.py` | Admit + route MANIPULATE |
| `umbra_core/runtime.py` | Trusted resolve + orchestration + P0 mode |
| `umbra_core/persistence.py` | Atomic multi-effect commits |
| `umbra_core/events.py` | Register AUTHORITATIVE habitat event types |
| `umbra_core/embodiment.py` | Body-only ownership; projection facade; BodyOccupancyView |
| `umbra_core/world_model/` | Learning from verified outcomes (idempotent by execution_id) |
| `umbra_core/memory/` | Environmental routine lifecycle |
| `umbra_core/expression/habitat_read_model.py` | Project from HabitatEngine snapshot |
| `umbra_core/expression/engine.py` | Coherent render-packet bindings |
| `experiments/d009/*` | Definitions, freeze, harnesses, diagnostics |
| `tests/test_d009.py` | Full minimum + amendment tests |
| `docs/evidence/d009/*` | Evidence pack incl. raw-results.jsonl |

---

### Task 0: Directive + governance bookkeeping

**Files:**
- Create: `docs/directives/UMBRA-D-009-persistent-habitat-agency.md`
- Modify: `.agent/PROJECT_GOAL.md`, `.agent/PROJECT_PROFILE.md`, `.agent/REPO_MAP.md`, `.agent/CURRENT.md`
- Modify: `.cursor/rules/04-umbra-architecture.mdc`, `AGENTS.md`, `CLAUDE.md` (D-009 authorized → in progress; D-008 closed)

**Interfaces:**
- Produces: committed directive matching the operator-supplied UMBRA-D-009 text; program status updated

- [ ] **Step 1: Write the directive file** from the operator-supplied project directive (verbatim structure; include starting commit `b230790…` and Mimir task `06b5b59709864e11bddb8c1da56dd66e`).

- [ ] **Step 2: Update program status** in PROJECT_PROFILE / PROJECT_GOAL / architecture rules: D-008 QUALIFIED; D-009 in progress under design `79a00f2`.

- [ ] **Step 3: Update REPO_MAP** with `umbra_core/habitat/`, `habitat_affordances/`, `experiments/d009/`, design/plan paths.

- [ ] **Step 4: Commit**

```bash
git add docs/directives/UMBRA-D-009-persistent-habitat-agency.md .agent/ docs/ AGENTS.md CLAUDE.md .cursor/rules/04-umbra-architecture.mdc
git commit -m "Document UMBRA-D-009 directive and open program status."
```

---

### Task 1: Habitat state model + hashing + object versioning

**Files:**
- Create: `umbra_core/habitat/__init__.py`, `umbra_core/habitat/state.py`
- Test: `tests/test_d009.py` (new file; grow across tasks)

**Interfaces:**
- Produces:
  - `HabitatState`, `Zone`, `ZoneConnection`, `HabitatObject`
  - `ObjectLocation = FreeLocation | HeldByLocation`
  - `object_version: int`, `object_state_hash: str`
  - `canonical_serialize(...)`, `compute_state_hash(state)`, `compute_object_state_hash(obj)`
  - `ObjectState` tagged union (Idle/Resource/Station/Activatable/SocialEntitySpatial)

- [ ] **Step 1: Write failing tests**

```python
def test_habitat_definitions_have_stable_hashes():
    ...

def test_object_version_increments_once_per_committed_mutation():
    ...

def test_failed_mutation_does_not_increment_object_version():
    ...
```

- [ ] **Step 2: Run to verify FAIL** — `pytest tests/test_d009.py::test_object_version_increments_once_per_committed_mutation -v`

- [ ] **Step 3: Implement `state.py`** with frozen initial `object_version`, hash excludes self, definition migration increments both definition_version and object_version.

- [ ] **Step 4: GREEN + commit**

```bash
git add umbra_core/habitat/ tests/test_d009.py
git commit -m "Add D-009 HabitatState model with object versioning and hashes."
```

---

### Task 2: HabitatEngine sole writer + projection + queries

**Files:**
- Create: `umbra_core/habitat/engine.py`, `umbra_core/habitat/projection.py`, `umbra_core/habitat/migration.py`
- Modify: `umbra_core/embodiment.py` (read-only projection facade; reject writes)
- Test: `tests/test_d009.py`

**Interfaces:**
- Consumes: Task 1 state types
- Produces:
  - `HabitatEngine.zone_at`, `connected_zones`, `get_object`, `query_nearby`, `check_collision(BodyCollisionShape, Position)`, `check_range(BodyPoseView, ReachProfile, object_id)`, `snapshot_view()`, `held_by`
  - `project_features(snapshot) -> ImmutableHabitatProjection`
  - `BodyOccupancyView` (in embodiment or habitat types module)
  - Indexes: `zone_free_object_count`, `zone_held_object_count`, `hold_index`, `free_spatial_index` (no persisted `zone_body_count`)

- [ ] **Step 1: Write failing tests**

```python
def test_habitat_engine_is_only_writer(): ...
def test_embodiment_habitat_projection_is_read_only(): ...
def test_projection_matches_authoritative_version_and_hash(): ...
def test_projection_mismatch_fails_closed(): ...
def test_body_occupancy_uses_immutable_embodiment_view(): ...
def test_habitat_does_not_persist_second_body_position(): ...
def test_legacy_reads_do_not_create_second_authority(): ...
```

- [ ] **Step 2: Implement engine + deeply immutable projection + feature→object migration helper**

- [ ] **Step 3: Wire Embodiment.habitat as projection-only** (mutable collections rejected)

- [ ] **Step 4: GREEN + commit**

```bash
git commit -m "Add HabitatEngine sole writer and read-only Embodiment projection."
```

---

### Task 3: Habitat events in canonical AUTHORITATIVE registry

**Files:**
- Create: `umbra_core/habitat/events.py`
- Modify: `umbra_core/events.py`
- Test: `tests/test_d009.py`

**Interfaces:**
- Produces: event type constants + `apply_habitat_event(state, event) -> HabitatState`
- Event classes per design §3 (no overlapping generic+specific for same mutation; `habitat_body_zone_transitioned` does not advance habitat state_version when habitat state unchanged)

- [ ] **Step 1: Failing tests** — `test_habitat_events_are_idempotent`, `test_invalid_habitat_event_order_fails_closed`, `test_missing_habitat_event_fails_closed`, `test_habitat_state_hash_mismatch_fails_closed`, `test_zone_transition_event_does_not_duplicate_body_authority`, `test_birth_replay_rebuilds_projection_from_habitat_events`, `test_replay_reproduces_object_versions_and_hashes`

- [ ] **Step 2: Register events + apply helpers**

- [ ] **Step 3: GREEN + commit**

```bash
git commit -m "Register D-009 habitat events on the canonical authoritative ledger."
```

---

### Task 4: Affordance definitions + pure HabitatAffordanceEngine

**Files:**
- Create: `umbra_core/habitat_affordances/__init__.py`, `definitions.py`, `engine.py`
- Create (Stage A draft, not formal freeze): `experiments/d009/affordance-definitions.json`, `experiments/d009/habitat-definition.json` (real content; hashes computed later in Task 11)
- Test: `tests/test_d009.py`

**Interfaces:**
- Produces:
  - `AffordanceDefinition`, `definition_hash(...)`
  - `HabitatAffordanceEngine.validate(...) -> AffordanceValidationResult`
  - `HabitatEffectPlan(habitat_mutations, habitat_events, requested_organism_effects)`
  - Typed `ManipulationParameters` union

- [ ] **Step 1: Failing tests** — `test_affordance_definitions_have_stable_hashes`, `test_manipulation_parameters_are_typed_and_bounded`, plus validate rejects cooldown/precondition failures with stable codes

- [ ] **Step 2: Implement pure engine (no mutation / no WM writes)**

- [ ] **Step 3: GREEN + commit**

```bash
git commit -m "Add pure HabitatAffordanceEngine and static affordance definitions."
```

---

### Task 5: Execution journal + shared-persistence atomic commit

**Files:**
- Create: `umbra_core/habitat/execution_journal.py`
- Modify: `umbra_core/persistence.py`, `umbra_core/governance.py`, `umbra_core/runtime.py`
- Test: `tests/test_d009.py`

**Interfaces:**
- Produces:
  - Journal states `PREPARED | COMMITTED_SUCCESS | COMMITTED_FAILURE`
  - `prepare_execution(...)`, `recover_execution(...)`, `commit_manipulation_transaction(...)`
  - Atomic: habitat mutation + approved organism effects + habitat/organism events + VerifiedOutcome
  - Codes: `EXECUTION_PAYLOAD_MISMATCH`, `HABITAT_COLLECTION_CAP_EXCEEDED`, `EVENT_STORAGE_BUDGET_EXCEEDED`

- [ ] **Step 1: Failing tests**

```python
def test_execution_id_has_exactly_one_terminal_outcome(): ...
def test_successful_execution_cannot_mutate_twice(): ...
def test_failed_execution_cannot_execute_after_restart(): ...
def test_prepared_execution_recovers_deterministically(): ...
def test_same_execution_id_with_different_payload_fails_closed(): ...
def test_same_request_id_with_different_payload_fails_closed(): ...
def test_unknown_commit_status_does_not_create_false_failure(): ...
def test_prepared_recovery_cannot_double_mutate(): ...
def test_resource_and_organism_effect_commit_atomically(): ...
def test_object_pickup_is_atomic(): ...
def test_object_place_is_atomic(): ...
def test_object_cannot_exist_in_two_locations(): ...
def test_failed_manipulation_has_durable_outcome(): ...
def test_invalid_manipulation_changes_no_habitat_state(): ...
def test_crash_during_manipulation_cannot_partially_commit(): ...
```

- [ ] **Step 2: Implement journal + persistence transaction**

- [ ] **Step 3: GREEN + commit**

```bash
git commit -m "Add MANIPULATE execution journal and atomic habitat outcome commits."
```

---

### Task 6: Adapter validate_manipulation + D-009 profiles + migration

**Files:**
- Modify: `umbra_core/embodiment_adapters/adapter.py`, `profiles.py`
- Modify: `umbra_core/runtime.py`, `umbra_core/persistence.py`
- Test: `tests/test_d009.py`

**Interfaces:**
- Produces:
  - D-009 profile versions with `MANIPULATE`, `hold_slot_count=1`, `maximum_held_mass_class`, `hold_anchor`
  - Preserve original D-008 definition hashes unchanged
  - `validate_manipulation(...) -> AdapterValidatedManipulation`
  - Migration `origin=D009_PROFILE_MIGRATION` via `embodiment_body_profile_swapped` + optional `habitat_held_binding_rebased`

- [ ] **Step 1: Failing tests** — profile unchanged hashes; migration idempotent/preserves identity/memory/individuality/relationships/habitat; unknown fails closed; held rebase atomic; incompatible held swap fails; `test_adapter_cannot_change_operation_or_target`; `test_manipulate_requires_supported_body_profile`; `test_d008_profile_definitions_remain_unchanged`

- [ ] **Step 2: Implement profiles + validate_manipulation + migration**

- [ ] **Step 3: GREEN + commit**

```bash
git commit -m "Add D-009 MANIPULATE profiles, adapter validation, and migration."
```

---

### Task 7: Address-only candidates + trusted resolve + governance path

**Files:**
- Modify: `umbra_core/arbitration.py`, `umbra_core/perception.py`, `umbra_core/governance.py`, `umbra_core/runtime.py`
- Test: `tests/test_d009.py`

**Interfaces:**
- Produces:
  - `ManipulationCandidate` (no `target_object_id`)
  - `resolve_manipulation_address(...) -> ResolvedManipulationTarget`
  - Full path: admit → resolve → adapter → affordance → habitat → journal commit

- [ ] **Step 1: Failing tests**

```python
def test_policy_candidate_contains_no_authoritative_object_id(): ...
def test_trusted_runtime_resolves_address_to_authoritative_object(): ...
def test_hidden_object_ids_never_enter_arbitration(): ...
def test_hidden_objects_do_not_generate_manipulation_candidates(): ...
def test_manipulate_requires_current_address_binding(): ...
def test_stale_object_address_binding_fails_closed(): ...
def test_ambiguous_object_address_binding_fails_closed(): ...
def test_manipulate_requires_governance(): ...
def test_valid_manipulation_changes_habitat(): ...
def test_stale_object_version_fails_closed(): ...
def test_object_out_of_range_fails(): ...
def test_unsupported_affordance_fails(): ...
def test_object_definition_mismatch_fails_closed(): ...
def test_affordance_definition_mismatch_fails_closed(): ...
def test_profile_definition_mismatch_fails_closed(): ...
```

- [ ] **Step 2: Implement candidate generation + trusted resolve + wire**

- [ ] **Step 3: GREEN + commit**

```bash
git commit -m "Wire address-only MANIPULATE candidates through trusted resolve."
```

---

### Task 8: Learning, routines, individuality environmental scoring

**Files:**
- Modify: `umbra_core/world_model/engine.py`, `umbra_core/memory/engine.py`, `umbra_core/individuality/engine.py`, `umbra_core/arbitration.py`
- Test: `tests/test_d009.py`

**Interfaces:**
- WorldModel updates idempotent by `execution_id`; reject incomplete/denied/stale bindings
- Routine lifecycle: `CANDIDATE|ACTIVE|WEAKENED|INACTIVE|RETIRED` (not FIFO)
- Individuality: bounded scoring only

- [ ] **Step 1: Failing tests** — environmental learning requires verified outcomes; frequency alone no preference; revision tests; routine multi-episode/interruptible/missing-object/governance-each-step; different histories; individuality disabled reduces separation; WM idempotent by execution

- [ ] **Step 2: Implement learning/routine/individuality hooks**

- [ ] **Step 3: GREEN + commit**

```bash
git commit -m "Integrate environmental learning, routines, and individuality scoring."
```

---

### Task 9: Expression HabitatReadModel + coherent held render + Tk habitat overlays

**Files:**
- Modify: `umbra_core/expression/habitat_read_model.py`, `engine.py`, `ui/reference_companion/habitat_view.py`
- Test: `tests/test_d009.py`

**Interfaces:**
- `HabitatReadModel.from_habitat_snapshot(snapshot, ...)` (not Embodiment.to_state)
- Render packet binds habitat_state_version/hash, organism_state_version, body_attachment_generation, execution_id, body_pose_version
- Drop packet on mismatch; held render requires matching generation

- [ ] **Step 1: Failing tests** — expression reads habitat engine snapshot; renderer does not invent motion / show failed as success; held render generation; coherent packet versions; habitat read model matches authoritative state; UI cannot write habitat

- [ ] **Step 2: Implement + GREEN + commit**

```bash
git commit -m "Project habitat expression from HabitatEngine with coherent packet bindings."
```

---

### Task 10: Conditions C0–C13 + scenarios S0–S16 scaffolding

**Files:**
- Create: `experiments/d009/diagnostic_controllers.py` (C2/C3 only), hostile/governance-bypass helpers for C9/C10
- Modify: `umbra_core/runtime.py` (P0 compatibility mode: HabitatEngine on; MANIPULATE/routines/D-009 dynamics off)
- Test: `tests/test_d009.py`

**Interfaces:**
- C2 fails causal attribution; C3 fails history dependence; C9/C10 rejected with zero mutation
- P0 mode configuration flag consumed by Gate 13 later

- [ ] **Step 1: Failing tests** — scripted motion not autonomy; random manipulation not learning; governance bypass; autonomous activity without user; rest/waiting valid

- [ ] **Step 2: Implement condition switches + scenario plants (environmental opportunities only)**

- [ ] **Step 3: GREEN + commit**

```bash
git commit -m "Add D-009 experimental conditions and scenario scaffolding."
```

---

### Task 11: Stage B preregistration freeze (hashes + matrix + thresholds)

**Files:**
- Create/finalize: `experiments/d009/thresholds.json`, `experiment-matrix.json`, `scenario-suite.json`, `habitat-definition.json`, `affordance-definitions.json`
- Optionally: `experiments/d009/seed-manifest.json` template for formal runs
- Modify: thresholds to include all freeze additions from design §5

**Interfaces:**
- Produces: complete freeze with **real** SHA-256 hashes (no placeholders)
- Harness refuse rules documented in `run_experiment.py` (Task 13)

**Order (mandatory):**

- [ ] **Step 1:** Ensure Stage A definitions/profiles implemented and tested (Tasks 1–6)
- [ ] **Step 2:** Compute canonical hashes for habitat definition, affordances, D-009 profiles, migration source/dest
- [ ] **Step 3:** Write final numeric thresholds, matrix, scenarios, seed counts (≥100), capacity codes, routine policies, P0 config, adaptive protocol
- [ ] **Step 4:** Commit freeze package on a clean worktree

```bash
git add experiments/d009/
git commit -m "Freeze D-009 preregistration definitions, thresholds, and matrix."
```

- [ ] **Step 5:** Record freeze commit SHA in `.agent/CURRENT.md` — formal experiments must start from this commit

---

### Task 12: Complete `tests/test_d009.py` minimum list + prior seals

**Files:**
- Modify: `tests/test_d009.py`
- Create helpers as needed under `tests/` only if required

- [ ] **Step 1:** Cross-check directive §17 + design amendment test lists against `tests/test_d009.py`; add any missing named tests
- [ ] **Step 2:** Include `test_d001_through_d008_seals_unchanged`, `test_prior_regressions_within_bounds`, `test_no_deferred_modules`, `test_100k_tick_boundedness`, `test_adaptive_performance_validation` (artifact-reading until Task 14 evidence exists, D-008 pattern — no skips in final seal)
- [ ] **Step 3:** `pytest tests/test_d009.py -v` GREEN; full suite still green
- [ ] **Step 4: Commit**

```bash
git commit -m "Complete D-009 minimum test coverage and prior-seal checks."
```

---

### Task 13: Experiment harness + raw evidence (Gates 1–12)

**Files:**
- Create: `experiments/d009/run_experiment.py`, `evidence.py`, `validate_evidence.py`
- Create: `docs/evidence/d009/*.json` summaries + `raw-results.jsonl` + `seed-manifest.json` + `evidence-validation.json`

**Interfaces:**
- ≥100 paired seeds per gate-critical cell
- Validator recomputes summaries from raw ledger; rejects missing/duplicate/seed mismatch/mixed hashes/unexplained exclusions
- Harness refuses placeholder hashes, dirty freeze files, definition mismatches, uncommitted source changes, unknown failure codes, insufficient seeds
- Do **not** claim QUALIFIED; Gate 13 deferred to Task 14

- [ ] **Step 1: Implement harness + validator**
- [ ] **Step 2: Run gate-critical matrix; write raw + summaries**
- [ ] **Step 3: Validate evidence**
- [ ] **Step 4: Commit evidence only if validator OK**

```bash
git commit -m "Add D-009 Gates 1–12 experiment evidence with reproducible raw ledger."
```

---

### Task 14: Adaptive performance (S3) + final seal

**Files:**
- Create: `experiments/d009/run_performance.py`, `run_seal.py`, `performance-protocol.json`, `with_tk_display.sh` (reuse D-008 patterns)
- Modify: `tests/test_d009.py` (unskip/artifact-read Gate 13)
- Create: `docs/evidence/d009/performance-*.json`, soak jsonl, `final-verdict.md`, `evidence-hashes.json`, `prior-seals.json`, `schema-manifest.json`

**Modes (same D-009 commit):**

```text
P0  HabitatEngine compatibility mode (MANIPULATE/routines/D-009 dynamics off)
P1  Full D-009 + HeadlessRenderer
P2  Full D-009 + TkinterRenderer
```

Protocol: warm-up 300s → measure 1800s → +900s if ambiguous → max 3600s/mode.

- [ ] **Step 1: Implement performance harness**
- [ ] **Step 2: Run 100k + P0/P1/P2 adaptive matrix**
- [ ] **Step 3: Run seal (zero-skip full suite, prior seals, hashes)**
- [ ] **Step 4: Commit seal + close Mimir against final commit**
- [ ] **Step 5: Confirm clean worktree; no leftover soak/Xvfb/runtime processes**

Allowed QUALIFIED only if all gates pass:

```text
UMBRA_D009_PERSISTENT_HABITAT_AGENCY_QUALIFIED
```

---

## Spec coverage checklist

| Spec area | Tasks |
|-----------|-------|
| HabitatEngine sole writer / projection | 2, 3 |
| Object versioning | 1, 5 |
| Zones continuous overlays | 1, 2 |
| HELD_BY / pickup-place atomic | 2, 5, 7 |
| Pure affordance engine | 4 |
| Address-only candidates + trusted resolve | 7 |
| Execution journal PREPARED/COMMITTED | 5 |
| BodyOccupancyView | 2 |
| Profile migration + held rebase | 6 |
| Learning / routines / individuality | 8 |
| Expression coherent packets | 9 |
| C0–C13 / S0–S16 | 10, 13 |
| Two-stage freeze | 4 (A), 11 (B) |
| Raw evidence reproducibility | 13 |
| Adaptive perf + seal | 14 |
| Directive / governance | 0 |

## Plan self-review

- No placeholder hashes in Stage B freeze task; Stage A definitions precede hash computation.
- Failure codes match design A1–A6 (`EXECUTION_PAYLOAD_MISMATCH`, capacity codes, no `BODY_CAPABILITY_UNSUPPORTED`).
- P0 is compatibility mode on the same D-009 commit.
- Formal experiments gated after Task 11 freeze commit.
