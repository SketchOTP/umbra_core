# UMBRA-D-009 Design: Persistent Digital Habitat and Autonomous Environmental Agency

**Date:** 2026-07-23  
**Project directive:** UMBRA-D-009  
**Agent memory directive:** `D-20260723-umbra-d009-persistent-habitat-agency`  
**Starting commit:** `b230790df1cab1580ea650a348eb0576e2e4599e`  
**D-008 seal commit:** `ce777adda2d38daa3037411c5a88688c51cb3122`  
**Prerequisite:** `UMBRA_D008_COHERENT_DIGITAL_EMBODIMENT_QUALIFIED`  
**Mimir project:** `7777645d52a91b49`  
**Mimir task:** `06b5b59709864e11bddb8c1da56dd66e`  
**Status:** Design frozen pending final operator review of this file; then implementation planning

## Purpose

Advance Phase 2 by making UMBRA’s digital habitat a persistent, causally interactive environment rather than a passive visual backdrop. The qualified D-001…D-008 organism must explore, perceive under uncertainty, learn environmental consequences, manipulate supported objects, leave inspectable habitat history, develop environmental routines, and continue acting when no user is present — through the same governance, perception, prediction, memory, individuality, and expression architecture already qualified.

## Locked decisions (operator-approved)

1. **Own-and-delegate authority:** `HabitatEngine` is sole habitat authority, mutator, and event source immediately. `Embodiment.habitat` is a read-only compatibility projection rebuilt from committed HabitatEngine state.
2. **Continuous plane + zone overlays:** One authoritative 2D coordinate space; non-overlapping axis-aligned zones; zone membership derived from position; movement remains MOVE/APPROACH/RETREAT; portals deferred.
3. **HabitatObject sole spatial entity model:** Passive and interactive entities are HabitatObjects. `HabitatFeature` is projection vocabulary only.
4. **Held objects:** `HELD_BY` location mode lives only in HabitatEngine; production `hold_slot_count = 1`; no Embodiment inventory.
5. **Strict affordance split:** AffordanceDefinition + HabitatAffordanceEngine = world truth; D-003 WorldModel = uncertain expectations for proposal scoring only.
6. **MANIPULATE in arbitration:** New candidate type on the existing scorer; no EnvironmentalAgency controller.
7. **Packaging:** Split packages `umbra_core/habitat/` and `umbra_core/habitat_affordances/` with runtime orchestration only.
8. **Pure affordance evaluation:** AffordanceEngine returns immutable `AffordanceValidationResult` / `effect_plan`; never mutates.
9. **Shared-persistence atomicity:** Habitat mutation, habitat events, approved organism effects, and VerifiedOutcome commit together or not at all.
10. **Canonical event registry:** Habitat payloads/apply in `umbra_core/habitat/events.py`; registered through existing AUTHORITATIVE ledger — no second habitat ledger.
11. **Adapter validates only:** `validate_manipulation` → `AdapterValidatedManipulation`; runtime coordinates commit.
12. **Exactly-once execution:** One terminal VerifiedOutcome per `execution_id`; retries return existing outcome.
13. **P0 performance mode:** Same D-009 commit; HabitatEngine active; MANIPULATE/routines/D-009 dynamics disabled (compatibility mode).
14. **Import rule:** `umbra_core` / `experiments` never import `ui/`. `ui/` may import from `umbra_core.expression`.

## Hard constraints

* No LLM controller; no scripted pet game, animation scheduler, dialogue system, engagement grind, chemistry prerequisite, camera/microphone, or robotics body project.
* Habitat/affordance systems must not select organism goals, assign personality, write constitutional identity, write memory directly, write social relationships, grant capabilities, bypass governance, fabricate success, or treat UI as world truth.
* WorldModel must never become habitat truth.
* No direct commands: play, sleep, explore, collect, or organize as personality performances.
* Physiology changes only through existing verified organism-effect contracts coordinated in the shared persistence transaction.
* Closing or hiding the UI must not stop UMBRA.

## Scientific claims

**Authorized (bounded):** UMBRA demonstrates bounded autonomous environmental agency in a persistent digital habitat, including governed object interaction, history-dependent habitat use, learned environmental routines, and continuity of organism and habitat state across restart and replay.

**Not authorized:** consciousness; sentience; subjective experience; genuine emotion; biological life; unrestricted agency; human-equivalent planning; complete companion capability; physical-world competence; general-purpose object manipulation.

---

## 1. Architecture & packaging

```text
umbra_core/habitat/
  engine.py           # HabitatEngine: state, queries, mutate under persistence txn, dynamics
  state.py            # HabitatState, Zone, HabitatObject, FREE|HELD_BY, typed ObjectState
  events.py           # habitat event payloads + apply helpers (canonical registry)
  projection.py       # deeply immutable HabitatFeature compatibility projection
  migration.py        # feature→object and definition migrations

umbra_core/habitat_affordances/
  definitions.py      # static AffordanceDefinition load / hash
  engine.py           # HabitatAffordanceEngine (pure validate + effect plan)

umbra_core/embodiment_adapters/
  adapter.py          # validate_manipulation → AdapterValidatedManipulation
  profiles.py         # preserve D-008 hashes; add D-009 versions with MANIPULATE

umbra_core/arbitration.py   # MANIPULATE candidates
umbra_core/governance.py    # admit path
umbra_core/runtime.py        # orchestration + shared persistence coordination
umbra_core/persistence.py    # atomic multi-effect commits
umbra_core/expression/habitat_read_model.py  # from HabitatEngine snapshot

experiments/d009/
tests/test_d009.py
docs/evidence/d009/
docs/directives/UMBRA-D-009-persistent-habitat-agency.md
```

### Authority pipeline

```text
arbitration (MANIPULATE candidate + addressability proof)
  → governance admit
  → EmbodimentAdapter.validate_manipulation(...)
       → AdapterValidatedManipulation (immutable)
  → HabitatAffordanceEngine.validate(...) → AffordanceValidationResult + effect_plan
  → HabitatEngine consequence validation (against same HabitatSnapshot)
  → shared persistence transaction:
       check existing execution_id outcome
       revalidate expected versions/hashes
       apply habitat mutation
       apply approved organism effects (existing physiology authority)
       append habitat event(s) + organism effect event(s)
       append terminal VerifiedOutcome
       advance state_version / recompute state_hash
       commit
  → WorldModel / Memory / Individuality updates from committed outcome only
  → ExpressionEngine.derive from coherent post-commit packet bindings
```

On any validation or commit failure:

```text
no habitat mutation
+ durable failed VerifiedOutcome (when an execution was admitted)
```

### Ownership

| Layer | Owns | Must not |
|-------|------|----------|
| HabitatEngine | zones, objects, locations, dynamics, habitat events, indexes | goals, personality, memory, beliefs, capabilities, Embodiment mutation |
| HabitatAffordanceEngine | definition truth, preconditions, effect calculation | mutate habitat; write WM/memory; write physiology |
| Runtime | orchestration + shared persistence coordination | habitat semantics; becoming a habitat controller |
| Persistence | atomic multi-effect commit | invent habitat effects |
| Embodiment | body pose, collision, MOVE/…, reach facts | object inventory; habitat writes |
| Embodiment.habitat | read-only compatibility projection | independent mutation; authority decisions |
| EmbodimentAdapter | body compatibility, translation/clamp of continuous params | change operation/target/affordance/intent; coordinate habitat commit |
| WorldModel | uncertain expectations | habitat truth; authorize execution |
| Memory | episodes, procedural routines | mutate habitat |
| Individuality | bounded scoring modifiers | move objects; grant affordances |
| Expression | derived presentation | invent object motion; write habitat |
| SocialEngine | partner behavior | change partner position except via HabitatEngine commit |

### Migration stages

1. Introduce HabitatEngine as the only writer.  
2. Adapt D-001…D-008 reads through narrow HabitatEngine queries.  
3. Retain `Embodiment.habitat` only as a derived compatibility facade.  
4. Completion gate: zero production writes through the projection; zero production authority decisions based solely on projection state; temporary legacy reads only when version/hash-validated against HabitatEngine. Expression reads HabitatEngine snapshots.

### Placement validation split

| Layer | Validates |
|-------|-----------|
| Embodiment / adapter | reach, pose, orientation, body collision geometry, profile physical limits, hold slots / mass class |
| HabitatAffordanceEngine | affordance exposed, preconditions, cooldown, portable, definition match, typed parameters |
| HabitatEngine | object exists/version, FREE/HELD_BY invariants, free-object zone capacity, conflicts, resulting location, habitat version/hash |

Runtime passes one immutable `HabitatSnapshot(version, hash)` through reach, affordance, and commit validation. If habitat version changes before commit → `HABITAT_STATE_CONFLICT`.

---

## 2. Habitat data model

### HabitatState

```text
habitat_id
schema_version
habitat_tick                 # bound to authoritative runtime tick (one clock)
state_version
definition_hash              # frozen habitat definition identity
state_hash                   # current instance state identity
zones: map[zone_id → Zone]   # bounded
objects: map[object_id → HabitatObject]  # bounded
zone_connections: tuple[ZoneConnection, ...]   # sole topology authority
active_environmental_transitions: tuple[EnvironmentalTransition, ...]  # bounded typed
bounded_environmental_history_refs: tuple[...]  # bounded refs, not unbounded log
```

**Canonical `state_hash`:**

```text
state_hash = sha256(canonical_serialize(
  HabitatState excluding:
    state_hash
    derived indexes
    compatibility projections
    runtime caches
))
```

Canonical serialization freezes field order, map-key order, numeric representation, enum representation, null handling, and schema version.

`definition_hash` identifies the frozen habitat definition. `state_hash` identifies the current authoritative instance state.

**Zone connections:** only `HabitatState.zone_connections`. Query via `HabitatEngine.connected_zones(zone_id)`. Do not store mutable `Zone.connections`.

### Zone

```text
zone_id
zone_kind ∈ {GENERAL, REST, RECOVERY, MAINTENANCE, EXPLORATION, SOCIAL}
bounds                    # axis-aligned rect; polygon interface reserved, not required
occupancy_limit           # applies to free-object capacity (see occupancy rules)
body_constraints
  required_capabilities
  maximum_body_radius
  maximum_body_mass_class
  locomotion_requirements
environmental_properties  # versioned typed record (not open dict)
rest_support / maintenance_support   # environmental roles, not organism commands
```

Rules:

* Non-overlapping zones; every navigable coordinate belongs to exactly one zone.  
* `zone_id = HabitatEngine.zone_at(x, y)`.  
* Zone kinds describe place roles, never organism commands.  
* Zone boundary crossing does not reset velocity, orientation, commitments, or action state.  
* Emit `habitat_body_zone_transitioned` as a consequence of governed locomotion (not teleportation).

### HabitatObject

```text
object_id
object_kind ∈ {
  SCENERY, OBSTACLE, HAZARD, RESOURCE, INSPECTABLE,
  REST_STATION, CHARGE_STATION, PORTABLE_OBJECT,
  ACTIVATABLE_OBJECT, SOCIAL_ENTITY
}
definition_version
definition_hash
location = FREE {x, y, zone_id} | HELD_BY {body_instance_id, attachment_generation, hold_slot}
state                     # typed ObjectState union (not open dict)
mass_class
portable
passable / occluded
collision_radius
affordance_ids            # may be empty
visibility                # environmental visibility ≠ organism perception proof
condition                 # common field; must not duplicate inside Object.state
cooldowns                 # map affordance_id → cooldown_until_tick
```

**ObjectState** (versioned tagged union), for example:

```text
IdleState | ResourceState | StationState | ActivatableState | SocialEntitySpatialState
```

**Location modes:**

* Exactly one location mode per object.  
* FREE: authoritative `(x, y)`; `zone_id` derived/cached only with matching habitat `state_version`.  
* HELD_BY: no independent authoritative `(x, y)`; removed from free-object occupancy and collision indexes; not targetable as free; render position derived from body pose + hold_anchor; zone derived from holder position (informational); cannot remain in prior zone.  

**Partners:** SocialEngine owns partner behavior. Every partner-position change commits through HabitatEngine as a `SOCIAL_ENTITY` HabitatObject. Spatial presence follows the single HabitatObject authority.

### Occupancy (derived indexes)

```text
zone_free_object_count
zone_body_count
zone_held_object_count
hold_index[body_instance_id][hold_slot] = object_id
free_spatial_index
```

Frozen category rules:

* Free-object capacity counts FREE objects only.  
* Body occupancy is governed separately.  
* Held objects do not consume free-object capacity.  
* Placement checks resulting free-object capacity.  
* Held-object derived zone is informational only.

Indexes are rebuilt from authoritative objects on commit; never separately event-sourced.

### Cooldowns and dynamics

Store `cooldown_until_tick`. Remaining time is derived:

```text
max(0, cooldown_until_tick - habitat_tick)
```

Do not decrement remaining ticks every tick; do not emit no-op tick events; do not event-source every cooldown decrement. Derive periodic lighting/activity phases from `habitat_tick` when possible. Emit events only for meaningful authoritative transitions.

Dynamics (cooldown expiration effects, bounded wear/restoration, station availability, scenario availability changes) use the **same** event and shared-persistence transaction path as organism-caused mutations. Deterministic under frozen seeds. Never select organism goals. No unrestricted offline catch-up while the process is stopped.

`EnvironmentalTransition` records require: stable ID, start tick, completion tick, definition hash, bounded status.

### Narrow query API (immutable physical inputs)

```text
get_zone(zone_id)
zone_at(x, y)
connected_zones(zone_id)
get_object(object_id)
query_nearby(x, y, radius, *, free_only=True)
check_collision(proposed_shape: BodyCollisionShape, proposed_position: Position)
check_range(body_pose: BodyPoseView, reach_profile: ReachProfile, object_id)
snapshot_view() → HabitatSnapshot(version, hash, …)
held_by(body_instance_id)
```

`HabitatEngine` must not receive mutable `Embodiment` objects. Embodiment supplies body facts; Habitat evaluates them without importing or mutating Embodiment.

### Compatibility projection

```text
HabitatObject* → deeply immutable HabitatFeature-shaped view
  kind, x, y, radius, passable, occluded, legacy plant flags
  source_state_version, source_state_hash
```

* Immutable tuples/mappings throughout (no mutable nested collections).  
* Mismatch with HabitatEngine → fail closed.  
* Never event-sourced; never replay authority.  
* Legacy feature IDs map deterministically to `object_id`.  
* Legacy writes fail.  
* Birth replay: reconstruct authoritative state → validate state_hash → rebuild indexes → rebuild projection.

### Collection caps and growth

Exceeding a frozen collection cap on an attempted action produces a durable failed outcome with zero partial mutation. Do not crash silently.

Gate 12 freezes separate limits for: active in-memory history refs, replay indexes, pending transactions, recent-event caches, snapshot frequency, and database growth rate. The immutable event ledger may grow within a preregistered storage-growth budget. Archival/compaction (if used) must keep original event identity/hashes recoverable, demonstrate replay equivalence, and must not rewrite scientific evidence. Snapshots remain accelerators, not replacement truth. Authoritative history is not silently deleted.

---

## 3. Affordances, MANIPULATE, adapter, profile migration

### AffordanceDefinition (static)

Frozen in `experiments/d009/affordance-definitions.json`.

```text
affordance_id
target_object_kind
operation ∈ {PICK_UP, PLACE, PUSH, ACTIVATE, DEACTIVATE, USE}
required_capability = MANIPULATE
preconditions                 # typed bounded schema
body_requirements
environmental_cost            # typed
organism_effect_contract      # typed requested effects (proposals only)
world_effect_contract
reversibility
cooldown_ticks                # sets cooldown_until_tick on success
failure_modes
definition_version
definition_hash
```

Definition changes require versioned migration and new hashes. Learned beliefs reference the definition version observed during each outcome. Obsolete-definition beliefs remain historical evidence but lose current predictive authority.

### HabitatAffordanceEngine (pure)

```text
validate(request, habitat_snapshot, adapter_validated, …)
  → AffordanceValidationResult
       allowed
       failure_code | None
       expected_object_version
       expected_habitat_version
       effect_plan: HabitatEffectPlan | None
       applied_parameters: typed ManipulationParameters
```

```text
HabitatEffectPlan
  habitat_mutations
  habitat_event(s)
  requested_organism_effects   # typed proposals only — not direct physiology writes
```

Runtime passes `requested_organism_effects` to the existing qualified organism-effect / physiology authority. Shared persistence coordinates:

```text
habitat mutation
+ approved organism effect
+ habitat event(s)
+ organism effect event(s)
+ VerifiedOutcome
```

If any required component fails validation, none commit.

### MANIPULATE request

```text
request_id
execution_id
capability = MANIPULATE
target_object_id
target_address_ref
perception_evidence_ref
perception_state_version
affordance_id
expected_habitat_version
expected_habitat_state_hash
target_object_version
target_object_definition_version
target_object_definition_hash
affordance_definition_version
affordance_definition_hash
body_profile_definition_hash
body_instance_id
body_profile_id
attachment_generation
parameters: ManipulationParameters   # tagged union
```

```text
ManipulationParameters =
    PickUpParameters { hold_slot }
  | PlaceParameters { target_position, expected_zone_id, optional_support_object_id }
  | PushParameters { direction, requested_distance }
  | ActivateParameters | DeactivateParameters | UseParameters
```

Adapter may clamp continuous values (e.g. push distance). Adapter must not change operation, target object, placement target, affordance, or semantic intent. VerifiedOutcome records both canonical requested and applied parameter structures.

### Addressability / perception boundary

```text
HabitatEngine object existence ≠ policy-visible manipulation opportunity
```

* Remembered objects may motivate APPROACH or INSPECT.  
* MANIPULATE execution requires a current unambiguous perception or spatial-track binding.  
* Runtime resolves the policy-visible reference to the authoritative object.  
* Stale or ambiguous bindings fail closed.  
* Hidden authoritative objects must never leak into candidate generation.  
* `OBJECT_NOT_PERCEIVED` is evaluated from perception-membrane evidence, not inferred by HabitatEngine from world truth.

Gate 3/4 measurements (all must be zero when required):

* hidden-object candidate leakage  
* stale-address candidate execution  
* ambiguous-address execution  
* authoritative object enumeration exposed to policy  

### Candidate generation (arbitration)

```text
ActionCandidate
  capability = MANIPULATE
  target_object_id (+ addressability fields)
  affordance_id
  parameters
  expected_outcome / latency / effort
  success_confidence / uncertainty
  source ∈ {
    NOVELTY_EXPLORATION, NEED_RELEVANCE, WORLD_MODEL_EXPECTATION,
    PROCEDURAL_ROUTINE, HABIT, SOCIAL_CONTEXT, DEVELOPMENTAL_PRACTICE
  }
  supporting_evidence_refs
```

Source is explanatory metadata, not separate authority. Bound per tick: max manipulation candidates, max affordances per object, max remembered off-screen targets, max planning distance. Deterministically merge duplicate equivalent candidates.

Exploration path:

```text
INSPECT → perception/WM evidence → optional exploratory MANIPULATE
  → governance → authoritative validation → verified outcome → learning
```

High-risk/destructive unknown affordances must not be explored blindly.

Routine path: D-005 may inject/strengthen candidates; each step still passes full governance chain; routines never mutate habitat directly.

### Adapter output

```text
EmbodimentAdapter.validate_manipulation(...)
  → AdapterValidatedManipulation
       body_pose_view
       reach_profile
       collision_shape
       validated_profile
       requested_parameters
       applied_parameters
       translation_applied
```

### Exactly-once execution

Durable uniqueness for `request_id` / `execution_id`:

* One `execution_id` → at most one terminal VerifiedOutcome.  
* Retry after crash returns the existing outcome.  
* Committed success cannot mutate habitat again.  
* Committed failure cannot later execute under the same ID.  
* Duplicate requests with different execution IDs still fail when expected versions/hashes are stale.  
* Prepared but incomplete execution records resolve deterministically on recovery (frozen `prepared_execution_timeout`).

Transaction order:

```text
check existing execution outcome
→ revalidate expected versions and hashes
→ apply mutation + authoritative events + approved organism effects
→ append VerifiedOutcome
→ commit
```

### Failure codes (stable)

Retain D-008:

```text
UNSUPPORTED_BODY_CAPABILITY
BODY_LIMIT_REJECTED
BODY_DETACHED
STALE_ATTACHMENT_GENERATION
PROFILE_HASH_MISMATCH
```

D-009 codes:

```text
OBJECT_NOT_FOUND
STALE_OBJECT_VERSION
OBJECT_NOT_PERCEIVED
OBJECT_OUT_OF_RANGE
AFFORDANCE_NOT_SUPPORTED
AFFORDANCE_PRECONDITION_FAILED
OBJECT_NOT_PORTABLE
TARGET_ZONE_FULL
OBJECT_ALREADY_HELD
NO_OBJECT_HELD
HABITAT_STATE_CONFLICT
AFFORDANCE_COOLDOWN
MALFORMED_MANIPULATION_REQUEST
AFFORDANCE_DEFINITION_MISMATCH
OBJECT_DEFINITION_MISMATCH
OBJECT_ADDRESS_BINDING_STALE
OBJECT_ADDRESS_AMBIGUOUS
HOLD_SLOT_UNAVAILABLE
OBJECT_MASS_UNSUPPORTED
OBJECT_NOT_HELD_BY_BODY
PLACEMENT_POSITION_INVALID
PLACEMENT_COLLISION
TARGET_ZONE_MISMATCH
```

Do **not** introduce `BODY_CAPABILITY_UNSUPPORTED` (duplicate of `UNSUPPORTED_BODY_CAPABILITY`).

### Profile migration (D-008 → D-009)

Preserve sealed D-008 profile definitions and hashes. Add compatible D-009 profile versions supporting `MANIPULATE` plus:

```text
hold_slot_count = 1
maximum_held_mass_class
hold_anchor
```

Idempotent migration:

1. Validate sealed source D-008 profile hash.  
2. Attach compatible D-009 profile version (`origin = D009_PROFILE_MIGRATION`).  
3. Increment attachment_generation.  
4. Preserve body_instance_id where compatible.  
5. Preserve identity, physiology, memory, individuality, relationships, habitat state, location, compatible pending commitments.  
6. If held object exists: validate new hold support; atomically update held-object `attachment_generation`; else fail closed until PLACE.  
7. Unknown/incompatible source → fail closed.  
8. Second load is no-op.

Authoritative events:

```text
embodiment_body_profile_swapped
  origin = D009_PROFILE_MIGRATION
  old/new profile_id + hash
  old/new generation

habitat_held_binding_rebased   # when held object exists
  object_id, body_instance_id
  old/new attachment_generation, hold_slot
```

Do not use `habitat_profile_capability_migrated` as the sole record of body-profile migration (omit, or retain only as non-authoritative cross-domain audit). Shared transaction commits profile swap + held rebinding or neither.

Detach requires atomic governed release of held objects first, or detach fails.

### Habitat events (canonical AUTHORITATIVE registry)

Payloads/apply in `umbra_core/habitat/events.py`. Classes:

```text
habitat_initialized
habitat_zone_added
habitat_object_created
habitat_object_state_changed
habitat_object_moved              # push / free relocation
habitat_object_picked_up          # not also generic moved
habitat_object_placed             # not also generic moved
habitat_affordance_activated      # includes resulting object-state delta
habitat_affordance_deactivated
habitat_transition_applied
habitat_definition_migrated
habitat_held_binding_rebased
habitat_body_zone_transitioned
```

Every event includes: `event_id`, `habitat_id`, `transaction_id`, prior/new `state_version`, `habitat_tick`, `request_id`, `execution_id` (when applicable), actor/target refs, prior/new `state_hash`, definition version/hash.

Rules:

* One mutation must not emit overlapping generic and specific events for the same state change.  
* Multiple events in one transaction have deterministic ordering.  
* Idempotent apply; invalid order / state-hash mismatch fail closed.  
* Replay must reproduce the exact final habitat state hash.

---

## 4. Learning, routines, individuality, expression

### Verified consequence learning

A finalized VerifiedOutcome is necessary but not sufficient. Learning must verify the outcome belongs to the exact attempted execution:

```text
execution_id
request_id
target_object_id
target_address_ref
perception_evidence_ref
object_definition_hash
affordance_definition_hash
committed_habitat_version
```

Reject: stale/ambiguous address bindings; obsolete definitions (except historical evidence); denied proposals; nonterminal prepared executions; duplicate terminals.

WorldModel updates are idempotent by `execution_id`.

May learn: usefulness, zone suitability, success probability, effort/latency, object-state transitions, hazards, recovery value, prerequisites, preferences.

Must not: treat raw action frequency as preference (C11 fails); let beliefs authorize execution; write habitat.

Gate 8: sustained contradiction revises predictions; one anomaly does not erase established learning; unrelated preferences/routines remain intact; prior evidence remains inspectable.

### Environmental procedural routines

Lifecycle states (not FIFO deletion):

```text
CANDIDATE → ACTIVE → WEAKENED → INACTIVE → RETIRED
```

Retirement considers: evidence support, recency, success/failure history, contradiction, definition compatibility, duplicate coverage.

Active handles may be pruned; complete provenance remains recoverable via D-005 episodes and the event ledger.

Promotion/retirement thresholds frozen before formal execution. Routines are interruptible soft proposal sequences; each step re-enters full governance; missing/stale objects fail safely; never mutate habitat from memory.

### Environmental individuality

Bounded scoring modifiers only: exploration breadth, persistence, object/zone preference, organization, recovery location, uncertainty response, routine selection. Must not move objects, grant affordances, or write habitat/memory/identity.

### Expression / coherent render packet

`HabitatReadModel` projects from HabitatEngine snapshot. D-009 render packet binds:

```text
habitat_state_version
habitat_state_hash
organism_state_version
body_attachment_generation
execution_id
body_pose_version
```

Held-object position may be derived only when `HELD_BY.body_instance_id` matches, attachment generations match, and body pose belongs to the same compatible committed state. Mismatch → drop the packet (do not render approximately).

Must not invent object motion, show success before commit, retain stale positions, parallel-simulate habitat, or animate failed affordances as success. UI is read-only (C9 rejected).

---

## 5. Experimental conditions, scenarios, freeze

### Conditions C0–C13

As in the project directive. Isolated experimental controls: C2, C3, C9, C10. C13 is a performance baseline, not a scientific qualification condition.

Scientific meaning:

* **C2** (scripted object movement): fails causal attribution — object changes without governed organism execution. Must not qualify via high motion frequency.  
* **C3** (random manipulation): fails history dependence and action-outcome coherence. Must not qualify as learning.  
* **C10** (governance bypass): rejected with zero mutation.

Gate 2 scores:

```text
governed_action_to_mutation_alignment
unauthorized_mutation_rate
verified_outcome_alignment
correct_target_effect_rate
failed_request_world_mutation_rate
```

Required for C0:

```text
unauthorized_mutation_rate = 0
failed_request_world_mutation_rate = 0
```

### Scenarios S0–S16

As in the project directive. Scenarios may change environmental opportunities/consequences only — never preferences, habits, personality, choices, routines, WorldModel beliefs, or presentation state.

### Preregistration (commit + hash before formal experiments)

```text
experiments/d009/thresholds.json
experiments/d009/experiment-matrix.json
experiments/d009/scenario-suite.json
experiments/d009/habitat-definition.json
experiments/d009/affordance-definitions.json
```

Also freeze:

```text
maximum_manipulation_candidates_per_tick
maximum_affordances_considered_per_object
maximum_remembered_offscreen_targets
maximum_manipulation_planning_distance
routine_promotion_support_minimum
routine_active_count_maximum
routine_retirement_policy
zone_capacity_category_rules
habitat_event_storage_growth_limit
snapshot_frequency
prepared_execution_timeout
render_packet_version_compatibility_rule
P0 compatibility-mode configuration
all stable failure codes
habitat definition hash
affordance-definition hashes
D-009 body-profile hashes
migration source/destination hashes
gate-critical paired-seed count (≥100)
scenario tick budgets
object/zone bounds
manipulation latency / prediction / replay / continuity thresholds
CPU and RSS limits
adaptive performance protocol
```

Post-execution changes require a committed supplement.

---

## 6. Acceptance gates

| Gate | Pass criteria (summary) |
|------|-------------------------|
| 0 | D-001…D-008 seals validate; sealed evidence unchanged; D-008 profiles recoverable; no authority regression |
| 1 | HabitatEngine sole habitat truth; WM uncertain; UI projection; C9 rejected |
| 2 | Valid MANIPULATE commits correctly; invalid → durable fail + zero mutation; C2 fails attribution; C3 fails coherence; C10 rejected; C0 unauthorized_mutation_rate=0 and failed_request_world_mutation_rate=0 |
| 3 | Held-out environmental predictions; C4/C5 weaker; C11 not consequence learning; hidden-object leakage metrics = 0 |
| 4 | No-user autonomous environmental behavior; not scripted schedule; perception boundary held |
| 5 | Organism-caused habitat change survives restart, snapshot, birth replay, UI replacement, compatible migration; C1/C8 weaker |
| 6 | Non-authored interruptible routine from multiple independent episodes; C6 weaker; safe failure on missing/stale objects |
| 7 | Contrasting D-007 histories separate habitat use; C7 reduces separation |
| 8 | Revision under environmental change; single anomaly does not erase learning; unrelated intact |
| 9 | D-008→D-009 migration preserves organism+habitat; held rebinding atomic; unknown fails closed |
| 10 | No capability grant/self-auth/bypass/memory write/identity/relationship fabricate/over-bound overwrite; C10 rejected |
| 11 | ≥100 restarts; snapshot/birth match; idempotent events; invalid order fail closed; exactly-one terminal outcome per execution_id; retry returns existing; no double mutate; prepared recovery deterministic; habitat+organism-effect+events+outcome atomic; profile swap+held rebase atomic; no stale attachment bindings; replay reproduces exact final state_hash |
| 12 | Boundedness of objects/zones/pending/routines/cooldowns/read models; event storage growth within budget; no silent authoritative history deletion; no uncontrolled spawning |
| 13 | ≥100k accelerated ticks; adaptive P0/P1/P2 per S3 pattern on same D-009 commit; RSS/CPU absolute and Tkinter incremental limits |
| 14 | Project-goal alignment — habitat supports the persistent organism, not a game/decorative/LLM/chemistry/robotics substitute |
| 15 | All modules present; zero skipped tests; evidence hashes validate; final evidence committed; Mimir closed against final commit; clean worktree; no leftover experiment/renderer/Xvfb/runtime processes; only an allowed verdict |

### Adaptive performance (Gate 13)

```text
warm-up: 300 s
initial measurement: 1800 s
extension: +900 s only when ambiguous
maximum measurement: 3600 s per mode
```

Modes (same D-009 commit, habitat definition, starting state, organism seed, tick rate, warm-up, tooling):

```text
P0  HabitatEngine compatibility mode:
      HabitatEngine sole authority; legacy D-008 behavior preserved;
      MANIPULATE candidates, affordance execution, environmental routines,
      and D-009 dynamics disabled
P1  Full D-009 habitat agency + HeadlessRenderer
P2  Full D-009 habitat agency + TkinterRenderer
```

Limits:

```text
RSS p95 ≤ 180 MiB
RSS slope ≤ 1 MiB/hour
CPU mean ≤ 5% of one logical core
Tkinter incremental RSS p95 ≤ 128 MiB
Tkinter incremental slope ≤ 1 MiB/hour
Tkinter incremental CPU mean ≤ 5% of one logical core
```

Do not require a fixed two-hour soak.

---

## 7. Minimum tests

`tests/test_d009.py` must include the project-directive minimum list plus:

**Own-and-delegate / projection**

```text
test_habitat_engine_is_only_writer
test_embodiment_habitat_projection_is_read_only
test_projection_matches_authoritative_version_and_hash
test_projection_mismatch_fails_closed
test_expression_reads_habitat_engine_snapshot
test_legacy_reads_do_not_create_second_authority
test_birth_replay_rebuilds_projection_from_habitat_events
```

**Addressability / definitions / exactly-once / coherence**

```text
test_hidden_objects_do_not_generate_manipulation_candidates
test_manipulate_requires_current_address_binding
test_stale_object_address_binding_fails_closed
test_ambiguous_object_address_binding_fails_closed
test_object_definition_mismatch_fails_closed
test_affordance_definition_mismatch_fails_closed
test_profile_definition_mismatch_fails_closed
test_manipulation_parameters_are_typed_and_bounded
test_adapter_cannot_change_operation_or_target
test_execution_id_has_exactly_one_terminal_outcome
test_successful_execution_cannot_mutate_twice
test_failed_execution_cannot_execute_after_restart
test_prepared_execution_recovers_deterministically
test_world_model_update_is_idempotent_by_execution
test_resource_and_organism_effect_commit_atomically
test_profile_swap_rebases_held_object_generation_atomically
test_incompatible_profile_swap_with_held_object_fails
test_held_object_render_requires_matching_generation
test_render_packet_uses_coherent_habitat_and_body_versions
test_scripted_object_motion_does_not_count_as_autonomy
test_random_manipulation_does_not_count_as_learning
test_authoritative_event_history_is_not_silently_deleted
```

Final sealed suite: zero skips. Add focused tests for every defect discovered.

---

## 8. Evidence & seal

Required evidence paths under `docs/evidence/d009/` as listed in the project directive (prior-seals, schema-manifest, per-gate result JSONs, evidence-hashes, final-verdict).

Hash manifest includes: directive, design, implementation plan, thresholds, matrix, scenario suite, habitat definition, affordance definitions, body-profile definitions, source files, tests, all result files, final verdict.

Allowed verdicts only:

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

D-010 is authorized only under `UMBRA_D009_PERSISTENT_HABITAT_AGENCY_QUALIFIED`.

---

## 9. Completion condition

D-009 is complete only when evidence demonstrates that the qualified UMBRA individual autonomously perceives, learns, uses, and persistently modifies a bounded digital habitat through governed environmental affordances; develops non-authored environmental preferences and routines; preserves organism and habitat continuity across restart, replay, and compatible body-capability migration; and remains measurably dependent on accumulated history rather than scripted environmental behavior.

The result must be a persistent creature inhabiting a world, not an animation moving through a decorative scene.

---

## Spec self-review notes (resolved)

* No TBD/TODO placeholders remain for architectural authority. Numeric freeze values are intentionally deferred to committed preregistration JSON (explicitly gated before formal experiments).  
* Embodiment no longer owns habitat truth (D-008 design superseded for habitat authority in D-009; D-008 sealed profiles/hashes preserved).  
* `BODY_CAPABILITY_UNSUPPORTED` excluded; `UNSUPPORTED_BODY_CAPABILITY` retained.  
* `habitat_profile_capability_migrated` is not authoritative for profile migration.  
* P0 is compatibility mode on the D-009 commit, not a separate D-008 binary.  
* AffordanceEngine organism effects are proposals only; physiology authority unchanged.  
* Event growth uses a storage budget; authoritative history is not silently deleted.
