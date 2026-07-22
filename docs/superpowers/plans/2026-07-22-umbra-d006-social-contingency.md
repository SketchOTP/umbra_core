# UMBRA-D-006 Social Contingency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Qualify partner-specific social contingency and history-dependent relationships without affection scores, per the approved design at `docs/superpowers/specs/2026-07-22-umbra-d006-social-contingency-design.md`.

**Architecture:** New `umbra_core/social/` SocialEngine owns recognition hypotheses, EMA contingency tables, satiation derivation, pending interaction lifecycle, and routine eligibility. MemoryEngine owns finalized episodes and procedural routine persistence. Embodiment hosts hidden partner entities and noisy cues. Runtime proposes soft social intents; governance authorizes hybrid actuation including thin `SIGNAL_PLAY` / `SIGNAL_ASSISTANCE`. Authoritative social events are ledger-sourced; outcome finalization is one SQLite transaction.

**Tech Stack:** Python 3 stdlib, SQLite WAL (`umbra_core/persistence.py`), existing `umbra_core` organism loop, pytest.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-22-umbra-d006-social-contingency-design.md` (commit `0813a06`+)
- Starting commit for directive work: `70dd08ee3d664b6eda1968ca7129a953622d45bc`
- Mimir project: `7777645d52a91b49`; agent directive: `D-20260722-umbra-d006-social-contingency`
- No LLM, no emotion/attachment labels, no affection meter in production schemas
- Hidden `partner_id` is evaluator-only — never enters SocialEngine / MemoryEngine / arbitration / routines
- C3 affection controller lives only under `experiments/d006/`
- Physiology critical + governance remain authoritative over social proposals
- Final sealed test suite: zero skips
- Do not edit `.agent/RECORD.md`
- Ponytail: smallest correct diff; reuse D-005 patterns

## File map

| Path | Responsibility |
|------|----------------|
| `umbra_core/social/__init__.py` | Public exports |
| `umbra_core/social/engine.py` | SocialEngine, hypotheses, contingency, pending, satiation, propose |
| `umbra_core/events.py` | Authoritative social event types + authority map |
| `umbra_core/embodiment.py` | `SIGNAL_*` capabilities; PartnerEntity; noisy cues |
| `umbra_core/perception.py` | Expose cue fields without hidden id |
| `umbra_core/governance.py` | Signal cost/cooldown; deny unauthorized |
| `umbra_core/persistence.py` | Atomic outcome transaction helper; evidence-link table |
| `umbra_core/runtime.py` | Wire social tick path; config/ablations |
| `umbra_core/memory/engine.py` | Episode finalize hook; social procedural promotion |
| `experiments/d006/thresholds.json` | Preregistered numeric gates (freeze before experiments) |
| `experiments/d006/experiment-matrix.json` | Frozen curated cells |
| `experiments/d006/affection_controller.py` | C3-only isolated controller |
| `experiments/d006/run_experiment.py` | C×H harness |
| `experiments/d006/run_performance.py` | 100k + soak |
| `experiments/d006/run_closeout.py` | Seal aggregator |
| `tests/test_d006.py` | All D-006 tests |
| `docs/directives/UMBRA-D-006-social-contingency.md` | Directive copy |
| `docs/evidence/d006/*` | Evidence pack |
| `.agent/*` | Governance tracking (not RECORD) |

---

### Task 1: Governance bootstrap + directive + freeze files

**Files:**
- Create: `docs/directives/UMBRA-D-006-social-contingency.md`
- Create: `experiments/d006/thresholds.json`
- Create: `experiments/d006/experiment-matrix.json`
- Modify: `.agent/CURRENT.md`, `.agent/DIRECTIVES.md`, `.agent/PROJECT_PROFILE.md`, `.agent/REPO_MAP.md`

**Interfaces:**
- Produces: frozen numeric thresholds and matrix consumed by later experiment/tests

- [ ] **Step 1: Append directive start to `.agent/DIRECTIVES.md` and update CURRENT/PROFILE**

Set active directive to UMBRA-D-006 / `D-20260722-umbra-d006-social-contingency`. Update program status: D-005 QUALIFIED; D-006 active; D-007 blocked.

- [ ] **Step 2: Write `experiments/d006/thresholds.json`**

Include at minimum:

```json
{
  "paired_seeds_gate_critical": 100,
  "contingency_effect_size_min": 0.15,
  "history_effect_size_min": 0.12,
  "ci_confidence": 0.95,
  "recognition_accuracy_min": 0.70,
  "false_merge_rate_max": 0.05,
  "false_split_rate_max": 0.10,
  "swap_detection_latency_ticks_max": 40,
  "ambiguous_left_unknown_min": 0.80,
  "routine_h10_reproduce_fraction_min": 0.60,
  "routine_min_independent_episodes": 3,
  "response_window_contingent_ticks": [1, 8],
  "response_window_delayed_ticks": [9, 24],
  "response_window_none_timeout_ticks": 32,
  "max_active_evidence_refs": 32,
  "max_active_supporting_episodes": 24,
  "max_active_contradicting_episodes": 24,
  "max_source_hypothesis_ids": 8,
  "max_routine_supporting_episodes": 24,
  "max_partner_hypotheses": 16,
  "max_contingency_cells": 256,
  "max_pending_interactions": 8,
  "signal_cooldown_ticks": 6,
  "satiation_rise": 0.12,
  "satiation_decay_per_tick": 0.002,
  "recognition_match_threshold": 0.55,
  "recognition_contest_gap_max": 0.08,
  "rss_p95_mib_max": 180,
  "rss_slope_mib_per_hour_max": 1.0,
  "cpu_mean_frac_max": 0.05
}
```

- [ ] **Step 3: Write `experiments/d006/experiment-matrix.json`**

Define mandatory gate-critical cells (each with `paired_seeds: 100`) covering Gates 1–7 comparisons (C0 vs C1/C9 on H0/H1; history probes H0 vs H1/H2/H5/H6; recognition H8/H9; satiation C0 vs C5; absence H7; routines H10 vs C8). Mark exploratory cells with fewer seeds and rationale. List exclusions.

- [ ] **Step 4: Write directive markdown summarizing objective, constraints, verdicts (link design+thresholds)**

- [ ] **Step 5: Commit**

```bash
git add docs/directives/UMBRA-D-006-social-contingency.md experiments/d006/thresholds.json experiments/d006/experiment-matrix.json .agent/CURRENT.md .agent/DIRECTIVES.md .agent/PROJECT_PROFILE.md .agent/REPO_MAP.md
git -c user.name='SketchOTP' -c user.email='sketchotp@gmail.com' commit -m "Preregister UMBRA-D-006 thresholds, matrix, and directive bootstrap."
```

---

### Task 2: Signal capabilities + event authority registry

**Files:**
- Modify: `umbra_core/embodiment.py` (CAPABILITIES + actuation)
- Modify: `umbra_core/governance.py` (cooldown/cost)
- Modify: `umbra_core/events.py`
- Test: `tests/test_d006.py` (start file)

**Interfaces:**
- Produces: `"SIGNAL_PLAY"`, `"SIGNAL_ASSISTANCE"` in `CAPABILITIES`
- Produces: `SOCIAL_EVENT_AUTHORITY` map; types in `AUTHORITATIVE_EVENT_TYPES`
- Consumes: existing `Governance.admit` / embodiment `actuate`

- [ ] **Step 1: Write failing tests**

```python
def test_signal_capabilities_exist_and_are_governed():
    from umbra_core.embodiment import CAPABILITIES
    assert "SIGNAL_PLAY" in CAPABILITIES
    assert "SIGNAL_ASSISTANCE" in CAPABILITIES

def test_social_event_authority_classes():
    from umbra_core.events import social_event_authority_class
    assert social_event_authority_class("social_pending_created") == "AUTHORITATIVE"
    assert social_event_authority_class("social_recognition_updated") == "AUTHORITATIVE"
    assert social_event_authority_class("social_match_score") == "DIAGNOSTIC"
```

- [ ] **Step 2: Run to verify fail**

`pytest tests/test_d006.py::test_signal_capabilities_exist_and_are_governed tests/test_d006.py::test_social_event_authority_classes -v`

- [ ] **Step 3: Implement**

Extend `CAPABILITIES` with the two signals. Actuation: no movement; emit environmental event payload `{kind: "social_signal", signal, tick}` only. Governance: admit with cooldown from thresholds default (6 ticks) and tiny energy cost; unknown social authority fails closed.

In `events.py`:

```python
SOCIAL_EVENT_AUTHORITY = {
    "social_hypothesis_created": "AUTHORITATIVE",
    "social_hypothesis_merged": "AUTHORITATIVE",
    "social_hypothesis_split": "AUTHORITATIVE",
    "social_hypothesis_contested": "AUTHORITATIVE",
    "social_hypothesis_retired": "AUTHORITATIVE",
    "social_recognition_updated": "AUTHORITATIVE",
    "social_pending_created": "AUTHORITATIVE",
    "social_pending_resolved": "AUTHORITATIVE",
    "social_pending_expired": "AUTHORITATIVE",
    "social_pending_interrupted": "AUTHORITATIVE",
    "social_contingency_updated": "AUTHORITATIVE",
    "social_reliability_revised": "AUTHORITATIVE",
    "social_satiation_anchor_updated": "AUTHORITATIVE",
    "social_routine_promoted": "AUTHORITATIVE",
    "social_routine_deactivated": "AUTHORITATIVE",
    "social_match_score": "DIAGNOSTIC",
}
# Add AUTHORITATIVE names into AUTHORITATIVE_EVENT_TYPES
```

- [ ] **Step 4: Tests pass; commit**

```bash
git commit -m "Add SIGNAL_* capabilities and social event authority registry."
```

---

### Task 3: Habitat partner entities + noisy cue perception

**Files:**
- Modify: `umbra_core/embodiment.py`
- Modify: `umbra_core/perception.py`
- Test: `tests/test_d006.py`

**Interfaces:**
- Produces: `PartnerEntity(hidden_partner_id, x, y, true_cues, response_policy)` plantable on Habitat
- Produces: policy observations with cue fields only (no `partner_id`)
- Produces: `Embodiment.hidden_partner_truth_for_eval()` evaluator-only accessor

- [ ] **Step 1: Failing tests**

```python
def test_policy_cannot_access_hidden_partner_id():
    # create organism with partner plant; inspect observation dict keys
    ...
    assert "partner_id" not in obs
    assert "hidden_partner_id" not in obs

def test_hidden_partner_id_is_evaluator_only():
    truth = emb.hidden_partner_truth_for_eval()
    assert "partner_id" in truth[0]
    # ensure social engine / observations never receive it
```

- [ ] **Step 2: Implement PartnerEntity + noisy cue generation**

Cue fields: `relative_position`, `motion_signature`, `appearance_signature`, `response_timing_pattern`, `interaction_style_cues`, `cue_confidence`, `cue_uncertainty`. Noise from `SeededRNG`; no permanently unique perfect cues.

Partner response policies for histories H0–H10 (contingent windows, noncontingent, absent, swap, ambiguous cue overlap).

- [ ] **Step 3: Tests pass; commit**

```bash
git commit -m "Plant habitat partners with noisy multimodal cues; hide partner_id from policy."
```

---

### Task 4: SocialEngine core — hypotheses, recognition, satiation derivation

**Files:**
- Create: `umbra_core/social/__init__.py`, `umbra_core/social/engine.py`
- Test: `tests/test_d006.py`

**Interfaces:**
- Produces:
  - `PartnerHypothesis` dataclass (status ∈ {UNKNOWN,FAMILIAR,CONTESTED,INACTIVE})
  - `SocialConfig` + `condition_to_social_config(condition: str) -> SocialConfig`
  - `SocialEngine.recognize(cues, tick) -> RecognitionResult`
  - `SocialEngine.current_satiation(hypothesis_id, tick) -> float` (derived)
  - `SocialEngine.expected_response_latency(hypothesis_id) -> float | None` (derived)
  - `SocialEngine.to_state()` / `from_state()`
- Consumes: thresholds caps; event emit callback

- [ ] **Step 1: Failing tests**

```python
def test_partner_identity_is_uncertain():
    ...
def test_ambiguous_partner_remains_unknown():
    ...
def test_expected_response_latency_is_derived():
    ...
def test_provenance_active_sets_are_bounded():
    ...
```

- [ ] **Step 2: Implement engine skeleton**

Recognition: maintain multiple hypotheses; match cue prototypes with confidence; contest when top-two gap < threshold; UNKNOWN when below match threshold; emit `social_recognition_updated` only for accepted anchors / lifecycle-changing updates; per-tick decay is derived.

Satiation: store `satiation_anchor`, `last_satiation_update_tick`, `decay_parameters`; derive current value.

C4 config: `persist_relationship=False` → reset hypotheses at encounter boundaries and on restart.

C6: `recognition_enabled=False` → always UNKNOWN.

- [ ] **Step 3: Tests pass; commit**

```bash
git commit -m "Add SocialEngine recognition hypotheses and derived satiation/latency."
```

---

### Task 5: Pending interactions + contingency classification + atomic commit

**Files:**
- Modify: `umbra_core/social/engine.py`
- Modify: `umbra_core/persistence.py` (transaction helper + `social_evidence_links` table)
- Modify: `umbra_core/memory/engine.py` (finalize episode API used inside txn)
- Test: `tests/test_d006.py`

**Interfaces:**
- Produces:
  - `SocialEngine.create_pending(...)` → emits `social_pending_created`
  - `SocialEngine.resolve_pending(..., classification)` inside `Persistence.atomic_social_outcome(...)`
  - `classify_response(...)` with precedence EXTERNAL→AMBIGUOUS→CONTINGENT→DELAYED→COINCIDENTAL→NONE
  - `ContingencyCell` updates + reliability_by_context revision
- Consumes: executed signal only (not proposals)

- [ ] **Step 1: Failing tests**

```python
def test_denied_signal_creates_no_partner_evidence(): ...
def test_response_classification_precedence(): ...
def test_overlapping_bids_resolve_ambiguous(): ...
def test_contingency_beats_frequency(): ...  # unit-level mini
def test_noncontingent_events_do_not_build_reliability(): ...
def test_atomic_outcome_commit_crash_between_stages(): ...
def test_pending_survives_restart_or_resolves_deterministically(): ...
def test_pending_cannot_become_evidence_twice(): ...
def test_missing_authoritative_social_event_fails_closed(): ...
```

- [ ] **Step 2: Implement classification using `thresholds.json` windows**

- [ ] **Step 3: Implement `Persistence.atomic_social_outcome(stages)`**

Stages in order (crash injection hook between each):

1. finalize immutable episode  
2. append episode event  
3. update contingency evidence (+ evidence links)  
4. revise reliability  
5. append social authority events (`social_pending_resolved|…`, `social_contingency_updated`, `social_reliability_revised`)

On crash injection: raise after stage N before commit; assert no partial durable state.

- [ ] **Step 4: Restart path for pending**

Reload unresolved pendings; if window elapsed → expire/interrupt deterministically with authority events; else resume. Never silent drop; never double-evidence.

- [ ] **Step 5: Tests pass; commit**

```bash
git commit -m "Event-source pending social interactions with atomic contingency commits."
```

---

### Task 6: Merge/split provenance + reliability revision rules

**Files:**
- Modify: `umbra_core/social/engine.py`
- Test: `tests/test_d006.py`

**Interfaces:**
- Produces: `merge_hypotheses(ids) -> new_id`, `split_hypothesis(id, evidence_partition) -> (id_a, id_b)`
- Rules: non-destructive; `source_hypothesis_ids` bounded; full links in ledger

- [ ] **Step 1: Failing tests**

```python
def test_hypothesis_merge_preserves_provenance(): ...
def test_hypothesis_split_preserves_provenance(): ...
def test_partner_swap_is_detected(): ...
def test_partner_models_remain_separate(): ...
def test_single_failure_does_not_destroy_reliability(): ...
def test_repeated_failure_revises_expectation(): ...
def test_recovery_history_revises_expectation(): ...
```

- [ ] **Step 2: Implement; tests pass; commit**

```bash
git commit -m "Add non-destructive hypothesis merge/split and reliability revision rules."
```

---

### Task 7: Soft social proposals + hybrid actuation wiring in runtime

**Files:**
- Modify: `umbra_core/runtime.py` (`OrganismConfig.social_enabled`, `social_history`, condition ownership)
- Modify: `umbra_core/social/engine.py` (`propose(...)`)
- Modify: `umbra_core/arbitration.py` only if needed for wait metadata
- Test: `tests/test_d006.py`

**Interfaces:**
- Produces: `SocialEngine.propose(phys, cues, tick, critical) -> Candidate | None`
- Mapping per design table; C7 random; C5 ignore satiation; C1 familiarity-only preference
- Pin self/world/memory configs to C0 when `social_enabled` owns condition (same pattern as D-005)

- [ ] **Step 1: Failing tests for proposal mapping + governance bypass refusal**

```python
def test_social_urgency_cannot_bypass_governance(): ...
def test_relationship_memory_cannot_grant_authority(): ...
def test_scalar_affection_is_not_relationship_authority(): ...
```

- [ ] **Step 2: Wire tick path after memory bias, before governance**

Order: recognize → (resolve pendings) → propose social soft candidate if not critical → arbitrate/govern → on SIGNAL execute create pending.

- [ ] **Step 3: Tests pass; commit**

```bash
git commit -m "Wire hybrid social proposals into runtime without granting authority."
```

---

### Task 8: Shared routines via D-005 procedural promotion

**Files:**
- Modify: `umbra_core/social/engine.py`
- Modify: `umbra_core/memory/engine.py` (`promote_social_routine(...)`)
- Test: `tests/test_d006.py`

**Interfaces:**
- Produces: eligibility check after N independent successful chains; `MemoryEngine.promote_social_routine(spec) -> skill_id`
- Procedural applicability includes `partner_hypothesis`, `context`, ordered soft proposals, interrupt conditions, satiation constraints
- C8: authored script path in experiments only — never counted as learned

- [ ] **Step 1: Failing tests**

```python
def test_shared_routine_is_learned(): ...
def test_shared_routine_is_interruptible(): ...
def test_scripted_routine_is_not_development(): ...
def test_relationship_state_has_episode_provenance(): ...
```

- [ ] **Step 2: Implement; tests pass; commit**

```bash
git commit -m "Promote contingent chains into partner-scoped D-005 procedural routines."
```

---

### Task 9: Ablations C0–C9 + C3 isolated controller + C4 reset semantics

**Files:**
- Modify: `umbra_core/social/engine.py` (`condition_to_social_config`)
- Create: `experiments/d006/affection_controller.py` (C3 only)
- Test: `tests/test_d006.py`

- [ ] **Step 1: Failing tests**

```python
def test_c3_affection_controller_is_isolated():
    import umbra_core.social.engine as eng
    assert not hasattr(eng, "AffectionMeter")
    from experiments.d006.affection_controller import AffectionController
    assert AffectionController is not None

def test_c4_resets_relationship_state_between_encounters(): ...
```

- [ ] **Step 2: Implement all ablation switches; tests pass; commit**

```bash
git commit -m "Implement D-006 social ablations; isolate C3 affection under experiments/."
```

---

### Task 10: Persistence, restart, replay contracts

**Files:**
- Modify: `umbra_core/runtime.py` snapshot include `social`
- Modify: `umbra_core/persistence.py` / events as needed
- Test: `tests/test_d006.py`

- [ ] **Step 1: Failing tests**

```python
def test_restart_preserves_partner_models(): ...
def test_birth_and_snapshot_replay_match(): ...
def test_partner_and_routine_counts_are_bounded(): ...
def test_prior_seals_validate(): ...
def test_prior_regressions_pass(): ...  # import/run key prior assertions or subprocess pytest subset
def test_no_deferred_modules_added(): ...
```

- [ ] **Step 2: Implement snapshot+ledger reconstruction; fail closed on missing social authority; tests pass; commit**

```bash
git commit -m "Persist and replay social hypotheses via authoritative events."
```

---

### Task 11: Full `tests/test_d006.py` suite completion

**Files:**
- Modify: `tests/test_d006.py`

Ensure every directive-required and design-added test exists and passes (or is explicitly marked pre-soak skip **only** for performance soak until Task 13). Include absence/manipulation tests:

```python
def test_social_interaction_satiates(): ...
def test_absence_does_not_escalate_bids(): ...
def test_absence_does_not_increase_bid_frequency(): ...
def test_absence_does_not_damage_viability(): ...
def test_absence_does_not_reduce_relationship_state_as_punishment(): ...
def test_different_histories_change_behavior(): ...
```

- [ ] **Step 1: Fill remaining tests; run `pytest tests/test_d006.py -v`**
- [ ] **Step 2: Run `pytest tests/ -q` regression**
- [ ] **Step 3: Commit**

```bash
git commit -m "Complete UMBRA-D-006 unit and contract test suite."
```

---

### Task 12: Experiment harness + evidence generation

**Files:**
- Create: `experiments/d006/run_experiment.py`
- Create: `experiments/d006/run_closeout.py`
- Create: `docs/evidence/d006/*.json` (results)

- [ ] **Step 1: Implement harness reading frozen matrix/thresholds; ≥100 paired seeds for gate-critical cells**
- [ ] **Step 2: Run experiments; write recognition/contingency/history/reliability/satiation/absence/routine/governance/replay/event-authority/manipulation results**
- [ ] **Step 3: Assert gates 1–9 numerically against thresholds; fail closed if C3 leaks into production schemas**
- [ ] **Step 4: Commit results (not thresholds/matrix replacements)**

```bash
git commit -m "Record UMBRA-D-006 experiment evidence against frozen matrix."
```

---

### Task 13: Performance gate + soak + final seal

**Files:**
- Create: `experiments/d006/run_performance.py`
- Create: `docs/evidence/d006/performance-results.json`, `prior-seals.json`, `schema-manifest.json`, `evidence-hashes.json`, `final-verdict.md`
- Modify: `.agent/OUTCOMES.md`, `.agent/CURRENT.md`, `.agent/LEARNINGS.md` (if durable), `.agent/REPO_MAP.md`, `.agent/PROJECT_PROFILE.md`
- Remove any pre-soak skips for final suite

- [ ] **Step 1: 100k accelerated ticks + 2h RUNTIME_READY VmRSS soak; write performance-results**
- [ ] **Step 2: `pytest tests/ -q` → 0 skipped**
- [ ] **Step 3: Hash design + thresholds + matrix + sources + tests + all results into `evidence-hashes.json`**
- [ ] **Step 4: Write `final-verdict.md` with allowed verdict only**
- [ ] **Step 5: Mimir validation/evidence/close against final commit**
- [ ] **Step 6: Commit seal; ensure clean worktree**

```bash
git commit -m "Seal UMBRA-D-006 social contingency with evidence and verdict."
```

---

## Plan self-review

**Spec coverage:** Architecture, hybrid actuation, recognition, contingency+atomic commit, pending authority, satiation/absence, routines via D-005 procedural, ablations C0–C9, gates 0–13, tests, evidence files (including event-authority + manipulation), freeze files, provenance caps, Gate 8 wording, paired seeds — each maps to tasks 1–13.

**Placeholders:** None intentional; numeric values live in Task 1 `thresholds.json`.

**Type consistency:** `SocialEngine`, `PartnerHypothesis`, `ContingencyCell`, pending events, and `atomic_social_outcome` names are stable across tasks.

**Risk notes from Mimir:** When `social_enabled` owns condition, pin self/world/memory configs to C0 (same lesson as D-005).
