# UMBRA-D-008 Coherent Digital Embodiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Qualify body-independent digital embodiment and nonverbal expression so the same persistent UMBRA individual is visibly present in a habitat whose presentation causally reflects the D-001…D-007 organism core.

**Architecture:** Side-car expression loop. Governance routes body execution through a thin `EmbodimentAdapter` that enforces profile limits then delegates to `Embodiment`. After each committed tick outcome, `ExpressionEngine.derive` builds a coherent `RenderPacket` (presentation + immutable habitat read model) into a bounded non-authoritative frame ring. `HeadlessRenderer` / `TkinterRenderer` poll non-destructively. Attachment/detach/swap (+ D007→D008 migration) are authoritative events; frames are never snapshotted.

**Tech Stack:** Python 3 stdlib + SQLite WAL (`umbra_core`), `tkinter` for visible soak only, pytest. No new third-party dependencies.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-23-umbra-d008-coherent-digital-embodiment-design.md` (tip includes `40236da` amendments)
- Directive: `docs/directives/UMBRA-D-008-coherent-digital-embodiment.md`
- Starting commit: `bc7bfaa`; design commits: `a2371ab`, `40236da`
- Mimir project: `7777645d52a91b49`; task: `cbbb61834c98463cb70fb9254ba08ea2`; agent directive: `D-20260723-umbra-d008-coherent-digital-embodiment`
- Capability names: `IDLE|ORIENT|MOVE|APPROACH|RETREAT|INSPECT|REST|CHARGE|SIGNAL_PLAY|SIGNAL_ASSISTANCE` only — never invent `MAINTAIN`/`PRACTICE`
- `core` / `experiments` never import `ui/`; `ui/` may import `umbra_core.expression`
- C1/C2/C3/C7/C8/CONSTRAINED_TEST_BODY live only under `experiments/d008/`
- C10 = expression+renderers disabled (perf baseline), not a Gate 1–10 scientific ablation
- Expression/frame state never in organism snapshots
- Final sealed suite: zero skips
- Do not edit `.agent/RECORD.md`
- Ponytail: smallest correct diff; reuse D-006/D-007 harness patterns

## File map

| Path | Responsibility |
|------|----------------|
| `umbra_core/embodiment_adapters/__init__.py` | Public exports |
| `umbra_core/embodiment_adapters/profiles.py` | Production profiles + hash helpers |
| `umbra_core/embodiment_adapters/adapter.py` | EmbodimentAdapter execute/attach/swap/reject |
| `umbra_core/expression/__init__.py` | Public exports |
| `umbra_core/expression/presentation_state.py` | PresentationState, postures, channels |
| `umbra_core/expression/habitat_read_model.py` | Immutable bounded habitat projection |
| `umbra_core/expression/engine.py` | ExpressionEngine.derive → RenderPacket |
| `umbra_core/expression/frame_ring.py` | FrameRingEntry + ring + cursors |
| `umbra_core/expression/renderer.py` | ReferenceRenderer protocol |
| `umbra_core/expression/headless_renderer.py` | HeadlessRenderer |
| `ui/reference_companion/tkinter_renderer.py` | TkinterRenderer (Canvas) |
| `ui/reference_companion/habitat_view.py` | Canvas draw helpers |
| `ui/reference_companion/diagnostics.py` | Optional diagnostic panel |
| `umbra_core/events.py` | Attachment event authority |
| `umbra_core/governance.py` | Route execute via adapter |
| `umbra_core/runtime.py` | Adapter + derive wiring; migration on load |
| `umbra_core/persistence.py` | Atomic attachment + failed-outcome commits as needed |
| `experiments/d008/thresholds.json` | Frozen gates + freeze additions |
| `experiments/d008/experiment-matrix.json` | C0–C10 × S0–S12 cells |
| `experiments/d008/scenario-suite.json` | Scenario definitions |
| `experiments/d008/constrained_profile.py` | CONSTRAINED_TEST_BODY |
| `experiments/d008/diagnostic_controllers.py` | C1/C2/C3 only |
| `experiments/d008/run_experiment.py` | Paired-seed harness |
| `experiments/d008/run_performance.py` | 100k + 2h soak (C10/headless/tk) |
| `experiments/d008/run_seal.py` | Seal aggregator |
| `tests/test_d008.py` | All directive minimum tests |
| `docs/evidence/d008/*` | Evidence pack |

---

### Task 1: Freeze preregistration artifacts

**Files:**
- Create: `experiments/d008/thresholds.json`
- Create: `experiments/d008/experiment-matrix.json`
- Create: `experiments/d008/scenario-suite.json`
- Modify: `.agent/CURRENT.md`, `.agent/REPO_MAP.md`

**Interfaces:**
- Produces: frozen numbers consumed by all later harnesses/tests

- [ ] **Step 1: Write `experiments/d008/thresholds.json`**

Include at minimum (adjust only with recorded supplement after formal run):

```json
{
  "minimum_gate_critical_paired_seeds": 100,
  "ci_confidence": 0.95,
  "action_expression_alignment_min": 0.90,
  "physiology_condition_alignment_min": 0.80,
  "attention_target_accuracy_min": 0.85,
  "attention_confidence_display_threshold": 0.55,
  "contradictory_expression_rate_max": 0.05,
  "stale_frame_rate_max": 0.02,
  "action_onset_latency_ticks_max": 3,
  "interruption_latency_ticks_max": 3,
  "body_swap_fingerprint_l2_max": 0.22,
  "replay_equivalence_l2_max": 0.05,
  "individuality_expression_separation_min": 0.12,
  "autonomous_visible_action_coverage_min": 0.40,
  "renderer_write_authority_violations_max": 0,
  "accepted_generation_mismatch": 0,
  "accepted_state_version_mismatch": 0,
  "accepted_incoherent_habitat_packet": 0,
  "obsolete_execution_rendered_as_current": 0,
  "frame_ring_capacity": 64,
  "frame_ring_retention_ticks": 128,
  "habitat_read_model_max_entities": 64,
  "habitat_read_model_max_bytes": 65536,
  "source_event_refs_max": 16,
  "renderer_cadence_hz": 10,
  "tkinter_diagnostics_visible_for_soak": false,
  "display_mode": "auto",
  "virtual_display_command": "Xvfb :99 -screen 0 1280x720x24",
  "default_migration_profile_id": "ABSTRACT_SHAPE_BODY",
  "production_profile_ids": ["ABSTRACT_SHAPE_BODY", "MINIMAL_CREATURE_BODY"],
  "production_profile_definition_hashes": {
    "ABSTRACT_SHAPE_BODY": "PLACEHOLDER_COMPUTE_AT_FREEZE",
    "MINIMAL_CREATURE_BODY": "PLACEHOLDER_COMPUTE_AT_FREEZE"
  },
  "adapter_failure_codes": [
    "UNSUPPORTED_BODY_CAPABILITY",
    "BODY_LIMIT_REJECTED",
    "BODY_DETACHED",
    "STALE_ATTACHMENT_GENERATION",
    "PROFILE_HASH_MISMATCH"
  ],
  "ticks_accelerated_min": 100000,
  "soak_seconds_min": 7200,
  "rss_p95_mib_max": 180,
  "rss_slope_mib_per_hour_max": 1.0,
  "cpu_mean_frac_max": 0.05,
  "ui_incremental_rss_p95_mib_max": 128,
  "ui_incremental_rss_slope_mib_per_hour_max": 1.0,
  "ui_incremental_cpu_mean_frac_max": 0.05,
  "restarts_continuity_min": 100
}
```

After writing production profiles in Task 2, replace `PLACEHOLDER_COMPUTE_AT_FREEZE` with real SHA-256 of canonical profile JSON (stable field order). Amend this file in the same freeze commit once hashes exist — or freeze hashes in Task 2 commit with a note that formal execution starts after that commit.

- [ ] **Step 2: Write `experiments/d008/experiment-matrix.json`**

Document C0–C10 meanings (C10 = expression disabled perf baseline). List gate-critical cells with `paired_seeds: 100` for every Gate 1–10 comparison. Include S0–S12 refs.

- [ ] **Step 3: Write `experiments/d008/scenario-suite.json`**

Define S0–S12: environment/opportunity manipulations only (no direct expression commands). Include seed lists or seed ranges, tick budgets, partner/history plants where needed.

- [ ] **Step 4: Commit**

```bash
git add experiments/d008/*.json .agent/CURRENT.md .agent/REPO_MAP.md
git commit -m "Freeze UMBRA-D-008 preregistration thresholds, matrix, and scenarios."
```

---

### Task 2: Production body profiles + hash helper

**Files:**
- Create: `umbra_core/embodiment_adapters/__init__.py`
- Create: `umbra_core/embodiment_adapters/profiles.py`
- Create: `experiments/d008/constrained_profile.py`
- Test: `tests/test_d008.py` (initial tests)
- Modify: `experiments/d008/thresholds.json` (real profile hashes)

**Interfaces:**
- Produces: `BodyProfile` dataclass; `get_profile(profile_id) -> BodyProfile`; `profile_definition_hash(profile) -> str`; `ABSTRACT_SHAPE_BODY`, `MINIMAL_CREATURE_BODY`; experimental `CONSTRAINED_TEST_BODY`

```python
@dataclass(frozen=True)
class BodyProfile:
    profile_id: str
    schema_version: str
    supported_capabilities: frozenset[str]
    physical_limits: dict[str, float]  # e.g. max_step, turn_rate
    presentation_mapping: dict[str, Any]  # geometry, posture map, signal icons
```

Both production profiles support the full capability set. Constrained profile rejects ≥1 capability (e.g. drop `SIGNAL_ASSISTANCE`), lowers `max_step`, omits ≥1 presentation feature.

- [ ] **Step 1: Write failing tests**

```python
def test_two_production_profiles_support_full_capability_set():
    ...

def test_constrained_profile_rejects_at_least_one_capability():
    ...

def test_profile_definition_hash_is_stable():
    ...
```

- [ ] **Step 2: Implement profiles + hash; update thresholds hashes; pass tests; commit**

```bash
git commit -m "Add D-008 production and constrained body profiles with stable hashes."
```

---

### Task 3: EmbodimentAdapter — attach/swap + durable rejection

**Files:**
- Create: `umbra_core/embodiment_adapters/adapter.py`
- Modify: `umbra_core/events.py` (AUTHORITATIVE attach/detach/swap)
- Modify: `umbra_core/governance.py` and/or `umbra_core/runtime.py` (route execute)
- Modify: `umbra_core/persistence.py` if atomic commit helper needed
- Test: `tests/test_d008.py`

**Interfaces:**
- Produces:

```python
class EmbodimentAdapter:
    def attach(self, profile_id: str, *, origin: str = "NORMAL") -> None: ...
    def detach(self, reason: str) -> None: ...
    def swap_profile(self, new_profile_id: str) -> None: ...
    def execute(self, request: AdapterRequest, embodiment: Embodiment, rng) -> dict[str, Any]:
        """Validate; on reject return failed raw (no Embodiment.execute); else delegate."""
```

Rejection raw must include: `ok_raw=False`, `failure_code`, `execution_id`, `request_id`, `body_instance_id`, `body_profile_id`, `attachment_generation`, `capability`, `profile_constraint`, `tick`. Codes: `UNSUPPORTED_BODY_CAPABILITY|BODY_LIMIT_REJECTED|BODY_DETACHED|STALE_ATTACHMENT_GENERATION|PROFILE_HASH_MISMATCH`.

Governance path: `execute_and_verify` accepts optional adapter; if present, call `adapter.execute` instead of `embodiment.execute_primitive`. VerifiedOutcome from reject must be durable via existing `outcome_verified` (or equivalent) **before** expression derive. Crash/replay: rejected request never executes after restart; duplicate apply idempotent.

- [ ] **Step 1: Failing tests** — `test_adapter_cannot_grant_capabilities`, `test_unsupported_body_action_fails_safely`, `test_adapter_rejection_commits_failed_outcome_without_world_mutation`, `test_adapter_rejection_replay_idempotent`

- [ ] **Step 2: Implement + wire + green + commit**

```bash
git commit -m "Add EmbodimentAdapter with durable rejection and profile attach/swap."
```

---

### Task 4: D007→D008 attachment migration

**Files:**
- Modify: `umbra_core/embodiment_adapters/adapter.py` or `umbra_core/runtime.py` (`load_organism` / create path)
- Test: `tests/test_d008.py`

**Interfaces:**
- Produces: `maybe_migrate_d008_attachment(store, organism) -> bool`  
  Detect pre-D008 schema; append `embodiment_body_attached` with `origin=D008_MIGRATION`, default profile from frozen thresholds, stable `body_instance_id`, schema version + definition hash; atomic; idempotent.

- [ ] **Step 1: Failing tests** — migrate once; second load no-op; birth replay includes migration event; no phys/memory/social/individuality/habitat reset; post-migration missing attach fails closed

- [ ] **Step 2: Implement + green + commit**

```bash
git commit -m "Add idempotent D-007 to D-008 body attachment migration."
```

---

### Task 5: PresentationState + habitat read model + ExpressionEngine

**Files:**
- Create: `umbra_core/expression/presentation_state.py`
- Create: `umbra_core/expression/habitat_read_model.py`
- Create: `umbra_core/expression/engine.py`
- Create: `umbra_core/expression/__init__.py`
- Test: `tests/test_d008.py`

**Interfaces:**

```python
@dataclass
class PresentationState:  # fields per design §2; no mood fields; no wall-clock

@dataclass(frozen=True)
class HabitatReadModel:
    entities: tuple[FrozenEntity, ...]
    version: int
    # bounded construction from Embodiment.to_state()

@dataclass(frozen=True)
class RenderPacket:
    presentation_state: PresentationState
    habitat_read_model: HabitatReadModel
    source_state_version: int
    habitat_state_version: int
    body_attachment_generation: int

class ExpressionEngine:
    def derive(self, view: ExpressionView) -> RenderPacket:
        """Every tick including no-action; DETACHED → empty body fields."""
```

`ExpressionView` is a read-only bundle: physiology, last outcome, attention/perception, individuality summary, developmental markers, attachment metadata, embodiment state snapshot — **no mutators**.

- [ ] **Step 1: Failing tests** — `test_expression_engine_cannot_select_actions`, `test_no_mood_or_emotion_authority_fields`, `test_physiology_is_not_modified_by_expression`, `test_fatigue_changes_visible_condition`, `test_rest_changes_posture_and_activity`, `test_uncertain_attention_remains_ambiguous`, `test_denied_action_is_not_rendered_as_executed`, `test_failed_action_renders_interruption`

- [ ] **Step 2: Implement + green + commit**

```bash
git commit -m "Add ExpressionEngine and body-neutral PresentationState derivation."
```

---

### Task 6: Frame ring with embedded RenderPacket

**Files:**
- Create: `umbra_core/expression/frame_ring.py`
- Test: `tests/test_d008.py`

**Interfaces:**

```python
@dataclass(frozen=True)
class FrameRingEntry:
    frame_id: int
    derived_at_tick: int
    active_execution_id: str | None
    render_packet: RenderPacket
    source_event_refs: tuple[str, ...]

class FrameRing:
    def __init__(self, capacity: int, retention_ticks: int): ...
    def push(self, entry: FrameRingEntry) -> None:  # drop oldest / stale on backpressure
    def read_latest(self, cursor: RendererCursor) -> FrameRingEntry | None:  # non-destructive
    def clear(self) -> None
```

Stale if generation/state-version/execution mismatch vs current validity predicates. Habitat must come from packet — never rebuild at read.

- [ ] **Step 1: Failing tests** — `test_expression_transition_buffers_are_bounded`, `test_stale_expression_frames_are_rejected`, `test_expression_frame_source_refs_are_valid`, multi-cursor non-destructive, generation bump invalidates pre-swap frames

- [ ] **Step 2: Implement + green + commit**

```bash
git commit -m "Add bounded FrameRing storing coherent RenderPackets."
```

---

### Task 7: HeadlessRenderer + runtime side-car wire

**Files:**
- Create: `umbra_core/expression/renderer.py`
- Create: `umbra_core/expression/headless_renderer.py`
- Modify: `umbra_core/runtime.py` — after outcome commit: `derive` → `frame_ring.push`; expose ring; C10 disable expression
- Test: `tests/test_d008.py`

**Interfaces:**

```python
class ReferenceRenderer(Protocol):
    def read_latest(self, ring: FrameRing) -> FrameRingEntry | None: ...
    def render(self, entry: FrameRingEntry) -> None: ...
    def set_diagnostics_visible(self, visible: bool) -> None: ...
    def close(self) -> None: ...
```

Organism tick must not block on renderer. Closing headless is a no-op for core.

- [ ] **Step 1: Failing tests** — `test_autonomous_activity_continues_without_user`, `test_rest_and_inactivity_are_valid_visible_states`, `test_renderer_does_not_fake_autonomy`, `test_habitat_state_is_not_duplicated`, `test_action_expression_alignment`

- [ ] **Step 2: Wire + green + commit**

```bash
git commit -m "Wire ExpressionEngine side-car and HeadlessRenderer into runtime."
```

---

### Task 8: Restart, replay, body-swap continuity

**Files:**
- Modify: `umbra_core/runtime.py`, adapter, events, persistence as needed
- Test: `tests/test_d008.py`

- [ ] **Step 1: Failing tests** — `test_restart_preserves_body_position`, `test_restart_preserves_visible_condition`, `test_interrupted_action_resolves_after_restart`, `test_snapshot_replay_matches`, `test_birth_replay_matches_authoritative_transitions`, `test_missing_embodiment_event_fails_closed`, `test_body_profile_swap_preserves_{identity,memory,relationships,individuality}`, `test_avatar_identifier_absent_from_constitutional_identity`, `test_ui_identifier_absent_from_individuality_state`

- [ ] **Step 2: Implement continuity contracts + green + commit**

```bash
git commit -m "Prove D-008 restart, replay, and body-swap continuity contracts."
```

---

### Task 9: Tkinter reference companion

**Files:**
- Create: `ui/reference_companion/__init__.py`
- Create: `ui/reference_companion/habitat_view.py`
- Create: `ui/reference_companion/diagnostics.py`
- Create: `ui/reference_companion/tkinter_renderer.py`
- Test: `tests/test_d008.py` (import isolation + optional skip only if no display for unit tests that need Canvas — formal soak later must not skip)

**Rules:** Habitat canvas = shapes/orientation/posture/attention/icons only. Capability/phase/versions in diagnostics. `close()` unregisters cursor, destroys window, leaves organism running. Organism tick off Tk thread; thread-safe handoff. Verify `import experiments` / `umbra_core` modules do not import `ui`.

- [ ] **Step 1: Failing tests** — `test_reference_interface_runs_without_diagnostics`, `test_two_body_profiles_render_same_organism`, `test_renderer_cannot_write_core_state`, experiments never import ui

- [ ] **Step 2: Implement + green + commit**

```bash
git commit -m "Add Tkinter reference companion over headless presentation model."
```

---

### Task 10: Nonverbal signals + individuality presentation

**Files:**
- Modify: `umbra_core/expression/engine.py`
- Test: `tests/test_d008.py`

- [ ] **Step 1: Failing tests** — `test_signal_play_is_visibly_expressed`, `test_signal_assistance_is_visibly_expressed`, `test_signal_does_not_directly_change_relationship`, `test_individuality_history_changes_visible_behavior`, `test_renderer_does_not_create_authored_personality`, `test_learned_habit_is_visibly_expressed`, `test_shared_routine_is_visibly_expressed`, `test_recovery_restores_visible_activity`, `test_orientation_matches_selected_target`, `test_cosmetic_motion_is_non_authoritative`

- [ ] **Step 2: Implement channel mapping + green + commit**

```bash
git commit -m "Map signals, individuality, and habits into visible expression channels."
```

---

### Task 11: Isolated ablations C1–C10

**Files:**
- Create: `experiments/d008/diagnostic_controllers.py`
- Create: `experiments/d008/hostile_renderer.py` (C7 test double — attempts prohibited writes)
- Modify: `umbra_core/expression/engine.py` / runtime condition switches for C4/C5/C6/C9/C10 where production-config flags are needed (C1–C3/C7/C8 stay experimental-only)
- Test: `tests/test_d008.py`

- [ ] **Step 1: Failing tests** — `test_scripted_animation_condition_is_isolated`, `test_random_expression_condition_is_isolated`, `test_scalar_mood_controller_is_isolated`, plus C7 write rejection, C8 disposable-DB only assertion helpers

- [ ] **Step 2: Implement + green + commit**

```bash
git commit -m "Isolate D-008 ablation conditions C1–C10 under experiments."
```

---

### Task 12: Complete `tests/test_d008.py` minimum list + prior seals

**Files:**
- Modify: `tests/test_d008.py`
- Create: helpers as needed under `tests/` or `experiments/d008/`

Ensure every directive §16 name exists. Gate 12 soak tests may be marked for harness invocation but must not remain `pytest.mark.skip` at seal — follow D-006/D-007 pattern: run via `run_performance` / seal, assert artifacts in tests that read evidence or run bounded shortened checks in CI plus full soak in seal.

Include: `test_d001_through_d007_seals_unchanged`, `test_prior_behavior_regressions_within_bounds`, `test_no_deferred_modules`, `test_100k_tick_boundedness`, `test_two_hour_visible_runtime_soak` (seal path).

- [ ] **Step 1: Cross-check directive list; add missing tests**
- [ ] **Step 2: `pytest tests/test_d008.py -q` green (pre-soak skips only if explicitly matching D-006 interim pattern — remove before seal)**
- [ ] **Step 3: Commit**

```bash
git commit -m "Complete D-008 minimum test coverage against directive list."
```

---

### Task 13: Experiment harness + evidence (Gates 1–11)

**Files:**
- Create: `experiments/d008/run_experiment.py`
- Create: `experiments/d008/run_closeout.py` (optional interim)
- Create: `docs/evidence/d008/*.json` results + `render-coherence-results.json`

- [ ] **Step 1: Implement paired-seed ProcessPool harness reading frozen matrix/thresholds unmodified**
- [ ] **Step 2: Run gate-critical cells; write evidence JSONs; assert numeric gates**
- [ ] **Step 3: Commit evidence**

```bash
git commit -m "Run D-008 experiment matrix and record gate evidence."
```

---

### Task 14: Performance — 100k + 2h visible soak + seal

**Files:**
- Create: `experiments/d008/run_performance.py`
- Create: `experiments/d008/run_seal.py`
- Modify: `tests/test_d008.py` (unskip Gate 12 if needed)
- Create: `docs/evidence/d008/performance-*.json`, `soak-2h*`, `prior-seals.json`, `schema-manifest.json`, `evidence-hashes.json`, `final-verdict.md`
- Modify: `.agent/PROJECT_GOAL.md`, `.agent/PROJECT_PROFILE.md`, `.agent/CURRENT.md`, `.agent/OUTCOMES.md`, `.agent/REPO_MAP.md`

**Soak methodology (frozen):** same seed/scenario/tick rate/duration/diagnostics/warmup/`RUNTIME_READY` for:

1. C10 core only  
2. core + ExpressionEngine + HeadlessRenderer  
3. core + ExpressionEngine + TkinterRenderer (real Canvas + event loop)

Report `expression_over_core`, `tkinter_over_headless`, `tkinter_over_core`. No display → fail closed or preregistered Xvfb — never silent headless substitute.

- [ ] **Step 1: Run 100k boundedness**
- [ ] **Step 2: Run 2h triple comparison soak**
- [ ] **Step 3: `run_seal.py` — prior seals, zero-skip `pytest tests/`, hashes, verdict**
- [ ] **Step 4: Commit seal; close Mimir against final commit; confirm clean worktree**

```bash
git commit -m "Seal UMBRA-D-008 coherent digital embodiment with performance evidence."
```

Allowed QUALIFIED verdict only if all gates pass: `UMBRA_D008_COHERENT_DIGITAL_EMBODIMENT_QUALIFIED`.

---

## Spec coverage checklist (self-review)

| Spec requirement | Task |
|------------------|------|
| ExpressionEngine + PresentationState | 5 |
| FrameRing stores RenderPacket w/ habitat | 6 |
| Headless + Tkinter renderers | 7, 9 |
| Thin EmbodimentAdapter | 3 |
| Two prod profiles + constrained | 2 |
| Migration D007→D008 | 4 |
| Durable adapter rejection | 3 |
| Runtime side-car derive | 7 |
| Restart/replay/swap | 8 |
| Signals / individuality / habits | 10 |
| C1–C10 isolation | 11 |
| Freeze files + hashes/cadence/etc. | 1–2 |
| Full tests | 12 |
| Experiments + evidence | 13 |
| 100k + 2h soak + seal | 14 |
| Import rule core↛ui | 9 |
| C7 hostile double | 11 |
| Render coherence metrics | 6, 13 |

No TBD/TODO placeholders remain in task bodies above.
