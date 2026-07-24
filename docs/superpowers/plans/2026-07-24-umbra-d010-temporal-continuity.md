# UMBRA-D-010 Temporal Continuity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Qualify bounded temporal continuity — TemporalEngine sole age authority, robust parametric recurrence from organism-observable evidence, soft anticipation + narrow WAIT, Memory temporal_binding routines, analytic downtime reconciliation, and continuity across restart/replay — without becoming a scheduler.

**Architecture:** Own-and-delegate `umbra_core/temporal/`. Runtime supplies `TrustedSample` and orchestration sequence only; `prepare_advance` → `TemporalAdvancePlan` commits atomically inside the shared tick transaction with a replay-complete `TemporalAdvanceRecord`. Recurrence uses hybrid evidence (O-lane promotes; A-lane seeds CANDIDATE only). Arbitration applies capped modifiers and may propose WAIT inside open ACTIVE windows. Downtime: TemporalEngine plan → Runtime validates versioned pure `ElapsedTimeContract`s → persistence applies atomically; conservative classes advance age by 0. Two-stage freeze; one-shot formal campaign via contract + evidence manifest.

**Tech Stack:** Python 3 stdlib + SQLite WAL (`umbra_core`), `tkinter` + Xvfb for P2 soak only, pytest. No new third-party dependencies.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-24-umbra-d010-temporal-continuity-design.md` (tip includes amendments `03e1269`)
- Directive: `docs/directives/UMBRA-D-010-temporal-continuity.md`
- Starting commit: `bb90e6111f883f58cced7e71b7d452df7f072aa7`
- Design commits: `ad97ddd` (initial), `03e1269` (eight final amendments)
- D-009 seal: `af35371` / `UMBRA_D009_PERSISTENT_HABITAT_AGENCY_QUALIFIED`
- Mimir project: `7777645d52a91b49`; parent task: `9adf61b087ea4fa6a90a1c3bd401a9b3` (open until seal)
- Agent directive: `D-20260724-umbra-d010-temporal-continuity`
- `umbra_core` / `experiments` never import `ui/`
- TemporalEngine never selects/executes actions or launches routines
- C1–C13 harness-only / production-unreachable
- Formal experiments only after Stage B freeze (no placeholder hashes)
- Final sealed suite: zero skips
- Do not edit `.agent/RECORD.md`
- Ponytail: smallest correct diff; reuse D-008/D-009 harness patterns
- Parent Mimir stays open until final seal; close against seal tip

## File map

| Path | Responsibility |
|------|----------------|
| `umbra_core/temporal/__init__.py` | Public exports |
| `umbra_core/temporal/clock.py` | TrustedSample, wall mapping, discontinuity (pure) |
| `umbra_core/temporal/state.py` | TemporalState, TimeAnchor, hashes, epoch |
| `umbra_core/temporal/engine.py` | TemporalEngine sole writer |
| `umbra_core/temporal/recurrence.py` | Parametric estimator + hypotheses |
| `umbra_core/temporal/events.py` | Temporal payloads + apply + envelopes |
| `umbra_core/temporal/migration.py` | Epoch/schema migrations |
| `umbra_core/runtime.py` | Sample intake, prepare_advance orchestration, downtime apply |
| `umbra_core/persistence.py` | Atomic tick + downtime + observation commits |
| `umbra_core/events.py` | Register AUTHORITATIVE temporal kinds; TemporalAdvanceRecord on tick |
| `umbra_core/arbitration.py` | Modifiers, WAIT candidate, WaitSuppression gating |
| `umbra_core/governance.py` | Admit WAIT |
| `umbra_core/memory/engine.py` | Relative temporal_binding + BoundRoutineEligibility |
| `experiments/d010/*` | Allowlists, registry, freeze, harnesses, controls |
| `tests/test_d010.py` | Full minimum + amendment tests |
| `docs/evidence/d010/*` | Evidence pack |

---

### Task 0: Align governance with design tip

**Files:** `.agent/CURRENT.md`, `.agent/REPO_MAP.md`, `docs/directives/UMBRA-D-010-temporal-continuity.md` (status), progress ledger

- [ ] **Step 1:** Point CURRENT at design tip `03e1269`; status = plan written / implementation starting.
- [ ] **Step 2:** REPO_MAP: design + plan paths; `umbra_core/temporal/` planned.
- [ ] **Step 3:** Commit

```bash
git commit -m "Align D-010 governance with amended design tip for planning."
```

---

### Task 1: Temporal state, clock, hashing, epoch init

**Files:** Create `umbra_core/temporal/{__init__,clock,state,migration}.py`; `tests/test_d010.py`

**Produces:** `TrustedSample`, `TemporalState`, `TimeAnchor` (with trust provenance fields), `canonical_serialize`, `state_hash`, `temporal_epoch_id`, genesis init age=0.

- [ ] **Step 1:** Failing tests: age never decreases; state_hash canonical; TimeAnchor trust fields; init idempotent; second load does not reset age.
- [ ] **Step 2:** Implement minimal state/clock/migration.
- [ ] **Step 3:** Commit `Add D-010 TemporalState, TrustedSample, and epoch initialization.`

---

### Task 2: TemporalEngine prepare_advance + TickTemporalContext + TemporalAdvancePlan

**Files:** `umbra_core/temporal/engine.py`; wire stub in `runtime.py` (attach only); tests

**Produces:** `prepare_advance` → `TemporalAdvancePlan`; `TickTemporalContext`; `abandon_advance`; no age change until txn apply.

- [ ] **Step 1:** Failing tests: abandoned tick does not advance age; advance_id unique; context uses proposed age.
- [ ] **Step 2:** Implement engine prepare/abandon.
- [ ] **Step 3:** Commit `Add TemporalEngine prepare_advance and TickTemporalContext.`

---

### Task 3: Atomic tick commit + TemporalAdvanceRecord + TemporalTransactionEnvelope

**Files:** `persistence.py`, `events.py`, `runtime.py`, `temporal/events.py`

**Produces:** Shared tick txn applies plan; embeds replay-complete `TemporalAdvanceRecord` (anchors + clock mapping); envelope one state_version/txn; no duplicate `temporal_anchor_committed` on ordinary ticks.

- [ ] **Step 1:** Failing tests: atomic with tick; failed tick no advance record; tick replay reconstructs anchors/mapping; no duplicate anchor event; missing advance fails replay.
- [ ] **Step 2:** Implement apply + event embedding.
- [ ] **Step 3:** Commit `Commit TemporalAdvancePlan atomically with replay-complete tick records.`

---

### Task 4: Recurrence estimator + hypothesis lifecycle

**Files:** `temporal/recurrence.py`, engine observe stubs; tests

**Produces:** Robust median/MAD; phase_anchor; next_index prediction; statuses; occurrence_id vs evidence_identity; recurrence_key.

- [ ] **Step 1:** Failing tests: stable/jittered learn; frequency-only does not ACTIVE; single miss does not erase; fitted prediction; multi-obs one occurrence counts once.
- [ ] **Step 2:** Implement estimator.
- [ ] **Step 3:** Commit `Add robust parametric recurrence estimator for D-010.`

---

### Task 5: Observation plans (IN_TICK / POST_HOC), allowlists, ObservationWindowEvidence, dedup compaction

**Files:** `engine.py`, `experiments/d010/*-allowlist.json` drafts, tests

**Produces:** `TemporalObservationPlan` modes; miss rules; durable dedup digests; A-lane seed-only.

- [ ] **Step 1:** Failing tests from design §2 (+ occurrence/miss/dedup tests).
- [ ] **Step 2:** Implement intake + miss + dedup.
- [ ] **Step 3:** Commit `Add temporal observation plans, miss windows, and durable dedup.`

---

### Task 6: PolicyExpectationView + arbitration modifiers + WAIT + WaitExecution + WaitSuppression

**Files:** `arbitration.py`, `governance.py`, execution/wait persistence, tests

**Produces:** ACTIVE/UNCERTAIN views; capped modifiers; WAIT only in open window; durable WaitExecution; durable WaitSuppression; fallback_bias; O-lane success only.

- [ ] **Step 1:** Failing tests from design §3.
- [ ] **Step 2:** Implement WAIT path without TemporalEngine owning waits.
- [ ] **Step 3:** Commit `Add temporal modifiers, governed WAIT, and durable wait suppression.`

---

### Task 7: Memory temporal_binding + BoundRoutineEligibility

**Files:** `memory/engine.py`, tests

**Produces:** Relative binding fields; eligibility evaluation; Memory-owned promote events referencing recurrence.

- [ ] **Step 1:** Failing tests: multi-episode promote; interruptible; stale version blocked; schedule revision.
- [ ] **Step 2:** Implement binding.
- [ ] **Step 3:** Commit `Extend procedural routines with relative temporal_binding.`

---

### Task 8: Downtime reconciliation + ElapsedTimeContract registry + wait/expectation recovery deltas

**Files:** `engine.py`, `persistence.py`, `experiments/d010/elapsed-contract-registry.json` draft, tests

**Produces:** `downtime_interval_id` journal; trust classes; required vs optional contracts; sticky PREPARED sample; recorded-delta replay; age_advance 0 for non-trusted.

- [ ] **Step 1:** Failing tests from design §4.
- [ ] **Step 2:** Implement reconcile + atomic apply.
- [ ] **Step 3:** Commit `Add TemporalEngine downtime reconciliation and elapsed-time contracts.`

---

### Task 9: Runtime tick classification scanner + production O/T/B migration for T/B sites

**Files:** scanner tooling under `experiments/d010/`; migrate production T/B call sites; tests

**Produces:** Classification inventory; harness fail on unclassified production use; semantic T sites use organism_age_ticks.

- [ ] **Step 1:** Failing test `test_all_production_runtime_tick_uses_are_classified`.
- [ ] **Step 2:** Scanner + migrate critical T/B sites.
- [ ] **Step 3:** Commit `Classify and migrate production runtime.tick temporal dependencies.`

---

### Task 10: Conditions C0–C13 + scenarios S0–S17 scaffolding (harness-only controls)

**Files:** `experiments/d010/` diagnostics/adapters; runtime hooks for P0/C13; tests for production-unreachable controls

- [ ] **Step 1:** Failing tests: controls unreachable; C8 disposable; control rows not in C0.
- [ ] **Step 2:** Implement harness adapters only.
- [ ] **Step 3:** Commit `Add D-010 harness-only conditions and scenario plants.`

---

### Task 11: Stage A definitions + hashes; Stage B freeze bundle

**Files:** Stage A/B JSON artifacts per spec §5.5 including `formal-execution-contract.json`, `test-manifest.json`, `development-seed-manifest.json`, `runtime-tick-classification.json`

- [ ] **Step 1:** Complete Stage A; compute hashes; no placeholders.
- [ ] **Step 2:** Commit Stage B freeze (content-addressed hashes; no self-referential freeze_commit inside bundle).
- [ ] **Step 3:** Record freeze tip; harness refuses dirty freeze.

```bash
git commit -m "Freeze D-010 Stage B preregistration bundle."
```

---

### Task 12: Complete `tests/test_d010.py` minimum list (zero skips)

- [ ] **Step 1:** Ensure all directive §14 + amendment tests present; artifact-reading Gate 13 until evidence exists.
- [ ] **Step 2:** Full suite green (allow pre-existing non-D010 skips only if any; prefer zero in test_d010).
- [ ] **Step 3:** Commit `Complete D-010 minimum test coverage.`

---

### Task 13: Formal experiments Gates 1–12 (isolated)

**Files:** `experiments/d010/run_experiment.py`, `validate_evidence.py`, `docs/evidence/d010/*`

- [ ] **Step 1:** Harness: ≥100 paired seeds; raw-results.jsonl; formal-execution-manifest at run start records freeze_commit; validator recomputes from raw.
- [ ] **Step 2:** Run Gates 1–12; no QUALIFIED; Gate 13 deferred.
- [ ] **Step 3:** Commit evidence; independent review before Task 14.

---

### Task 14: Adaptive S3 performance + seal (isolated)

**Files:** `run_performance.py`, `run_seal.py`, `with_tk_display.sh`, evidence performance/*, `final-verdict.md`

- [ ] **Step 1:** 100k + lifecycle + P0/P1/P2 (comparability rules); recompose.
- [ ] **Step 2:** Zero-skip seal under `with_tk_display.sh`.
- [ ] **Step 3:** QUALIFIED only if earned: `UMBRA_D010_TEMPORAL_CONTINUITY_QUALIFIED`.
- [ ] **Step 4:** Close parent Mimir against seal commit; clean worktree; no leftover processes.
- [ ] **Step 5:** Independent review before operator-final.

---

## Plan self-review

- Spec amendments reflected: advance record complete; transaction envelope; fitted prediction; IN_TICK/POST_HOC; formal contract vs evidence manifest; TimeAnchor trust; seed split; test-manifest.
- Tasks ordered so Stage B freeze precedes formal experiments; Task 13/14 isolated.
- No TemporalEngine action ownership; WAIT in execution system.
- Parent Mimir remains open until Task 14 seal.
