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
- Plan tip: **this amended plan commit** (supersedes `2149297`)
- D-009 seal: `af35371` / `UMBRA_D009_PERSISTENT_HABITAT_AGENCY_QUALIFIED`
- Mimir project: `7777645d52a91b49`; parent task: `9adf61b087ea4fa6a90a1c3bd401a9b3` (open until seal)
- Agent directive: `D-20260724-umbra-d010-temporal-continuity`
- `umbra_core` / `experiments` never import `ui/`
- TemporalEngine never selects/executes actions or launches routines
- C1–C13 harness-only / production-unreachable
- Formal experiments only after Stage B freeze (no placeholder hashes)
- **Nothing may change production/test/harness source after Stage B freeze** except evidence commits
- Final sealed suite: zero skips (no pre-evidence skipped Gate 13 tests)
- Do not edit `.agent/RECORD.md`
- Ponytail: smallest correct diff; reuse D-008/D-009 harness patterns
- Parent Mimir stays open until final seal after independent Task 14 review

## Execution model (Subagent-Driven)

- Fresh implementation subagent per task
- Independent review between tasks (spec + quality)
- No advancement with unresolved Important or Critical findings
- Tasks 13 and 14 isolated from implementation (evidence-only after freeze)
- No formal execution before the final Stage B freeze
- If Task 13/14 reveals a code defect: invalidate freeze → patch source → rerun tests → new Stage B freeze → new `formal_execution_id`

## Regression checkpoints

Require relevant D-001 through D-009 regression suites after:

| After task | Checkpoint |
|------------|------------|
| Task 3 | Atomic runtime/persistence integration |
| Task 6 | Arbitration / governance / WAIT |
| Task 8 | Downtime and cross-subsystem persistence |
| Task 9 | `runtime.tick` migration |
| Task 12 | Final pre-freeze suite (last source-changing commit before Stage B freeze tip) |

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
| `docs/evidence/d010/*` | Evidence pack (Tasks 13–14 only after freeze) |

---

### Task 0: Align governance with amended plan tip

**Files:** `.agent/CURRENT.md`, `.agent/REPO_MAP.md`, `docs/directives/UMBRA-D-010-temporal-continuity.md` (status), `.superpowers/sdd/progress.md`

- [ ] **Step 1:** Point `CURRENT.md` at **this amended plan commit** (not design `03e1269`; not superseded `2149297`). Status = plan approved / SDD starting.
- [ ] **Step 2:** REPO_MAP: design + amended plan paths; `umbra_core/temporal/` planned.
- [ ] **Step 3:** Commit

```bash
git commit -m "Align D-010 governance with amended implementation plan tip."
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
- [ ] **Step 3:** Run D-001…D-009 regression checkpoint (atomic runtime/persistence).
- [ ] **Step 4:** Commit `Commit TemporalAdvancePlan atomically with replay-complete tick records.`

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
- [ ] **Step 3:** Run D-001…D-009 regression checkpoint (arbitration/governance/WAIT).
- [ ] **Step 4:** Commit `Add temporal modifiers, governed WAIT, and durable wait suppression.`

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
- [ ] **Step 3:** Run D-001…D-009 regression checkpoint (downtime / cross-subsystem persistence).
- [ ] **Step 4:** Commit `Add TemporalEngine downtime reconciliation and elapsed-time contracts.`

---

### Task 9: Runtime tick classification scanner + production O/T/B migration for T/B sites

**Files:** scanner tooling under `experiments/d010/`; migrate production T/B call sites; tests

**Produces:** Classification inventory; harness fail on unclassified production use; semantic T sites use organism_age_ticks.

- [ ] **Step 1:** Failing test `test_all_production_runtime_tick_uses_are_classified`.
- [ ] **Step 2:** Scanner + migrate critical T/B sites.
- [ ] **Step 3:** Run D-001…D-009 regression checkpoint (`runtime.tick` migration).
- [ ] **Step 4:** Commit `Classify and migrate production runtime.tick temporal dependencies.`

---

### Task 10: Conditions C0–C13 + scenarios S0–S17 scaffolding (harness-only controls)

**Files:** `experiments/d010/` diagnostics/adapters; runtime hooks for P0/C13; tests for production-unreachable controls

- [ ] **Step 1:** Failing tests: controls unreachable; C8 disposable; control rows not in C0.
- [ ] **Step 2:** Implement harness adapters only.
- [ ] **Step 3:** Commit `Add D-010 harness-only conditions and scenario plants.`

---

### Task 11: Stage A definitions + complete formal harnesses (pre-freeze)

**Files:** Stage A artifacts + **all** formal runners (source must be complete before Stage B)

**Complete in this task (no later source edits after Task 12 freeze):**

```text
experiments/d010/
  authoritative-event-allowlist.json
  observable-evidence-allowlist.json
  elapsed-contract-registry.json
  failure-code registry / temporal event schemas (as needed)
  development-seed-manifest.json
  formal-seed-manifest.json          # uninspected until Stage B; disjoint from development
  formal-seed-nonoverlap rule (in thresholds or dedicated freeze field)
  test-manifest.json                 # all required test IDs
  run_experiment.py
  validate_evidence.py
  run_performance.py
  run_seal.py
  with_tk_display.sh
  runtime-tick classification scanner (final)
```

- [ ] **Step 1:** Complete Stage A definitions; compute Stage A hashes; no placeholders.
- [ ] **Step 2:** Complete experiment/performance/seal harnesses and `with_tk_display.sh`.
- [ ] **Step 3:** Produce `development-seed-manifest.json` and `formal-seed-manifest.json` with explicit nonoverlap rule; formal seeds remain uninspected before Stage B.
- [ ] **Step 4:** Complete `test-manifest.json` enumerating every required test ID (including Gate 13 harness-contract tests — **not** skipped placeholders).
- [ ] **Step 5:** Commit Stage A + harnesses (still pre-freeze; Task 12 freezes Stage B).

```bash
git commit -m "Complete D-010 Stage A definitions and formal harnesses."
```

---

### Task 12: Complete tests + final Stage B freeze (last source-changing commit)

**Files:** `tests/test_d010.py`; Stage B freeze JSON; thresholds; matrix; scenario-suite; formal-execution-contract.json; runtime-tick-classification.json

**Critical rules:**

- **No skipped / placeholder Gate 13 tests.** Code-level tests validate performance and seal **harness contracts**. Evidence-dependent qualification runs only through the frozen seal harness after evidence exists (Tasks 13–14).
- Final Stage B freeze is the **last production/test/harness source-changing commit**.
- After this freeze tip: Tasks 13–14 may commit **evidence only**.

- [ ] **Step 1:** Complete all directive §14 + amendment tests; zero skips in `test_d010.py`.
- [ ] **Step 2:** Run final pre-freeze regression (D-001…D-009 + full D-010 suite).
- [ ] **Step 3:** Commit Stage B freeze bundle (`thresholds`, matrix, scenarios, formal-execution-contract, classification, seed manifests hashes, Stage A hashes, test-manifest hash, `implementation_source_hash`, allowed verdicts). No self-referential `freeze_commit` inside the bundle.
- [ ] **Step 4:** Record freeze tip; harness refuses dirty freeze / placeholder hashes / unclassified production ticks.

```bash
git commit -m "Freeze D-010 Stage B preregistration bundle."
```

---

### Task 13: Formal experiments Gates 1–12 (isolated; evidence only)

**Constraint:** Frozen source tip from Task 12. **Evidence commits only.** No harness/test/code edits.

**Files:** `docs/evidence/d010/*` (and evidence formal-execution-manifest.json recording `freeze_commit` at run start)

- [ ] **Step 1:** Run frozen Gates 1–12 harness (≥100 paired formal seeds); raw-results.jsonl; validator recomputes from raw.
- [ ] **Step 2:** No QUALIFIED; Gate 13 deferred to Task 14.
- [ ] **Step 3:** Commit evidence only.
- [ ] **Step 4:** Independent review; fix Critical/Important only via freeze-invalidate path if code defects found.

---

### Task 14: Adaptive S3 performance + seal (isolated; evidence then review then seal close)

**Constraint:** Same frozen source tip. Evidence + seal artifacts only unless freeze invalidated.

**Order (mandatory):**

```text
1. Execute frozen 100k + lifecycle + P0/P1/P2 + recompose
2. Produce provisional seal artifacts / final-verdict draft
3. Independent Task 14 review
4. Resolve all Important/Critical findings
   (code defects → invalidate freeze → patch → tests → new Stage B → new formal_execution_id)
5. Commit final seal
6. Close parent Mimir against that seal commit
7. Verify clean worktree and zero leftover processes
```

- [ ] **Step 1:** Run frozen performance matrix (comparability rules); commit evidence.
- [ ] **Step 2:** Run frozen seal under `with_tk_display.sh`; zero skips; every required test-manifest ID executed.
- [ ] **Step 3:** Independent review; resolve Critical/Important.
- [ ] **Step 4:** Commit final seal (`UMBRA_D010_TEMPORAL_CONTINUITY_QUALIFIED` only if earned).
- [ ] **Step 5:** Close parent Mimir `9adf61b087ea4fa6a90a1c3bd401a9b3` against seal tip.
- [ ] **Step 6:** Clean worktree; no leftover soak/Xvfb/runtime processes.

---

## Plan self-review

- Task 0 points CURRENT at **amended plan tip**, not design `03e1269` / not `2149297`.
- Stage A + all runners complete in Task 11; all tests + Stage B freeze in Task 12 (last source change).
- Tasks 13–14 evidence-only; freeze-invalidate path documented.
- Separate development/formal seed manifests + nonoverlap; formal seeds uninspected pre-Stage B.
- No pre-evidence skipped Gate 13 tests; seal runs required IDs with zero skips.
- Regression checkpoints after Tasks 3, 6, 8, 9, 12.
- Task 14: provisional evidence → independent review → final seal → Mimir close.
- Parent Mimir remains open until Task 14 seal after review.
