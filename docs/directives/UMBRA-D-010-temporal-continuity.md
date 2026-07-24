# UMBRA-D-010: Temporal Continuity, Anticipation, and Autonomous Daily Life

**Status:** AUTHORIZED / DESIGN SPEC WRITTEN (awaiting operator review)  
**Agent Memory Directive:** `D-20260724-umbra-d010-temporal-continuity`  
**Starting Commit:** `bb90e6111f883f58cced7e71b7d452df7f072aa7`  
**D-009 Scientific Seal:** `af35371`  
**Prerequisite Verdict:** `UMBRA_D009_PERSISTENT_HABITAT_AGENCY_QUALIFIED`  
**Mimir Project:** `7777645d52a91b49`  
**Mimir Task:** `9adf61b087ea4fa6a90a1c3bd401a9b3` (parent; stays open until final seal)

Canonical operator text for this directive is the project directive issued 2026-07-24. This file is the in-repo copy for navigation and seal hashing. Where a frozen design spec under `docs/superpowers/specs/` amends operator text, the design spec governs implementation.

## Objective

Implement and validate persistent temporal life. UMBRA must maintain continuous internal age and temporal history; learn recurring environmental and social patterns; estimate when events are likely to recur; anticipate useful or relevant events; prepare, wait, approach, rest, or continue independent activity based on uncertain expectations; develop non-authored time-linked habits and routines; revise expectations when schedules change; recover coherently after restart or downtime; and continue autonomous life without being directly controlled by a scheduler.

D-010 must make UMBRA a creature living through time, not a task runner executing calendar rules.

## Authorized claim

> UMBRA demonstrates bounded temporal continuity, learned recurrence expectations, anticipatory behavior, and history-shaped daily routines across autonomous operation, restart, and changing event schedules.

**Not authorized:** consciousness; subjective time perception; genuine anticipation or emotion; biological circadian rhythm; unrestricted future prediction; complete companion capability; autonomous operation while hardware is powered off.

## Packaging

```text
umbra_core/temporal/
  clock.py
  state.py
  engine.py
  recurrence.py
  events.py
  migration.py

experiments/d010/
tests/test_d010.py
docs/evidence/d010/
```

## Pipeline

```text
trusted time source
→ TemporalEngine observations
→ recurrence hypotheses and uncertainty
→ bounded temporal proposal modifiers
→ existing arbitration
→ governance
→ execution
→ verified outcomes
→ Memory / WorldModel / Individuality updates
```

## Ownership

| Component | Owns |
|-----------|------|
| TemporalEngine | Internal age, time anchors, recurrence estimates, temporal uncertainty |
| Runtime | Tick ordering and trusted time-source access |
| WorldModel | Expected event consequences |
| MemoryEngine | Episodes and temporal routines |
| Individuality | History-shaped timing preferences |
| HabitatEngine | Actual environmental availability and events |
| SocialEngine | Partner-specific contingency and social history |
| Arbitration | Final candidate competition |
| Governance | Authorization |

TemporalEngine must not: directly select actions; grant capabilities; write physiology; write habitat; write relationships; create future events; treat expectations as truth; execute routines; bypass governance.

## Time model (summary)

Authoritative: `organism_age_ticks`, `organism_active_ticks`, `last_committed_tick`, `last_time_anchor`, `wall_clock_mapping`, `clock_uncertainty`, `schema_version`. Internal age never decreases. One monotonic runtime clock. Wall-clock is optional context. Renderer time never authoritative. No second independent scheduler clock. Time-anchor events only (not one event per tick).

## Recurrence / anticipation / routines / downtime

See operator directive §§5–8. Soft anticipation only; bounded waits; temporal routines as D-005 procedural memories with governance each step; downtime reconciles once without fabricating experience.

## Conditions C0–C13 / Scenarios S0–S17

See operator directive §§10–11. C1/C7/C10 isolated experimental controls only. Scenarios manipulate event timing and opportunity only — never expectations, routines, preferences, or actions directly.

## Preregistration

Commit and hash before formal execution:

```text
experiments/d010/thresholds.json
experiments/d010/experiment-matrix.json
experiments/d010/scenario-suite.json
experiments/d010/seed-manifest.json
```

Formal harness must reject dirty or modified freeze files. Minimum 100 paired seeds per gate-critical comparison.

## Acceptance gates

Gates 0–15 per operator directive §13 (prior seals; temporal authority; recurrence; no future leakage; anticipation; revision; temporal routines; autonomy; safe absence; individuality timing; restart/downtime; replay; boundedness; S3 performance P0/P1/P2; project alignment; seal).

## Allowed verdicts

```text
UMBRA_D010_TEMPORAL_CONTINUITY_QUALIFIED
UMBRA_D010_PARTIAL_FOUNDATION
UMBRA_D010_TEMPORAL_AUTHORITY_FAIL
UMBRA_D010_RECURRENCE_LEARNING_FAIL
UMBRA_D010_FUTURE_LEAKAGE_FAIL
UMBRA_D010_ANTICIPATION_FAIL
UMBRA_D010_REVISION_FAIL
UMBRA_D010_TEMPORAL_ROUTINE_FAIL
UMBRA_D010_AUTONOMY_FAIL
UMBRA_D010_ABSENCE_SAFETY_FAIL
UMBRA_D010_DOWNTIME_CONTINUITY_FAIL
UMBRA_D010_REPLAY_FAIL
UMBRA_D010_BOUNDEDNESS_FAIL
UMBRA_D010_REGRESSION_FAIL
UMBRA_D010_PERFORMANCE_FAIL
```

D-011 authorized only under `UMBRA_D010_TEMPORAL_CONTINUITY_QUALIFIED`.

## Minimum tests

`tests/test_d010.py` — named tests per operator directive §14.

## Required evidence

`docs/evidence/d010/` — artifacts per operator directive §15.

## Completion

D-010 is complete only when evidence shows temporal continuity, learned recurrence from observed history, bounded governed anticipation, non-authored temporal routines, schedule revision, and coherent autonomous life across restart and downtime — without becoming scheduler-driven.

## Locked design decisions

### Decision A — TemporalEngine sole durable temporal authority (2026-07-24)

Runtime supplies a trusted monotonic sample and requests `TemporalEngine.advance(...)`, then receives a committed `TemporalState` before the rest of the organism tick. `Runtime.tick` may remain an orchestration sequence number but is **not** temporal authority.

TemporalEngine owns: `organism_age_ticks`, `organism_active_ticks`, `last_committed_tick`, `last_time_anchor`, `wall_clock_mapping`, `clock_uncertainty`.

Rules: age advances only when the runtime tick commits; failed/rolled-back ticks do not advance age; Runtime cannot modify age directly; no second scheduler or clock loop; wall-clock changes never rewind organism age; replay reconstructs age from temporal events; downtime reconciliation enters through TemporalEngine; other subsystems receive immutable temporal views; existing `runtime.tick` uses migrate gradually to orchestration sequence or `TemporalState.organism_age_ticks` by meaning.

> D-010 makes TemporalEngine the sole durable temporal authority. Runtime supplies trusted monotonic observations and orchestration order but cannot independently advance organism age.

### Decision C — Hybrid recurrence evidence (2026-07-24)

TemporalEngine inputs:
1. Temporal anchors (trusted monotonic samples; committed downtime reconciliation)
2. Finalized observable evidence (verified outcomes; finalized perception observations; committed social observations visible to the organism)
3. Allowlisted authoritative events — may create/update **CANDIDATE** hypotheses only; cannot increase confidence or promote by themselves

Promotion: `CANDIDATE` → sufficient independent observations → confidence calibration → `ACTIVE`.

Hidden habitat/partner/evaluator state never enters learning. Future schedules and scenario definitions are forbidden inputs. Authoritative event without perception evidence may support audit/causal matching only. Misses reduce confidence only when the observation window was available. Deduplicate by event/evidence identity. Immutable event envelopes only. Freeze authoritative-event allowlist before formal experiments. Policy receives recurrence expectations only, never raw authoritative events.

> D-010 uses hybrid recurrence evidence. Temporal anchors and finalized organism-observable evidence establish and promote recurrence hypotheses. Allowlisted authoritative events may seed candidates and support causal reconciliation, but cannot independently create predictive confidence.

### Decision D — Anticipation: modifiers + narrow WAIT (2026-07-24)

TemporalEngine exposes only immutable expectations: `recurrence_id`, `window_start`, `window_end`, `confidence`, `uncertainty`, `expected_context`, `supporting_evidence_refs`.

Arbitration may apply bounded score modifiers to existing MOVE/APPROACH/INSPECT/REST (and related) candidates, and may generate a governed `WAIT` candidate only when the expected window is open and confidence meets the frozen threshold. TemporalEngine never submits or executes actions.

`WAIT` fields: `recurrence_id`, `window_start`, `window_end`, `maximum_wait_ticks`, `interrupt_conditions`, `fallback_activity`, `expectation_version`. It is a narrow governed action (not an ANTICIPATE capability); grants no new body capability; competes via normal arbitration; may be rejected by governance; interrupted by physiology/danger/social urgency/habitat change/stronger candidates. Waiting cannot begin before the frozen preparation horizon. Ends at earliest of: expected event observed, interruption, maximum wait, expectation invalidated, window expiration. Expiration → finalized miss only if observability was adequate; then return to ordinary autonomy. Repeated misses reduce confidence and waiting propensity. No indefinite score escalation or repeated immediate re-entry.

> D-010 uses bounded temporal score modifiers plus a narrow governed WAIT action. TemporalEngine exposes expectations only. Arbitration proposes WAIT during an open, sufficiently confident window, and normal governance, physiology, interruption, and expiration rules retain control.

### Decision E — Temporal routines via MemoryEngine binding (2026-07-24)

Extend D-005/D-009 procedural routines with optional `temporal_binding` (`recurrence_id`, `expectation_version`, `eligibility_window_start`/`end`, `minimum_confidence`, `maximum_start_delay`). MemoryEngine remains sole routine authority. TemporalEngine supplies immutable expectations and reports revisions/misses/uncertainty — does not store action chains or promote/execute/retire routines. Arbitration scores each step; does not auto-execute chains.

Rules: temporal binding optional; promotion needs multiple independent finalized episodes; window makes eligible not mandatory; every step re-enters arbitration/governance/adapter/execution; interruptible; schedule changes via new expectation version; stale versions cannot activate; repeated misses weaken temporal binding before unrelated procedural knowledge; retiring recurrence disables binding, preserves provenance; no timer/TemporalEngine path launches routines.

> D-010 extends existing MemoryEngine procedural routines with optional recurrence-window bindings. TemporalEngine supplies expectations only; Memory owns routine lifecycle, and every routine step remains a governed soft proposal.

### Decision F — Downtime reconciliation (2026-07-24)

```text
restart → TemporalEngine.reconcile_downtime(...) → DowntimeReconciliationPlan
→ Runtime validates registered contracts → shared persistence applies atomically
→ temporal_downtime_reconciled committed
```

Plan fields: `reconciliation_id`, `prior_anchor`, `current_anchor`, `elapsed_duration`, `uncertainty`, `trust_class`, `age_advance`, `expired_expectation_ids`, `allowed_contract_ids`, `conservative_recovery`.

`ElapsedTimeContract`: pure `calculate_effects(snapshot, elapsed, uncertainty)` → immutable effect plan. Initial allowlist: physiology decay/recovery; satiation/need drift; temporal confidence decay; prediction/waiting window expiration; HabitatEngine dynamics explicitly designed for elapsed reconciliation.

Rules: no missed-tick replay; TemporalEngine never mutates other subsystems directly; no inventing actions/memories/observations/social/object moves/routines; one coherent pre-reconciliation snapshot; all-or-nothing commit; same `reconciliation_id` cannot apply twice; short trusted → analytic catch-up; excessive/uncertain → conservative recovery; unsupported contracts unchanged + recorded; age may advance, `organism_active_ticks` must not; failed reconciliation preserves prior committed temporal state and retries deterministically.

> D-010 uses TemporalEngine-authoritative analytic downtime reconciliation. TemporalEngine produces an immutable reconciliation plan; Runtime and shared persistence atomically apply allowlisted pure elapsed-time contracts. No tick replay or fabricated experience is permitted.

### Decision G — Robust parametric recurrence estimator (2026-07-24)

Per-hypothesis fields: `observation_ticks`, `interval_estimate`, `phase_estimate`, `jitter_estimate`, `confidence`, `miss_count`, `observation_count`. Primary basis: organism age ticks (not wall-clock).

Estimation: intervals between observations; `period_estimate` = robust center; `jitter_estimate` = robust spread; `phase_estimate` = latest_observation_tick mod period. Prefer median + MAD (or preregistered robust equivalent).

Confidence ↑: enough independent observations, consistent intervals, bounded jitter, held-out window hits, stable context. Confidence ↓: missed observable windows, rising variance, context mismatch, sustained drift, obsolete evidence. One anomaly must not erase an established recurrence.

Prediction: `predicted_center = last_observed_tick + period_estimate`; window = center ± frozen jitter_margin. Gradual drift updates incrementally; abrupt sustained contradiction weakens before replace (new version). Misses reduce confidence only when observable. Scope: one dominant period per hypothesis; S9 overlapping events → separate recurrence IDs/contexts; no histogram/multimodal in D-010.

> D-010 uses a bounded robust parametric recurrence estimator for period, phase, and jitter. It learns one dominant interval per recurrence hypothesis from organism-observable event timing, revises under sustained contradiction, and never uses hidden schedules as predictive evidence.

### Design §1 approved (2026-07-24) — seven revisions

1. Temporal advance is atomic via `TemporalAdvancePlan` inside the shared tick persistence transaction (no post-commit `commit_advance`).
2. `TickTemporalContext` provides speculative effective age for the current tick.
3. `TemporalState` includes `state_version`, `definition_hash`, `state_hash` with frozen canonical serialization.
4. Active WAIT state is not owned by TemporalEngine (execution system owns commitments).
5. `TrustedSample` is session-scoped; downtime needs trusted wall anchors; wall never rewinds age.
6. Frozen age semantics: ordinary tick +1 age/+1 active; trusted downtime advances age only (bounded); remove `last_committed_tick` → `last_committed_orchestration_sequence` + `last_advance_id`.
7. Complete production `runtime.tick` O/T/B classification + migration before preregistration/formal runs.

### Design §2 approved (2026-07-24) — seven revisions

1. Separate `occurrence_id` from `evidence_identity`; counts/intervals use unique occurrences.
2. Deterministic `recurrence_key` / `recurrence_id`; split `internal_context_key` vs `policy_context_view`.
3. Phase via fitted `phase_anchor_tick` + period; not unstable age mod changing period.
4. Explicit `ObservationWindowEvidence` for miss eligibility and idempotency.
5. Evidence intake via `TemporalObservationPlan` committed atomically with source evidence.
6. Policy: ACTIVE may WAIT; UNCERTAIN smaller modifier only; no WAIT; cap combined temporal modifiers.
7. Durable dedup summaries + compaction; eviction must not allow recount.

### Design §3 approved (2026-07-24) — eight revisions

1. Preparation horizon → modifiers/eligibility only; WAIT only when window open; wait_deadline = min(start+max_wait, window_end).
2. Durable replayable `WaitExecution` with exactly-one terminal outcome.
3. WAIT success (`OCCURRENCE_OBSERVED`) requires matching finalized O-lane occurrence.
4. Durable `WaitSuppression` for anti-reentry across restart.
5. Replace `fallback_activity` with optional bounded `fallback_bias`.
6. Relative `temporal_binding` + evaluated `BoundRoutineEligibility` (not stored absolute windows).
7. WAIT terminal outcome independent of ObservationWindowEvidence miss assessment.
8. Frozen modifier aggregation caps; temporal miss cannot write physiology/relationships/habitat/social/identity.

### Design §4 approved (2026-07-24) — eight revisions

1. `downtime_interval_id` + durable reconciliation journal (one commit per interval).
2. Tight `TRUSTED_SHORT` requirements; clock/source changes do not auto-trust elapsed.
3. Conservative classes: `age_advance = 0`; every successful reconcile commits a new session anchor.
4. Versioned/hashed `ElapsedTimeContractRegistry` and pure `ElapsedEffectPlan`s.
5. Required vs optional contracts; required failure → rollback → conservative replan.
6. Explicit `ExpectationRecoveryDelta` / `WaitRecoveryDelta` (no ambiguous policy fields).
7. Replay applies recorded downtime deltas; never rereads wall clock or recalculates.
8. Stable failure codes, journal bounds, and dedicated tests.

### Design §5 approved (2026-07-24) — eight revisions

1. TemporalAdvanceRecord embedded in committed-tick event (no per-tick temporal_advance event).
2. D-009→D-010 temporal epoch init: age starts at 0; prior history not fabricated into ticks.
3. Standardized temporal event envelopes; Memory owns routine lifecycle events.
4. Separate active-structure caps from immutable ledger; compaction preserves scientific identity.
5. One-shot formal-execution-manifest; validator recomputes gates from raw rows.
6. C1–C13 harness-only / production-unreachable.
7. Stage A implement+hash definitions; Stage B full preregistration bundle.
8. P0/P1/P2 same commit/snapshot/schedule; only anticipation/routines/renderer differ.

Full design: `docs/superpowers/specs/2026-07-24-umbra-d010-temporal-continuity-design.md`
