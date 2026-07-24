# UMBRA-D-010 Design: Temporal Continuity, Anticipation, and Autonomous Daily Life

**Date:** 2026-07-24  
**Project directive:** UMBRA-D-010  
**Agent memory directive:** `D-20260724-umbra-d010-temporal-continuity`  
**Starting commit:** `bb90e6111f883f58cced7e71b7d452df7f072aa7`  
**Bootstrap + Decision A commit:** `4770b5fa84faa60da10ee72ee53a0f0c0680db0b`  
**D-009 scientific seal:** `af35371`  
**Prerequisite:** `UMBRA_D009_PERSISTENT_HABITAT_AGENCY_QUALIFIED`  
**Mimir project:** `7777645d52a91b49`  
**Mimir parent task:** `9adf61b087ea4fa6a90a1c3bd401a9b3`  
**Status:** Design §§1–5 approved; eight final amendments applied; **approved for implementation planning**

## Purpose

Make UMBRA a creature living through time: continuous internal age, learned recurrence from organism-observable history, bounded anticipation, history-shaped temporal routines, schedule revision, and coherent restart/downtime recovery — without becoming a scheduler, calendar bot, or engagement timer.

## Scientific claims

**Authorized (bounded):** UMBRA demonstrates bounded temporal continuity, learned recurrence expectations, anticipatory behavior, and history-shaped daily routines across autonomous operation, restart, and changing event schedules.

**Not authorized:** consciousness; subjective time perception; genuine anticipation or emotion; biological circadian rhythm; unrestricted future prediction; complete companion capability; autonomous operation while hardware is powered off.

## Locked decisions (operator-approved)

1. **Decision A — TemporalEngine sole durable temporal authority.** Runtime supplies trusted monotonic samples and orchestration order; requests `prepare_advance` / downtime reconciliation; cannot independently advance organism age.
2. **Decision C — Hybrid recurrence evidence.** Temporal anchors + finalized organism-observable evidence establish and promote hypotheses. Allowlisted authoritative events may seed `CANDIDATE` and support causal reconciliation only — cannot independently create predictive confidence.
3. **Decision D — Anticipation.** Bounded temporal score modifiers + narrow governed `WAIT`. TemporalEngine exposes expectations only; never submits/executes actions. No `ANTICIPATE` capability.
4. **Decision E — Temporal routines.** Extend MemoryEngine procedural routines with optional relative `temporal_binding`. Memory owns lifecycle; every step re-enters arbitration/governance.
5. **Decision F — Downtime.** TemporalEngine-authoritative analytic reconciliation plan; Runtime validates; shared persistence applies allowlisted pure `ElapsedTimeContract`s atomically. No tick replay or fabricated experience.
6. **Decision G — Estimator.** Robust parametric period/phase/jitter on organism age ticks; one dominant period per hypothesis; S9 uses separate recurrence IDs; no histogram/multimodal in D-010.
7. **Approach 1 — Package `umbra_core/temporal/`** (clock, state, engine, recurrence, events, migration). Approaches 2–3 rejected.

## Hard constraints

* No LLM controller; no scheduler loop; no second clock thread; no timer-driven action execution.
* TemporalEngine must not select actions, grant capabilities, write physiology/habitat/relationships, create future events, treat expectations as truth, execute routines, or bypass governance.
* Wall-clock never sets or rewinds organism age; renderer time never authoritative.
* Hidden schedules, evaluator labels, and scenario definitions never enter temporal learning or policy.
* UI must not supply time, advance age, change recurrence evidence, or alter action selection.
* `umbra_core/temporal/**` never imports `ui/`.
* Experimental controls C1–C13 are harness-only and production-unreachable.

---

## 1. Architecture & packaging

```text
umbra_core/temporal/
  clock.py       # TrustedSample, wall mapping, discontinuity detection (pure)
  state.py       # TemporalState, hashes, epochs, anchors
  engine.py      # TemporalEngine sole writer: prepare_advance, observe plans, reconcile_downtime, views
  recurrence.py  # Robust parametric estimator + hypothesis lifecycle
  events.py      # Temporal event payloads + apply helpers → AUTHORITATIVE registry
  migration.py   # Schema / epoch / binding migrations

Orchestration only:
  runtime.py, persistence.py, arbitration.py, governance.py, memory/engine.py, events.py
```

| Owner | Authority |
|-------|-----------|
| TemporalEngine | Durable temporal state, recurrence hypotheses, expectation views, downtime plans |
| Runtime | Orchestration sequence `tick`; trusted sample intake; txn coordination |
| MemoryEngine | Procedural routines + relative `temporal_binding` |
| Arbitration | Modifiers, WAIT candidates, anti-reentry proposal gating |
| Execution/action system | `WaitExecution`, terminal outcomes |
| Persistence | Atomic commits |
| Governance | Admit/reject WAIT and routine steps |

### 1.1 Tick pipeline (atomic advance)

```text
1. Runtime begins orchestration step (sequence N)
2. If downtime gap → reconcile_downtime path (§4) before ordinary advance
3. TemporalEngine.prepare_advance(TrustedSample, sequence) → TemporalAdvancePlan
4. Runtime builds TickTemporalContext from the plan (speculative effective age)
5. Perception / learning / arbitration / governance / outcomes use TickTemporalContext
6. Shared persistence transaction:
     verify expected temporal version/hash
     apply TemporalAdvancePlan
     embed TemporalAdvanceRecord in the committed-tick event
     apply other tick effects/events
     commit
7. On rollback: abandon in-memory plan only — age does not advance
```

```text
TemporalAdvancePlan {
  advance_id
  expected_state_version
  expected_state_hash
  orchestration_sequence
  trusted_sample_hash
  prior_age_ticks / next_age_ticks
  prior_active_ticks / next_active_ticks
  anchor_delta
}
```

Same `advance_id` must not commit twice. No post-commit `commit_advance()`.

### 1.2 TickTemporalContext

```text
TickTemporalContext {
  advance_id
  effective_age_ticks
  effective_active_ticks
  orchestration_sequence
  prior_state_version
  prior_state_hash
}
```

Immutable and speculative; becomes authoritative only if the shared transaction commits; discarded on rollback. Prevents one-tick timestamp drift.

### 1.3 TemporalState

```text
TemporalState {
  schema_version
  temporal_epoch_id
  initialized_from_commit
  pre_temporal_history_ref
  organism_age_ticks              # never decreases
  organism_active_ticks           # unchanged across downtime
  last_committed_orchestration_sequence
  last_advance_id
  last_time_anchor
  wall_clock_mapping
  clock_uncertainty
  recurrence_index                # bounded
  state_version
  definition_hash
  state_hash
}
```

**Not in TemporalState:** pending waits (action system owns them).

```text
state_hash = sha256(canonical_serialize(TemporalState excluding state_hash and derived caches))
```

Freeze map ordering, numeric representation, enum representation, null handling, and schema version. Every committed temporal mutation increments `state_version` once per transaction.

### 1.4 TrustedSample

```text
TrustedSample {
  session_id
  monotonic_ns
  optional_wall_time
  wall_time_source
  wall_time_uncertainty
  sample_sequence
}
```

Monotonic values comparable only within one `session_id`. Downtime requires persisted prior wall anchor + current trusted wall sample. Missing/contradictory/excessive uncertainty → conservative recovery. Wall never rewinds age.

### 1.5 Age advancement semantics

```text
ordinary committed active tick:
  organism_age_ticks += 1
  organism_active_ticks += 1

trusted downtime (TRUSTED_SHORT only):
  organism_age_ticks += bounded elapsed_tick_equivalent
  organism_active_ticks unchanged

UNCERTAIN | EXCESSIVE | MISSING_WALL:
  age_advance = 0
  organism_active_ticks delta = 0
```

Freeze tick-duration conversion, rounding, maximum downtime age advance, uncertainty handling, and fractional remainder retention. First ordinary tick after downtime must not double-count elapsed.

### 1.6 TemporalAdvanceRecord (in committed-tick event)

No separate per-tick `temporal_advance_committed` event. Embed in the existing authoritative committed-tick event:

```text
TemporalAdvanceRecord {
  advance_id
  orchestration_sequence
  trusted_sample_hash
  prior/new temporal state_version
  prior/new temporal state_hash
  prior/new age_ticks
  prior/new active_ticks
  prior_time_anchor
  new_time_anchor
  prior_wall_clock_mapping
  new_wall_clock_mapping
  prior_clock_uncertainty
  new_clock_uncertainty
}
```

Every committed age advance has exactly one record; failed ticks have none. Replay must reconstruct the **complete** TemporalState from the committed-tick record (including anchors and clock mapping). Missing/duplicated records fail closed; replay never recalculates age from tick count.

`temporal_anchor_committed` is used **only** for anchor-only transactions outside an ordinary tick. An ordinary tick must **not** emit a duplicate anchor event.

Tests: `test_tick_replay_reconstructs_anchor_and_clock_mapping`, `test_ordinary_tick_does_not_emit_duplicate_anchor_event`, `test_committed_tick_contains_temporal_advance_record`, `test_failed_tick_has_no_temporal_advance_record`, `test_missing_advance_record_fails_replay`.

### 1.6b TemporalTransactionEnvelope

`state_version` advances **once per transaction**. One transaction may contain multiple temporal events.

```text
TemporalTransactionEnvelope {
  transaction_id
  prior_state_version
  new_state_version
  prior_state_hash
  new_state_hash
  ordered_events[]
}
```

Each contained event carries `transaction_event_index` and `payload_hash`, but **not** an independent state transition. Replay groups and applies the transaction atomically. Incomplete transaction event sets fail closed. Event order is deterministic. `temporal_initialized` uses a frozen genesis sentinel for absent prior state.

### 1.7 D-009 → D-010 initialization

Do not retroactively treat legacy `runtime.tick` as organism age.

`temporal_initialized` records `migration_id`, `temporal_epoch_id`, `source_commit`, `source_seal`, `initial_age_ticks = 0`, `initial_active_ticks = 0`, `pre_temporal_history_ref`, `initial_anchor`, `definition_hash`, `state_version`, `state_hash`.

D-009 identity/memory/individuality/relationships/habitat/history preserved. D-010 age begins at activation of authoritative temporal ownership. Prior history inspectable but not fabricated into temporal ticks. Initialization idempotent; second load does not reset age.

### 1.8 `runtime.tick` migration

Classify every production use as **O** (orchestration), **T** (organism time), or **B** (both).

* Implementation may temporarily treat unclassified as O.
* Before preregistration/formal execution: complete inventory, migrate all T/B semantic dependencies, commit `runtime-tick-classification.json`, harness fails if unclassified production use remains.
* Experimental harness scheduling may remain O.

### 1.9 Immutable views

```text
ImmutableTemporalView { organism_age_ticks, organism_active_ticks, last_time_anchor, clock_uncertainty, state_hash, schema_version, temporal_epoch_id }

PolicyExpectationView {
  recurrence_id, window_start, window_end, confidence, uncertainty,
  expected_context (coarse policy_context_view), expectation_version,
  status  # ACTIVE | UNCERTAIN only
}
```

Policy never receives raw authoritative events, CANDIDATE seeds, or hidden identifiers. Opaque evidence refs omitted unless arbitration needs audit provenance (default: omit).

---

## 2. Recurrence learning

### 2.1 Evidence lanes

| Lane | May seed CANDIDATE | May raise confidence / promote | Miss penalty |
|------|--------------------|--------------------------------|--------------|
| Temporal anchors | n/a | n/a | n/a |
| **O** Finalized organism-observable evidence | yes | **yes** | yes if window observable |
| **A** Allowlisted authoritative events | **yes only** (with observability proof) | **no** | audit/causal only |

Forbidden: hidden state, future schedules, scenario definitions, UI clocks, mutable subsystem objects.

### 2.2 Occurrence vs evidence identity

```text
occurrence_id     # real observed occurrence
evidence_identity # one observation envelope supporting an occurrence
```

`observation_count` and interval estimation use unique `occurrence_id`s. Multiple perception/social/habitat-plus-perception envelopes cannot inflate support.

### 2.3 Hypothesis identity

```text
recurrence_key = hash(event_kind, internal_context_key, context_schema_version, estimator_definition_hash)
```

`recurrence_id` derived from key or deterministic registry. Split `internal_context_key` (may resolve authoritative context) vs `policy_context_view` (coarse, no hidden ids). Context-schema change → migration or new hypothesis.

### 2.4 Estimator (Decision G)

Primary basis: organism age ticks.

```text
interval_i = occurrence_tick_i - occurrence_tick_(i-1)   # O-lane occurrences
period_estimate = robust_center(intervals)              # median default
jitter_estimate = robust_spread(intervals)              # MAD default

predicted_tick(n) = phase_anchor_tick + n * period_estimate
phase_error relative to fitted anchor (not age mod changing period)

next_index = first integer n where:
  phase_anchor_tick + n * period_estimate > current_age

predicted_center =
  phase_anchor_tick + next_index * period_estimate

window = predicted_center ± frozen jitter_margin
```

Freeze numeric rounding and integer conversion for `next_index` / `predicted_center`.

`last_observed_tick + period_estimate` may be used **only** during initial fitting when no stable `phase_anchor_tick` exists.

One dominant period per hypothesis. S9 overlapping events → separate recurrence IDs/contexts. No histogram/multimodal in D-010.

Confidence ↑: enough independent occurrences, consistent intervals, bounded jitter, held-out window hits, stable context.  
Confidence ↓: missed observable windows, rising variance, context mismatch, sustained drift, obsolete evidence.  
One anomaly must not erase an established ACTIVE pattern.

Lifecycle: `CANDIDATE → ACTIVE → UNCERTAIN|WEAKENED → INACTIVE|RETIRED`. Promotion to ACTIVE requires O-lane evidence. Replacement gets new `hypothesis_version` / `expectation_version`.

### 2.5 Observation windows and misses

```text
ObservationWindowEvidence {
  recurrence_id, expectation_version, window_start, window_end,
  coverage_start, coverage_end, observability_quality,
  supporting_observation_refs, matched_occurrence_id | None
}
```

Miss affects confidence only when: coverage ≥ frozen minimum; context observable; no matching occurrence; not in downtime/conservative recovery; expectation version current. Idempotent by expectation version + window. At most one occurrence or one miss per window.

### 2.6 Atomic observation intake

```text
prepare_finalized_evidence(...) / prepare_authoritative_event(...)
  → TemporalObservationPlan
```

```text
TemporalObservationPlan {
  observation_plan_id
  commit_mode                 # IN_TICK | POST_HOC
  expected_temporal_state_version / hash
  source_transaction_id       # IN_TICK: same as evidence txn
  source_event_id             # POST_HOC required
  source_event_hash           # POST_HOC required
  committed_advance_id        # POST_HOC required
  committed_age_ticks         # POST_HOC required
  committed_temporal_state_version  # POST_HOC required
  occurrence_id
  evidence_identities
  hypothesis_deltas
  temporal_events
}
```

**IN_TICK:** plan commits with the source evidence transaction.  
**POST_HOC:** commits in a **new** transaction anchored to `source_event_id`, `source_event_hash`, `committed_advance_id`, `committed_age_ticks`, `committed_temporal_state_version`. Post-hoc evidence cannot alter the historical age of its occurrence. Stale or missing source anchors fail closed. The same `occurrence_id` remains deduplicated across both modes.

Rollback leaves no recurrence mutation. Same plan cannot commit twice.

### 2.7 Dedup compaction

Bounded durable summaries: `recent_evidence_identities`, `retained_occurrence_identities`, `compacted_identity_digest`. Identities supporting active hypotheses retained. Compaction must still detect old duplicates. Eviction must not allow recount. Overflow → approved compaction or fail closed.

### 2.8 Policy filtering

* `ACTIVE`: full frozen modifier; may generate WAIT.  
* `UNCERTAIN`: smaller exploratory modifier only; **must not** generate WAIT.  
* `CANDIDATE|WEAKENED|INACTIVE|RETIRED`: policy-hidden.  
* Cap combined temporal contribution; freeze per-candidate positive/negative caps, per-tick combined cap, max expectations per candidate, deterministic merge order. Caps apply before signed cancellation.

### 2.9 Allowlists

Freeze before formal runs: `authoritative-event-allowlist.json`, `observable-evidence-allowlist.json`.

---

## 3. Anticipation, WAIT, routines, absence

### 3.1 Modifiers

Preparation horizon may modify MOVE/APPROACH/INSPECT/REST and routine eligibility **before** `window_start`. Soft only; physiology/danger/social urgency outrank. Temporal miss may update recurrence confidence, temporal-binding strength (via Memory evidence), and bounded WAIT propensity only — never physiology, relationships, habitat, social penalties, or identity writes.

### 3.2 WAIT

WAIT may begin only when `window_start <= effective_age_ticks <= window_end`.

```text
wait_deadline = min(wait_start_tick + maximum_wait_ticks, window_end)
```

```text
WAIT { recurrence_id, window_start, window_end, maximum_wait_ticks,
       interrupt_conditions, fallback_bias?, expectation_version }
```

```text
WaitExecution {
  execution_id, recurrence_id, expectation_version,
  window_start, window_end, started_age_tick, deadline_age_tick,
  interrupt_conditions_hash,
  status  # ADMITTED|ACTIVE|OCCURRENCE_OBSERVED|INTERRUPTED|EXPIRED|INVALIDATED|FAILED
}
```

Exactly one terminal outcome per `execution_id`. Retries return existing outcome. Rollback creates no active wait. Restart cannot silently resume unverified active wait; recovery resolves incomplete waits deterministically.

`OCCURRENCE_OBSERVED` requires matching finalized **O-lane** occurrence (`recurrence_id`, `expectation_version`, `occurrence_id`, `internal_context_key`, observation age in match window). A-lane alone cannot succeed WAIT.

### 3.3 Anti-reentry

Durable `WaitSuppression { anti_reentry_key, terminal_reason, suppressed_until_age_tick, source_execution_id|governance_decision_id }` in execution/arbitration journal — not TemporalState. Replay reconstructs. Materially revised expectation version may bypass under frozen epsilon. Governance rejection creates proposal suppression without fake WAIT execution. Bounded + deterministically compacted.

### 3.4 fallback_bias

Optional `{ candidate_class, bounded_delta, expires_after_ticks }`. No specific target/sequence; re-enters ordinary arbitration; expires quickly; overridden by critical needs.

### 3.5 Temporal routine binding

```text
ProceduralRoutine.temporal_binding {
  recurrence_id, minimum_confidence,
  eligibility_lead_ticks, eligibility_lag_ticks, maximum_start_delay,
  allowed_expectation_statuses
}
```

At evaluation, Memory binds current expectation → `BoundRoutineEligibility { recurrence_id, expectation_version, evaluated_window_*, evaluation_age_tick }`. Routine definition stable across ordinary phase updates. Stale version cannot activate. UNCERTAIN may get exploratory modifiers only — no auto-chain. Every step re-enters arbitration/governance. No TemporalEngine/timer launch path. Misses weaken temporal_binding before unrelated procedural knowledge. Retiring recurrence disables binding; provenance retained.

### 3.6 Interrupt vs miss

WAIT terminal outcome describes the action commitment. `ObservationWindowEvidence` independently determines occurrence/miss. Interrupt ≠ automatic miss. Coverage may continue after WAIT ends. One window → at most one occurrence or one miss. Downtime/conservative/incomplete coverage → no miss.

### 3.7 Absence safety

No indefinite bid escalation, viability punishment, irreversible relationship loss from miss alone, indefinite waiting, immediate WAIT re-entry for same key, or fabricated occurrence.

---

## 4. Downtime & restart

### 4.1 Pipeline

```text
restart → TrustedSample (new session) + prior TimeAnchor
→ TemporalEngine.reconcile_downtime → DowntimeReconciliationPlan
→ Runtime validates contracts → atomic apply → temporal_downtime_reconciled
```

### 4.2 Interval identity

```text
downtime_interval_id = hash(
  prior_anchor.state_hash, prior_anchor.advance_id, prior_anchor.session_id_at_commit,
  current_sample.session_id, current_sample_hash, reconciliation_policy_hash
)
```

```text
DowntimeReconciliationRecord {
  downtime_interval_id, reconciliation_id, canonical_plan_hash,
  status  # PREPARED|COMMITTED, transaction_id
}
```

One interval commits once; retry returns committed result; same ID different payload fails closed; unknown status recovered before retry; new reconciliation_id cannot reapply old interval.

### 4.3 Trust classes

`TRUSTED_SHORT` requires: accepted wall source, source continuity, sample freshness, non-negative gap ≤ max, uncertainty ≤ max, no discontinuity, no implausible wall/monotonic relationship. Freeze accepted sources, source-specific uncertainty, backward-jump handling, discontinuity thresholds, contradictory-anchor handling, freshness limits. Manual-clock/timezone/DST/source change may update mapping but does not auto-qualify trusted elapsed.

`UNCERTAIN|EXCESSIVE|MISSING_WALL`: `age_advance = 0`. Every successful reconciliation (including conservative) commits a **new session anchor**.

### 4.3b TimeAnchor trust provenance

```text
TimeAnchor {
  organism_age_ticks
  organism_active_ticks
  state_version
  state_hash
  wall_time | None
  wall_time_source | None
  wall_time_uncertainty
  session_id_at_commit
  advance_id
  anchor_trust_class
  trust_reason_codes
  eligible_as_downtime_baseline
  source_sample_hash
}
```

A conservative recovery anchor may establish the new session but **must not** convert an untrusted wall sample into a future trusted downtime baseline (`eligible_as_downtime_baseline = false` when trust is not TRUSTED_SHORT-quality).

The first sample used by a `PREPARED` reconciliation is persisted; retries reuse that sample; a later sample cannot silently change the prepared interval.

### 4.4 Contracts

```text
ElapsedTimeContractRegistry { schema_version, registry_version, registry_hash, contracts }
ElapsedTimeContract { contract_id, contract_version, contract_hash, subsystem,
  maximum_elapsed, maximum_uncertainty, supported_trust_classes,
  required_for_trust_classes, effect_schema_id, supported_effects,
  calculate_effects(...) -> ElapsedEffectPlan  # pure }
ElapsedEffectPlan { effect_plan_id, contract_id/version/hash,
  expected_subsystem_state_version/hash, declarative_effects, effect_plan_hash }
```

Initial allowlist: physiology decay/recovery; satiation/need drift; temporal confidence decay; expectation/waiting **window** expiration; HabitatEngine dynamics explicitly designed for elapsed reconciliation.

Optional contract may skip. Required missing/invalid/stale/out-of-range **blocks trusted catch-up** → rollback → conservative replan → separate atomic commit. No partial trusted catch-up. No arbitrary callbacks into persistence.

### 4.5 Recovery deltas

```text
ExpectationRecoveryDelta { recurrence_id, expected_hypothesis_version, expected_expectation_version,
  action  # EXPIRE|INVALIDATE|DECAY_CONFIDENCE|PRESERVE, bounded_delta }
WaitRecoveryDelta { execution_id, expected_status, terminal_status, terminal_reason, suppression_plan }
```

Stale versions fail the transaction. No downtime-derived occurrence/miss. ADMITTED/ACTIVE waits resolve deterministically; suppression commits atomically with terminal wait. Failed reconciliation changes neither waits nor suppression.

### 4.6 Replay of downtime

`temporal_downtime_reconciled` records interval/reconciliation ids, plan hash, prior/new temporal versions/hashes, trust class/reasons, elapsed, age_advance, fractional remainder, registry hash, effect_plan ids/hashes, skipped contracts, expectation/wait recovery deltas, prior/new anchors.

Replay applies recorded deltas. Must not reread wall clock, recalculate elapsed, rerun contracts, or reclassify trust.

### 4.7 Failure codes (freeze)

```text
DOWNTIME_INTERVAL_ALREADY_RECONCILED
RECONCILIATION_PAYLOAD_MISMATCH
TEMPORAL_ANCHOR_MISMATCH
WALL_TIME_UNTRUSTED
RECONCILIATION_STATE_CONFLICT
ELAPSED_CONTRACT_REGISTRY_MISMATCH
ELAPSED_CONTRACT_PLAN_INVALID
REQUIRED_ELAPSED_CONTRACT_UNAVAILABLE
```

---

## 5. Persistence, events, freeze, controls, performance

### 5.1 Temporal event envelope

Every authoritative temporal event includes: `event_id`, `event_kind`, `transaction_id`, `transaction_event_index`, `temporal_epoch_id`, `prior/new_state_version`, `prior/new_state_hash`, `effective_age_ticks`, `orchestration_sequence`, `definition_hash`, `payload_hash`. Multiple events in one transaction use deterministic ordering and are applied via `TemporalTransactionEnvelope` (§1.6b): one `state_version` step per transaction; events do not each carry an independent state transition.

Event kinds: `temporal_initialized`, `temporal_anchor_committed`, `temporal_clock_discontinuity_detected`, `temporal_recurrence_created|updated|revised|retired`, `temporal_downtime_reconciled`.

Routine promote/deactivate remain **Memory**-authoritative events referencing `recurrence_id`, `expectation_version`, `temporal_episode_refs`. TemporalEngine does not emit routine lifecycle events.

### 5.2 Boundedness

Separate limits for active runtime structures vs immutable ledger. Caps must not silently delete authoritative events. Compaction preserves event identity/hashes, terminal execution identity, reconciliation idempotency, evidence duplicate detection, replay equivalence, and scientific evidence. Overflow → approved compaction or fail closed.

### 5.3 Formal execution contract vs evidence manifest

Split frozen authorization from runtime campaign status:

```text
experiments/d010/formal-execution-contract.json   # immutable Stage B
  formal_execution_id
  freeze_bundle_hash
  implementation_source_hash
  runner_hash
  test_manifest_hash
  seed_manifest_hash

docs/evidence/d010/formal-execution-manifest.json  # runtime campaign
  freeze_commit          # actual Stage B commit recorded when formal execution begins
  started_at
  completed_at
  terminal_status
  row counts
  result hashes
```

Do **not** embed a commit hash inside the commit that creates that same freeze bundle. Record the actual Stage B `freeze_commit` when formal execution begins.

Smoke/dev runs explicitly non-formal. One freeze bundle → one terminal formal campaign. Rerun after terminal requires committed supplement + new execution ID. Partial campaigns resume from durable row ledger. Duplicate condition/scenario/seed rows rejected.

Evidence must include `raw-results.jsonl`, `formal-execution-manifest.json`, `evidence-validation.json`. Validator recomputes every gate from raw rows.

### 5.3b Development vs formal seeds

Freeze:

```text
development_seed_manifest
formal_seed_manifest
formal_seed_nonoverlap_rule
threshold_freeze_timestamp
```

Smoke and development runs use seeds **disjoint** from formal paired seeds. Formal seeds are not inspected before Stage B. Thresholds cannot change after any gate-critical formal row is produced. Changes require a committed supplement and a new formal execution ID. Development rows can never enter formal summaries.

### 5.4 Experimental controls

C1–C13 harness-only via experiment adapters. Not enableable via production config. Control code cannot become TemporalEngine dependency. C8 resets only disposable cloned state. C7 injection outside production policy construction. Control rows labeled; cannot enter C0 summaries. Tests verify production cannot import/activate controls.

Scenarios S0–S17 manipulate event timing and opportunity only.

### 5.5 Two-stage freeze

**Stage A — implement and hash definitions:**

```text
authoritative-event-allowlist.json
observable-evidence-allowlist.json
elapsed-contract-registry.json
temporal event schemas
failure-code registry
runtime-tick classification scanner
performance harness
```

Compute canonical hashes from implemented definitions.

**Stage B — final preregistration bundle (before formal experiments):**

```text
thresholds.json
experiment-matrix.json
scenario-suite.json
seed-manifest.json                    # formal paired seeds; ≥100 / gate-critical cell
development-seed-manifest.json        # disjoint from formal
performance-protocol.json
runtime-tick-classification.json
formal-execution-contract.json        # immutable authorization (not runtime status)
test-manifest.json                    # required test IDs / gates / files / modes
all Stage A hashes
implementation_source_hash
event-registry hash
failure-code-registry hash
allowed-verdict list
threshold_freeze_timestamp
formal_seed_nonoverlap_rule
```

`experiments/d010/test-manifest.json` enumerates `{ test_id, gate, required, test_file, expected_execution_mode }`. Seal validation must prove: every required test ID exists; every required test executed; zero skips; no duplicate or unknown test IDs; executed test-manifest hash matches Stage B.

Also freeze: occurrence identity rule, recurrence_key rule, context schema versions, phase_anchor fitting, next_index rounding, minimum observation coverage, miss idempotency, ACTIVE vs UNCERTAIN permissions, modifier caps/merge order, dedup compaction, wall sources/trust limits, downtime conversion/rounding/max age advance, TimeAnchor trust provenance fields, etc.

Formal execution requires: clean worktree; exact frozen source commit (recorded as `freeze_commit` in evidence manifest at start); no placeholder hashes; complete O/T/B classification; matching registries/schemas; sufficient paired seeds; no unknown failure codes; test-manifest hash match. Any production source change after Stage B invalidates the freeze.

### 5.6 Performance (Gate 13, Supplement S3)

P0/P1/P2 on **same** D-010 commit, starting organism snapshot, TemporalState, habitat state, seeds, event schedule, tick rate, runtime config, measurement tooling.

Only differences:

```text
P0  TemporalEngine active; anticipation + temporal routine eligibility disabled
P1  Full D-010 + HeadlessRenderer
P2  Full D-010 + TkinterRenderer
```

Warm-up 300s → measure 1800s → +900s if ambiguous → max 3600s/mode. RSS p95 ≤ 180 MiB; slope ≤ 1 MiB/h; CPU ≤ 5%; Tk incremental ≤ 128 MiB / 1 MiB/h / 5%. Record absolute and incremental P0→P1 and P1→P2 costs. Also ≥100k accelerated ticks + temporal lifecycle stress. No fixed two-hour soak.

### 5.7 Gates & verdicts

Gates 0–15 per operator directive (prior seals; temporal authority; recurrence; no future leakage; anticipation; revision; temporal routines; autonomy; absence safety; individuality timing; restart/downtime; replay; boundedness; performance; alignment; seal).

Allowed QUALIFIED: `UMBRA_D010_TEMPORAL_CONTINUITY_QUALIFIED`.  
D-011 authorized only under that verdict.

---

## 6. Minimum tests (aggregate)

Directive §14 named tests plus all section-revision tests, including (non-exhaustive highlight):

```text
# §1 / advance
test_temporal_advance_commits_atomically_with_tick
test_abandoned_tick_does_not_advance_age
test_temporal_advance_id_cannot_commit_twice
test_tick_context_uses_proposed_committed_age
test_temporal_state_hash_is_canonical
test_committed_tick_contains_temporal_advance_record
test_failed_tick_has_no_temporal_advance_record
test_missing_advance_record_fails_replay
test_all_production_runtime_tick_uses_are_classified

# §2 / recurrence
test_multiple_observations_of_one_occurrence_count_once
test_authoritative_and_observable_pair_do_not_double_count
test_authoritative_event_cannot_promote_to_active
test_same_expected_window_cannot_register_two_misses
test_partial_observation_coverage_does_not_register_miss
test_dedup_eviction_does_not_allow_recount
test_policy_view_excludes_candidates_and_raw_authoritative_events

# §3 / WAIT / routines / absence
test_uncertain_expectation_cannot_generate_wait
test_waiting_is_bounded
test_wait_execution_has_one_terminal_outcome
test_wait_anti_reentry_survives_restart
test_authoritative_hidden_event_cannot_complete_wait
test_temporal_miss_cannot_write_relationships
test_modifier_caps_apply_before_signed_cancellation

# §4 / downtime
test_same_downtime_interval_cannot_use_new_id_to_reapply
test_uncertain_downtime_has_zero_age_advance
test_required_contract_failure_replans_conservatively
test_replay_uses_recorded_downtime_deltas
test_replay_does_not_read_wall_clock

# §5 / freeze / controls
test_experimental_controls_are_production_unreachable
test_formal_harness_refuses_dirty_freeze
test_d001_through_d009_seals_unchanged
```

---

## 7. Required artifacts

```text
umbra_core/temporal/
experiments/d010/
tests/test_d010.py
docs/directives/UMBRA-D-010-temporal-continuity.md
docs/superpowers/specs/2026-07-24-umbra-d010-temporal-continuity-design.md  # this file
docs/superpowers/plans/2026-07-24-umbra-d010-temporal-continuity.md         # after plan approval
docs/evidence/d010/   # per directive §15 + formal-execution-manifest.json (runtime)
experiments/d010/formal-execution-contract.json
experiments/d010/test-manifest.json
experiments/d010/development-seed-manifest.json
```

---

## Spec self-review (2026-07-24; updated after eight final amendments)

| Check | Result |
|-------|--------|
| Placeholders | None; formal contract/manifest split; numeric thresholds deferred to Stage A/B freeze only. |
| Authority duplication | TemporalEngine / Memory / Execution / Runtime / Persistence boundaries unchanged and explicit. |
| Age / anchor replay | TemporalAdvanceRecord includes anchors + clock mapping; ordinary tick has no duplicate `temporal_anchor_committed`. |
| Transactions | TemporalTransactionEnvelope: one state_version step per txn; events indexed inside. |
| Prediction | Fitted phase_anchor + next_index; last_observed+period only for initial fitting. |
| Observation commits | IN_TICK vs POST_HOC modes explicit. |
| Formal freeze | Contract immutable in Stage B; evidence manifest records freeze_commit at run start. |
| Seeds | Development/formal disjoint; threshold freeze timestamp. |
| Tests | Stage B `test-manifest.json` required for seal. |
| Anchor trust | Conservative anchors not eligible as trusted downtime baselines; PREPARED sample sticky. |

## Final amendments (operator 2026-07-24)

1. Replay-complete TemporalAdvanceRecord (anchors + clock mapping); no duplicate anchor event on ordinary ticks.
2. TemporalTransactionEnvelope semantics.
3. Fitted next_index prediction consistency.
4. IN_TICK vs POST_HOC observation commits.
5. formal-execution-contract.json vs evidence formal-execution-manifest.json.
6. TimeAnchor trust provenance + sticky PREPARED sample.
7. Development/formal seed separation + threshold freeze timestamp.
8. experiments/d010/test-manifest.json required at Stage B.

## Next

Specification **approved for implementation planning**. Write `docs/superpowers/plans/2026-07-24-umbra-d010-temporal-continuity.md`, then Subagent-Driven execution. Parent Mimir `9adf61b087ea4fa6a90a1c3bd401a9b3` stays open until seal.
