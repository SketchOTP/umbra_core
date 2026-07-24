# UMBRA-D-010: Temporal Continuity, Anticipation, and Autonomous Daily Life

**Status:** AUTHORIZED / IN PROGRESS  
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
