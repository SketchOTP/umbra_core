# REPO_MAP.md

Concise navigation map for agents. Add entries as application code lands.

## Governance
- `.agent/PROJECT_GOAL.md` — product SoT (companion organism core; chemistry optional/non-gating)
- `.agent/PROJECT_PROFILE.md` — identity, Mimir binding `7777645d52a91b49`, program status (D-009 QUALIFIED; D-010 in progress)
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
- D-006 evidence (**SEALED QUALIFIED**, Task 13): `docs/evidence/d006/` — experiment-summary + recognition/contingency/history/reliability/satiation/absence/routine/governance/manipulation/replay/event-authority-results.json; Gate 12 perf: performance-results.json + performance-100k.json + soak-2h-summary.json + soak-2h.jsonl; prior-seals.json + schema-manifest.json; final-verdict.md (`UMBRA_D006_SOCIAL_CONTINGENCY_QUALIFIED`); evidence-hashes.json (design+thresholds+matrix+sources+tests+all results); test-results.txt
- D-006 performance harness: `experiments/d006/run_performance.py` (100k accelerated + 2h RUNTIME_READY VmRSS soak, social+memory+world enabled, social_history H0; thresholds from frozen thresholds.json; modes 100k/soak/all recompose performance-results.json)
- D-006 final seal: `experiments/d006/run_seal.py` (validates prior seals d001/d002p/d003/d004/d005 tolerating flat + d002p nested {hashes} formats, writes prior-seals.json + schema-manifest.json, runs full `pytest tests/` for zero-skip, emits final-verdict.md, recomputes evidence-hashes.json; verdict QUALIFIED only if Gate 12 + priors + zero-skip suite pass; argv[1]=ending commit)
- D-006 tests: `tests/test_d006.py` (Task 2–8: merge/split provenance, swap detection, reliability revision, soft proposals, shared routine promotion; Task 11: full directive+design §8 minimum-test-list coverage — satiation decline, absence non-escalation/non-frequency/non-viability-damage/non-punishment, different-histories behavior, `pytest.mark.skip`'d pre-soak Gate 12 placeholder for Task 13)
- D-006 social engine: `umbra_core/social/` — `engine.py`: `SocialEngine`/`PartnerHypothesis`/`ContingencyCell`/`PendingInteraction`/`RoutineHandle`/`ResponseClass`/`condition_to_social_config` (C0–C9 complete: C1 familiarity-only, C2 pooled partner, C3 baseline/no production affection, C4 no persist+reset, C5 no satiation, C6 no recognition, C7 random actions, C8 scripted routine, C9 randomized timing; recognition, derived satiation/expected_response_latency; `create_pending`/`classify_response`/`observe_outcome`/`resolve_pending` atomic commit; `resume_pending`/`reconstruct_pending` restart+fail-closed; Task 6: merge/split provenance, swap detection, reliability revision; Task 8: routine promotion; Task 9: `experiments/d006/affection_controller.py` C3-only `AffectionController`; Task 10: `accepted_state()` for birth/snapshot replay equality (excludes non-deterministic Governance-sourced `execution_id`); `MAX_ROUTINE_HANDLES` cap + `_prune_routine_handles()` FIFO eviction, `_prune_hypotheses()` now interrupts routines of evicted hypotheses so `routine_handles` stays bounded across the full hypothesis lifetime, not just the active set)
- D-006 Task 10 (persistence/restart/replay, Gate 11): snapshot already carried `social` via `Organism.authoritative_state()`/`load_organism()` (prior tasks) — `umbra_core/runtime.py`'s `resimulate()` now also compares `social_accepted`; tests: `tests/test_d006.py::test_restart_preserves_partner_models`, `test_birth_and_snapshot_replay_match`, `test_partner_and_routine_counts_are_bounded`, `test_prior_seals_validate` (adds d005 seal), `test_prior_regressions_pass`, `test_no_deferred_modules_added`
- D-006 atomic commit: `umbra_core/persistence.py` — `Store.atomic_social_outcome` + `social_evidence_links` + `social_hypothesis_provenance_links`; `umbra_core/memory/engine.py` — `finalize_social_episode`/`attach_episode`/`promote_social_routine`/`select_social_routine`/`SocialRoutineSpec`; `umbra_core/events.py` — social lifecycle + `social_partner_swap_detected` + `social_routine_promoted`/`social_routine_deactivated` AUTHORITATIVE
- `umbra_core/perception.py` — habitat + partner cue membrane (`partner_cues` in policy_view); identity-signature noise floor `_PARTNER_IDENTITY_NOISE_SIGMA=0.14` < spatial noise so distinct partners stay separable (Task 12 Critical fix)
- `umbra_core/embodiment.py` — habitat plant + `SIGNAL_*` + `PartnerEntity`/`apply_social_history`/`hidden_partner_truth_for_eval`; `PartnerTrueCues.for_history` uses antipodal per-index identity basis (`_identity_offsets`, noise-free inter-partner cue distance ~0.69; ambiguous H9 tiny amplitude) — Task 12 Critical fix, frozen threshold unchanged
- D-006 organism recognition (real-path Gate 3): `experiments/d006/run_experiment.py::_organism_recognition` + `tests/test_d006.py::test_organism_h8_distinct_partners_do_not_silently_merge`/`test_organism_h9_ambiguous_partners_are_not_split_into_distinct_identities`


## Organism kernel (D-007)
- `umbra_core/individuality/` — lived individuality / history-shaped dispositions
  - `engine.py` — IndividualityEngine / DispositionEstimate / VerifiedEvidence / condition_to_individuality_config
- D-007 directive: `docs/directives/UMBRA-D-007-lived-individuality.md`
- D-007 design: `docs/superpowers/specs/2026-07-22-umbra-d007-lived-individuality-design.md`
- D-007 preregistration: `experiments/d007/{thresholds,experiment-matrix,probe-suite}.json`
- D-007 harness: `experiments/d007/run_experiment.py`, `run_performance.py`, `run_seal.py`, `history_schedules.py`, `fingerprint.py`, `diagnostic_controllers.py` (C2/C3 only)
- D-007 tests: `tests/test_d007.py`
- D-007 evidence: `docs/evidence/d007/`
- Runtime: `OrganismConfig.individuality_enabled` + history plant `Embodiment.apply_individuality_history`; arbitration `individuality_apply` modifiers; authoritative individuality events in `events.py`

## Digital embodiment (D-008) — QUALIFIED (`UMBRA_D008_COHERENT_DIGITAL_EMBODIMENT_QUALIFIED`)
- Design: `docs/superpowers/specs/2026-07-23-umbra-d008-coherent-digital-embodiment-design.md`
- Directive: `docs/directives/UMBRA-D-008-coherent-digital-embodiment.md`
- Preregistration (frozen Task 1, hash-amended Task 2): `experiments/d008/thresholds.json`, `experiments/d008/experiment-matrix.json`, `experiments/d008/scenario-suite.json` — production profile definition hashes are real SHA-256 values
- Task 13 harness (complete, Gates 1–11): `experiments/d008/run_experiment.py`, `experiments/d008/evidence.py`, `experiments/d008/validate_evidence.py`
- Task 14 performance (complete, Supplement S3): `experiments/d008/run_performance.py`, `experiments/d008/run_seal.py`, `experiments/d008/performance-protocol.json`, `experiments/d008/with_tk_display.sh`; evidence `docs/evidence/d008/performance-*.json`, `accelerated-100k-results.json`, `renderer-lifecycle-results.json`, `soak-P{0,1,2}.jsonl`, `final-verdict.md`
- Expression (Tasks 5-6, D-009 Task 9): `umbra_core/expression/presentation_state.py` (`PresentationState` — mutable dataclass, design §2 fields exactly, no mood/emotion/personality/wall-clock field; `POSTURES`/`ACTION_PHASES` constants); `umbra_core/expression/habitat_read_model.py` (`FrozenEntity` with optional `held_*` fields, `HabitatReadModel.from_habitat_snapshot(snapshot, body_pose=)` authoritative D-009 path + legacy `from_embodiment_state` D-008 path); `umbra_core/expression/engine.py` (`ExpressionView` optional `habitat_snapshot`/`body_pose`/`body_pose_version`, `RenderPacket` binds habitat version/hash + organism version + execution_id + body_pose_version); `umbra_core/expression/frame_ring.py` (`_packet_is_coherent`, cursor `body_pose_version` rejection). `ExpressionEngine.derive(view)->RenderPacket` — no execute/select_action/propose method, no channel to Governance/Embodiment; denied outcome (`admitted=False`) renders IDLE/no active_capability, admitted-but-failed renders posture/action_phase=INTERRUPTED with active_capability still set; DETACHED nulls all body fields but habitat still renders; attention below `ATTENTION_CONFIDENCE_DISPLAY_THRESHOLD` (0.55) hides target only, keeps raw confidence); `FrameRingEntry` stores full `RenderPacket` including habitat snapshot, `FrameRing.from_thresholds()` uses frozen 64/128 capacity/retention, `RendererCursor` supports non-destructive per-renderer reads and rejects stale generation/state-version/execution/pose frames). Runtime still uses legacy embodiment path when `habitat_snapshot` unset (Task 10 wire).
- FrameRing (Task 6): `umbra_core/expression/frame_ring.py` — `FrameRingEntry` (stores the full `RenderPacket`, not just presentation), `RendererCursor`, `FrameRing` (bounded capacity/retention from thresholds.json, non-destructive `read_latest(cursor)`, stale rejection by generation/state-version/execution id).
- Renderer + runtime wire (Task 7, Gate 8 follow-up in Task 11's second fix): `umbra_core/expression/renderer.py` (`ReferenceRenderer` Protocol: `render(entry)`/`set_diagnostics_visible(bool)`/`close()` only — no method anywhere accepts a `FrameRing`/reader argument; organism never calls a renderer, so renderer failure structurally cannot pause the organism); `umbra_core/expression/headless_renderer.py` (`HeadlessRenderer` — holds no ring/cursor of its own; the trusted caller owns a `RendererCursor`, calls `FrameRing.read_latest(cursor)` itself, and passes only the resulting entry to `render()`; contained `render()` failures, no-op `close()`). `umbra_core/runtime.py`: `Organism` always constructs `self.expression_engine`/`self.frame_ring`; `Organism._push_expression_frame(last_outcome)` builds `ExpressionView` from copied snapshots (`phys.as_dict()`, `embodiment.to_state()` — never live aliases) and calls `derive`->`FrameRing.push`, wrapped in try/except (side-car failure never pauses the tick loop); called at both `tick_once` return sites via a `committed_outcome` local (denial -> `admitted=False`, delayed-this-tick -> `None`). `OrganismConfig.expression_enabled` (default True — additive/read-only, appends zero authoritative events) and condition `"C10"` (always forces it off, frozen performance baseline) gate `Organism._expression_active()`. Runtime-pushed `FrameRingEntry.active_execution_id` is always `None` (reserved for still-pending multi-tick actuations, not ordinary same-tick commits).
- Restart/replay/body-swap continuity (Task 8): all nine brief-named contracts held with **zero production code changes** — `tests/test_d008.py` only. Restart body-position/attachment and snapshot-replay round-trip via existing `Embodiment.to_state()/from_state()` + ledger-authoritative `attachment_state_from_event`; visible-condition continuity holds because `visible_condition_channels` is a pure function of restored physiology (no dependency on `ExpressionEngine._last_presentation`, which is intentionally not persisted); an INTERRUPTED frame never survives restart (ring rebuilds empty; next real outcome renders on its own merits); birth replay of an attach+2-swaps sequence reconstructs the same `AttachmentState` via `attachment_state_from_event`; deleting the `embodiment_body_attached` row fails closed through the ordinary `Store.validate_chain()` sequence-gap check (same mechanism as every other authoritative event); `EmbodimentAdapter.swap_profile` has no code path touching identity/memory/social/individuality (verified via exact state equality); `ConstitutionalIdentity` has no avatar/body/UI field and swap leaves `agent_id`/`identity_commitment` unchanged; D-007's `IndividualityEngine.FORBIDDEN_STATE_KEYS` (`avatar_id`/`ui_component_id`/`screen_coordinates`/`animation_name`) is exercised explicitly for D-008.
- Nonverbal signals + individuality presentation (Task 10, complete): `umbra_core/expression/engine.py` — `_visible_condition_channels(physiology, attention_confidence, individuality_summary=None)` now reads `ExpressionView.individuality_summary` (a read-only bag the caller may populate from `IndividualityEngine.disposition_vector()` plus `habit_active`/`routine_active` flags; engine never reaches into individuality/memory/social engines itself). Bounded nudges only: `INDIVIDUALITY_CHANNEL_BIAS_MAX` (0.15) shades `persistence`/`rest_frequency`/`activity_intensity` from `persistence_after_failure`/`recovery_pacing`/`stimulation_tolerance`; `HABIT_ROUTINE_CHANNEL_BIAS` (0.10) shades `transition_speed` (habit) and `attentional_persistence` (routine) independently. Still exactly the frozen 9 channel names, still clamped to [0,1], never changes posture/active_capability/nonverbal_signal for the same outcome — individuality shades, never authors. `SIGNAL_PLAY`/`SIGNAL_ASSISTANCE` visible mapping (nonverbal_signal + INTERACTING posture), `CHARGE`→RECOVERING→resumed-ACTIVE, and orientation pass-through from `Embodiment` heading were already correct from Task 5/7 — Task 10 added regression coverage only, no code change needed for those three.
- `ui/reference_companion/` (Task 9, complete; Gate 8 follow-up in Task 11's second fix): `habitat_view.py` (`render_habitat(canvas, packet)` — shapes/orientation/posture/attention-ring/nonverbal-icon only, never capability/phase/version text) + `diagnostics.py` (`render_diagnostics(canvas, packet)` — capability/phase/versions/source-refs/condition-channels only) both duck-type a `CanvasLike` `Protocol` and never import `tkinter`, so their logic is unit-testable without a display; `tkinter_renderer.py` (`TkinterRenderer` — `ReferenceRenderer` protocol impl; lazy `import tkinter` only inside `__init__`; holds no ring/cursor/lock of its own — dropped `ring_lock`/`poll_and_render`/`schedule`, since a future real UI driver owns the `FrameRing` + `RendererCursor` and calls `renderer.render(entry)` after its own `read_latest(cursor)`, never handing the renderer the ring; `close()` idempotent, destroys only its own canvases/root, never touches organism/adapter/`ExpressionEngine`). `umbra_core`/`experiments` verified (via `ast`-parsed test) to never import `ui/`; `ui/` verified to only ever import `umbra_core.expression`. This dev sandbox has no `python3-tk`; the 2 tests needing a real Tk instance `importorskip`/skip honestly rather than faking a display.
- Isolated ablations C1-C10 (Task 11, complete): `umbra_core/expression/engine.py` — `ExpressionConfig(ignore_actions, ignore_individuality, ignore_physiology)`/`ExpressionConfigError`/`condition_to_expression_config(condition)` (raises for C1/C2/C3/C7/C8 diagnostic-only conditions; maps C4→ignore_actions, C5→ignore_individuality, C6→ignore_physiology); `ExpressionEngine.__init__(config=None)` applies these uniformly in both the DETACHED and ATTACHED `_derive_presentation` branches (C4 forces `outcome=None` for presentation only — `Embodiment`/`Governance` still execute the real action). `umbra_core/runtime.py`: `OrganismConfig.expression_config: ExpressionConfig | None = None` is an **explicit-override-only** field (never auto-derived from the shared, already-overloaded `condition` string — many D-002..D-007 tests build organisms with `condition` in `C1..C8` while `expression_enabled` defaults `True`), wired into `Organism.__init__` as `ExpressionEngine(config=config.expression_config)`. `umbra_core/expression/presentation_state.py`: `PresentationState` is now `@dataclass(frozen=True)` — a real Gate-8/C7 finding: the same instance is both `ExpressionEngine._last_presentation` bookkeeping and the object stored in the shared `FrameRing`, so an unfrozen renderer field-assignment would have corrupted the engine's own next-tick transition state (verified only two construction sites exist, nothing mutates in place; residual not defended: nested mutable dict contents, `object.__setattr__` bypass, and `ReferenceRenderer.read_latest(ring)` handing renderers the live `FrameRing.push()` method — left for Task 13's Gate 8 sizing). `experiments/d008/diagnostic_controllers.py` (new): C1 `ScriptedAnimationScheduler`, C2 `RandomPresentationController`, C3 `ScalarMoodController`, `assert_not_production_schema`, plus C8's `assert_disposable_db_path(db_path)` (raises unless path resolves under system temp dir or `experiments/d008/`). `experiments/d008/hostile_renderer.py` (new): `HostileRenderer` (C7) — same `ReferenceRenderer` shape as `HeadlessRenderer`, never constructed with an organism/embodiment/physiology/governance reference; attempts ordinary field writes and records attempted/rejected/successful. C9 (shuffled frames)/C10 (fully disabled) need no engine switch.
- Body profiles: `umbra_core/embodiment_adapters/profiles.py` — sealed D-008 `ABSTRACT_SHAPE_BODY`/`MINIMAL_CREATURE_BODY` (hashes frozen in `experiments/d008/thresholds.json`); D-009 via `get_profile`/`d009_profile_from_d008` (`MANIPULATE`, `hold_slot_count`, `maximum_held_mass_class`, `hold_anchor`); `get_d008_profile` for migration source validation
- EmbodimentAdapter (Task 3/6): `umbra_core/embodiment_adapters/adapter.py` — `validate_manipulation` → `AdapterValidatedManipulation`; `maybe_migrate_d009_profile` in `runtime.py` (`origin=D009_PROFILE_MIGRATION` + optional `habitat_held_binding_rebased`); attach/detach/swap authoritative events; `ManipulationValidationError`/`ProfileMigrationError`
- Experiments: `experiments/d008/` — constrained profile, diagnostic controllers, hostile renderer, Task 13+14 harnesses (QUALIFIED)
- Task 13 status: local `UMBRA_D008_TASK13_GATES_1_11_PASS`; Task 14 AUTHORIZED: NO until independent review
- Runtime shape: governance → EmbodimentAdapter.execute → Embodiment.execute → ExpressionEngine.derive → frame ring; renderers poll non-destructively
- Caps: IDLE/ORIENT/MOVE/APPROACH/RETREAT/INSPECT/REST/CHARGE/SIGNAL_* (no MAINTAIN/PRACTICE aliases)

## Persistent habitat and environmental agency (D-009) — QUALIFIED
- Seal: `UMBRA_D009_PERSISTENT_HABITAT_AGENCY_QUALIFIED` @ `af35371` (tip governance `474ce97`; independent review Approve)
- Directive: `docs/directives/UMBRA-D-009-persistent-habitat-agency.md`
- Design: `docs/superpowers/specs/2026-07-23-umbra-d009-persistent-habitat-agency-design.md` (`79a00f2`)
- Plan: `docs/superpowers/plans/2026-07-23-umbra-d009-persistent-habitat-agency.md`
- `umbra_core/habitat/state.py` (Task 1): `HabitatState`, `Zone`, `ZoneConnection`, `HabitatObject`, `FreeLocation`/`HeldByLocation`, typed `ObjectState` union, `canonical_serialize`, `compute_state_hash`/`compute_object_state_hash`/`compute_habitat_definition_hash`, `apply_committed_object_mutation`/`apply_rejected_object_mutation`, `migrate_object_definition`, `sample_habitat_state` fixture
- `umbra_core/habitat/engine.py` (Task 2): `HabitatEngine` sole writer + indexes (`zone_free_object_count`, `zone_held_object_count` via `_apply_held_zone_counts`+body pose, `hold_index`, `free_spatial_index`); query API; `BodyPoseView`/`ReachProfile`/`BodyCollisionShape`; `commit_object_mutation`/`commit_free_location` (test/persistence hooks)
- `umbra_core/habitat/projection.py` (Task 2): `ImmutableHabitatProjection`, `HabitatProjectionFacade`, `project_features`, `validate_projection`, `ProjectionMismatchError`, `HabitatWriteRejected`
- `umbra_core/habitat/migration.py` (Task 2): `habitat_object_from_legacy_feature`, `legacy_object_id_for_feature`
- `umbra_core/habitat/events.py` (Task 3): 13 AUTHORITATIVE habitat event types, `apply_habitat_event`, `replay_habitat_from_events`, event builders (`build_initialized_event`, `build_object_moved_event`, `build_object_picked_up_event`, `build_body_zone_transition_event`), idempotent apply + fail-closed order/hash validation; `habitat_body_zone_transitioned` audit-only (no state_version bump)
- `umbra_core/events.py` (Task 3): `HABITAT_EVENT_AUTHORITY` + registry union for all habitat event types
- `umbra_core/embodiment.py` (Task 2): `BodyOccupancyView`, `attach_habitat_engine`, read-only `habitat` projection when engine attached; `_reject_habitat_mutation_when_engine_attached` fail-closed on legacy writers; `_habitat_read` routes primitives through projection; plant overlay (`blocked_cells`/delayed/misleading) passthrough to projection; legacy `_habitat` for D-008 compat without engine
- Packages (planned): `umbra_core/habitat_affordances/` (pure AffordanceEngine)
- `umbra_core/habitat_affordances/definitions.py` (Task 4): `AffordanceDefinition`, `definition_hash`, `load_affordance_definitions_file`, typed precondition/effect contracts
- `umbra_core/habitat_affordances/engine.py` (Task 4): pure `HabitatAffordanceEngine.validate` → `AffordanceValidationResult` + `HabitatEffectPlan`; USE emits `habitat_object_state_changed` with `new_state`; typed `ManipulationParameters` union; no habitat/WM/memory mutation
- `umbra_core/habitat/execution_journal.py` (Task 5): `prepare_execution`, `recover_execution`, `commit_manipulation_transaction`; journal states PREPARED/COMMITTED_SUCCESS/COMMITTED_FAILURE; idempotent COMMITTED_SUCCESS rehydrate via `_maybe_rehydrate_committed_success` (effect-plan or durable habitat events); atomic habitat events + organism_effect_applied + outcome_verified via `Store.atomic_manipulation_outcome`; codes EXECUTION_PAYLOAD_MISMATCH, HABITAT_COLLECTION_CAP_EXCEEDED, EVENT_STORAGE_BUDGET_EXCEEDED
- `umbra_core/persistence.py` (Task 5): `habitat_execution_journal` table + journal CRUD + `atomic_manipulation_outcome` + `list_habitat_events_for_execution` + optional `event_storage_budget` (enforced in `append_event`); recovery evidence via `outcome_verified` + `transaction_id` only
- `umbra_core/governance.py` (Task 5): `verify_manipulation_outcome` for MANIPULATE VerifiedOutcome with execution/request correlation in raw
- `umbra_core/governance.py` (Task 7): `execute_manipulation` — admit → `resolve_manipulation_address` → adapter.validate_manipulation → affordance.validate → journal commit; `MANIPULATE` in PREAUTHORIZED; rejects `target_object_id` in proposal params
- `umbra_core/perception.py` (Task 7): `ObjectAddressBinding`, `ResolvedManipulationTarget`, `resolve_manipulation_address`, `perceive_habitat_objects` (HIDDEN/occluded filtered); policy_view `manipulation_bindings` address-only
- `umbra_core/arbitration.py` (Task 7–8): `ManipulationCandidate` + `generate_manipulation_candidates`; Task 8: `select(manipulation_bindings=, routine_proposals=)`; MANIPULATE scoring
- `umbra_core/world_model/engine.py` (Task 8): `observe_environmental_outcome` idempotent by `execution_id`
- `umbra_core/memory/engine.py` (Task 8): `EnvironmentalRoutineSpec`, `RoutineLifecycle`, environmental routine promote/select/lifecycle/soft_proposals
- `umbra_core/individuality/engine.py` (Task 8): `habitat_modifier_for_candidate`, `observe_habitat_verified`, `HABITAT_DISPOSITION_DIMENSIONS`
- `umbra_core/runtime.py` (Task 5): `Organism.commit_manipulation` delegates to execution journal (trusted-resolved requests only)
- `umbra_core/runtime.py` (Task 7–8): `execute_manipulation_from_candidate`, bindings/routines → arbitration; environmental learning hooks on MANIPULATE outcomes
- `umbra_core/runtime.py` (Task 10): `HabitatConfig`/`habitat_enabled`/`habitat_scenario_hook`; P0/C13 gating disables MANIPULATE candidates, affordance execution, environmental routines, dynamics; `_push_expression_frame` wires `habitat_snapshot`+`body_pose` when engine attached
- `umbra_core/habitat/config.py` (Task 10): `HabitatConfig`, `condition_to_habitat_config` (C2/C3 diagnostic-only raise), `p0_compatibility_config`
- `experiments/d009/diagnostic_controllers.py` (Task 10): C2 `ScriptedObjectMovementController`, C3 `RandomManipulationController`
- `experiments/d009/hostile_habitat_view.py` (Task 10): C9 `HostileHabitatProjection` write-attempt recorder
- `experiments/d009/governance_bypass.py` (Task 10): C10 bypass payload helpers
- `experiments/d009/scenario_plants.py` (Task 10): S0–S16 environmental opportunity plants (`apply_scenario_plants`)
- Preregistration freeze (Task 11, commit `4e6c769f916fb7e8d0ca9ce42ddd0462c8654f3b`): `experiments/d009/thresholds.json`, `experiment-matrix.json`, `scenario-suite.json`, `habitat-definition.json`, `affordance-definitions.json`, `performance-protocol.json`, `seed-manifest.json` (template) — formal experiments start from this commit
- Task 13 harness (Gates 1–12): `experiments/d009/run_experiment.py`, `experiments/d009/evidence.py`, `experiments/d009/validate_evidence.py` — ProcessPool paired-seed matrix; preflight refuse rules; raw ledger + independent validator (cell-filtered mean recompute; Gate 2 C0×S2–S5; 100-restart probe; integrated routine/revision probes); **Gate 8 S16 requires full preregistered tick budget (1800 ticks) — do not use `D009_TICK_CAP` for qualification evidence**
- Task 13 harness tests: `tests/test_d009_task13_harness.py` — Gate 2 unauthorized semantics + validator cell spec
- Tests: `tests/test_d009.py` (Task 1: 3; Task 2: 7; Task 3: 7; Task 4: 5; Task 5: 15; Task 6: 8; Task 7: 15; Task 8: 11; Task 9: 8; Task 10: 13; Task 12: 108 total)
- Evidence (Task 13 Gates 1–12): `docs/evidence/d009/` — `*-results.json`, `raw-results.jsonl`, `seed-manifest.json`, `evidence-validation.json`, `experiment-summary.json` (`UMBRA_D009_TASK13_GATES_1_12_PASS`)
- Task 14 performance (complete, Supplement S3 Gate 13): `experiments/d009/run_performance.py`, `run_seal.py`, `with_tk_display.sh`, `performance-protocol.json`; evidence `docs/evidence/d009/performance-*.json`, `accelerated-100k-results.json`, `renderer-lifecycle-results.json`, `soak-P{0,1,2}.jsonl`, `final-verdict.md` (`UMBRA_D009_PERSISTENT_HABITAT_AGENCY_QUALIFIED`)
- Starting commit: `b230790df1cab1580ea650a348eb0576e2e4599e`; Mimir task: `06b5b59709864e11bddb8c1da56dd66e`
- Authority: own-and-delegate — HabitatEngine mutates; Embodiment.habitat read-only projection; MANIPULATE address-only candidates; PREPARED→COMMITTED execution journal; P0 compatibility mode on same D-009 commit

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

## Temporal continuity (D-010) — IN PROGRESS (SDD starting)
- Directive: `docs/directives/UMBRA-D-010-temporal-continuity.md` (plan approved)
- Design: `docs/superpowers/specs/2026-07-24-umbra-d010-temporal-continuity-design.md` (`03e1269`)
- Plan: `docs/superpowers/plans/2026-07-24-umbra-d010-temporal-continuity.md` (`c1f71bb7` — amended tip; supersedes `2149297`)
- Starting commit: `bb90e61`
- Prerequisite seal: D-009 `af35371`
- Parent Mimir: `9adf61b087ea4fa6a90a1c3bd401a9b3` (open until seal)
- Package: `umbra_core/temporal/` — Task 1–4 complete; Task 5: `observations.py` (TemporalObservationPlan, ObservationWindowEvidence, DedupSummary), `allowlists.py`, `engine.py` (prepare_finalized_evidence/prepare_authoritative_event, commit/abandon observation plans, record_observation_window_miss); `experiments/d010/{authoritative-event-allowlist,observable-evidence-allowlist}.json` drafts
- Tests: `tests/test_d010.py` (39 passed after Task 5)
- Experiments (draft): `experiments/d010/`, `docs/evidence/d010/` (planned)
