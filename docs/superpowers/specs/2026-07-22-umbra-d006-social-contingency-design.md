# UMBRA-D-006 Design: Social Contingency and History-Dependent Relationships

**Date:** 2026-07-22  
**Project directive:** UMBRA-D-006  
**Agent memory directive:** `D-20260722-umbra-d006-social-contingency`  
**Starting commit:** `70dd08ee3d664b6eda1968ca7129a953622d45bc`  
**Mimir project:** `7777645d52a91b49`  
**Status:** Design approved; proceed to implementation plan  
**Amendment note:** Final amendments applied 2026-07-22 (atomic episode/contingency commits, pending event authority, recognition events, provenance caps, Gate 8 wording, paired-seed coverage).

## Purpose

Enable UMBRA to form **partner-specific expectations from contingent interaction and shared history**, not affection scores or interaction counts.

UMBRA must distinguish partners under uncertainty, learn responsiveness and reliability, prefer or avoid interaction from verified experience, develop bounded shared routines, satiate social interaction, adapt when partners change, and continue safely during absence.

This design does **not** implement emotion labels, language, personality, romance, or human-like attachment claims.

## Locked decisions

1. **Hybrid social actuation:** existing embodiment capabilities for movement and observation, plus narrowly scoped governed signal capabilities (`SIGNAL_PLAY`, `SIGNAL_ASSISTANCE`) for explicit partner-directed bids.
2. **Embodied partners:** habitat partner entities observed only through noisy multimodal cue vectors. Hidden `partner_id` is evaluator-only.
3. **Contingency models:** bounded per-partner contingency tables with EMA latency and calibrated response distributions. Immutable D-005 episodes provide provenance; frequency alone cannot create reliability.
4. **Routines:** partner-specific shared routines by promoting repeated successful contingent chains into bounded D-005 procedural memories. C8 authored scripts are ablation-only.
5. **Packaging:** `umbra_core/social/` SocialEngine with thin runtime and embodiment hooks (Approach 1).

## Hard constraints

* No LLM or language.
* No emotion or attachment labels; no authored affection progression.
* No engagement-maximization objective.
* No guilt, jealousy, exclusivity, abandonment threats, or fabricated emergencies.
* No direct command to bond, trust, fear, forgive, or miss someone.
* Memory cannot grant authority; partner reliability cannot bypass governance.
* Absence cannot cause death or irreversible damage.
* Relationship models, histories, and routines remain bounded.
* Hidden `partner_id` never enters SocialEngine, MemoryEngine, arbitration, or routine formation.

## Scientific claims

**Authorized (bounded):** partner-specific contingency learning from verified interaction history under uncertainty.

**Not authorized:** genuine affection, attachment, emotion, personality, consciousness, human-equivalent relationship, complete companion.

---

## 1. Architecture

```text
Embodiment (truth)
  └─ PartnerEntity {hidden_partner_id, true cues, response policy}
        │ noisy observations only
        ▼
Perception membrane
        │ cue vector + uncertainty (no partner_id)
        ▼
SocialEngine
  ├─ Recognition: hypotheses, confidence decay, CONTESTED/UNKNOWN
  ├─ Contingency tables: (hypothesis, context, signal) → EMA + counts
  ├─ PartnerModel estimates: familiarity ≠ reliability
  ├─ Satiation / absence (no escalation, no absence-punishment)
  └─ Routine eligibility → request MemoryEngine ProceduralMemory promotion
        │ soft proposals only
        ▼
Runtime arbitration ──► Governance ──► Embodiment actuation
        │
        └── finalized episodes → MemoryEngine (provenance authority)
```

### Ownership

| Component | Owns |
|-----------|------|
| SocialEngine | Recognition, partner hypotheses, contingency models, satiation/absence handling, routine eligibility |
| MemoryEngine | Immutable episodes, provenance, semantic support/contradiction, procedural routine persistence |
| WorldModel | Current spatial partner tracking only (transient) |
| Runtime | Observations in; soft social proposals out |
| Governance | Authorization of all resulting capabilities |
| Embodiment | Hidden partner entities and noisy cue generation |

### Hard boundary

SocialEngine may influence proposals and memory formation. It may **not** execute actions, grant authority, write physiology directly, or treat recognized identity as certain.

### Event sourcing (required)

SocialEngine state **cannot exist only in snapshots**. Authoritative changes are event-sourced so birth replay reconstructs:

* partner-hypothesis creation, merge, split, contest, and retirement;
* recognition-confidence changes that affect behavior (`social_recognition_updated`);
* pending interaction lifecycle (`social_pending_created|resolved|expired|interrupted`);
* contingency updates;
* reliability revisions;
* satiation anchor updates;
* routine promotion or deactivation.

Snapshots may accelerate recovery but are not sole history. Missing authoritative social events fail closed on replay.

### Atomic outcome commit (required)

The following must occur in **one SQLite transaction**:

```text
finalize immutable episode
→ append episode event
→ update contingency evidence
→ revise reliability
→ append social authority events
```

A crash must not leave an episode without its aggregate update, a contingency update without its episode, or reliability pointing to nonexistent evidence. Crash-injection tests between each stage are required.

### Additional boundaries

* Recognition hypothesis IDs are internal estimates and **never equal** the hidden `partner_id`.
* WorldModel owns current spatial tracking; SocialEngine owns longitudinal partner hypotheses.
* MemoryEngine owns episodes and procedural records; SocialEngine only **requests** routine promotion.
* Ambiguous or contested recognition cannot update an established partner model directly.
* Social signals produce environmental events; they never directly produce relationship changes.

---

## 2. Data model

### Partner hypothesis (SocialEngine)

```text
hypothesis_id                 # internal estimate; never equals hidden partner_id
status                        # UNKNOWN | FAMILIAR | CONTESTED | INACTIVE
recognition_confidence
cue_prototype                 # noisy multimodal summary; never permanently unique
familiarity                   # from encounter frequency only
responsiveness
reliability_by_context        # context → calibrated estimate (not global status)
# expected_response_latency   # DERIVED summary of contingency cells — not stored
interaction_preference_by_context   # contextual; not a scalar affection meter
satiation_anchor              # canonical: value at last_satiation_update_tick
uncertainty
last_interaction_tick
last_satiation_update_tick
decay_parameters
evidence_refs                 # bounded active episode_id set (see provenance caps)
source_hypothesis_ids         # bounded merge/split links (see provenance caps)
```

**Status vs reliability:** status is recognition/lifecycle only. Reliability is always context-specific (e.g. reliable for play, unreliable for assistance).

**Derived latency:** partner-level `expected_response_latency` is a derived summary of contingency-cell `latency_ema` values (weighted by confidence/count). Do not persist a separate partner-level latency field.

**No second global social drive.** Use existing physiology `stimulation` plus derived social opportunity and per-partner satiation. Derived social priority is non-authoritative and must not be persisted as physiology.

### Contingency cell

Key: `(recognized_partner_hypothesis, context, organism_signal)`

```text
response_distribution
latency_ema
latency_variance
contingent_count
delayed_count
none_count
ambiguous_count
external_count
confidence
supporting_episode_ids        # bounded active set (see provenance caps)
contradicting_episode_ids     # bounded active set (see provenance caps)
last_updated
```

**Rules:**

* Reliability increases only from temporally plausible contingent responses.
* Interaction frequency alone changes familiarity, not reliability.
* Coincidental or externally caused events do not count as support.
* Ambiguous recognition updates no partner-specific model until resolved.
* Contested hypotheses may update temporary evidence but not established identity history.
* One anomalous response weakens confidence slightly; repeated contradiction triggers revision.
* Tables bounded by partner hypotheses, contexts, and signals.
* Every aggregate update references immutable D-005 episodes.
* Generic population priors may initialize unknown partners but must never overwrite partner-specific evidence.

### Provenance caps (required)

These collections must not grow unboundedly in working state:

```text
evidence_refs
supporting_episode_ids
contradicting_episode_ids
source_hypothesis_ids
routine.supporting_episode_ids
```

**Semantics (preregister exact caps in `thresholds.json` / schema):**

* Aggregate counts remain in the model.
* Bounded active reference sets remain in memory (ring / most-recent + high-salience retention).
* Complete provenance remains recoverable through normalized evidence-link tables and/or the event ledger.
* No historical provenance is silently destroyed — eviction from the active set must leave ledger/link recoverability.

Recommended default active caps (override only via preregistered thresholds):

```text
MAX_ACTIVE_EVIDENCE_REFS = 32
MAX_ACTIVE_SUPPORTING_EPISODES = 24
MAX_ACTIVE_CONTRADICTING_EPISODES = 24
MAX_SOURCE_HYPOTHESIS_IDS = 8
MAX_ROUTINE_SUPPORTING_EPISODES = 24
```

### Pending interaction trace (pre-episode)

Created when a social signal is **executed** (not merely proposed). Pending traces are **event-sourced**:

```text
social_pending_created
social_pending_resolved
social_pending_expired
social_pending_interrupted
```

Durable fields:

```text
pending_interaction_id
hypothesis_id_at_signal
recognition_confidence
context
signal
execution_id
signal_tick
response_window
```

Finalize a D-005 episode only after verified response, timeout, ambiguous outcome, or interruption. Incomplete pending traces are not settled history.

After restart, unresolved traces must either:

* resume from durable timing state; or
* deterministically resolve as interrupted/expired.

They must never disappear silently or become partner evidence twice.

### Satiation / absence (derived)

Do **not** persist per-tick decay fields. Derive current satiation and absence duration from:

```text
last_interaction_tick
last_satiation_update_tick
satiation_anchor              # canonical value at last_satiation_update_tick
decay_parameters
```

Only meaningful accepted changes require authoritative events (satiation anchor updates).

### Routine (D-005 ProceduralMemory specialization)

```text
routine_id
partner_hypothesis
context
ordered soft proposals
success conditions
interrupt conditions
body requirements
social satiation constraints
confidence
attempts
successes
failures
supporting_episode_ids
status
```

No separate routine store. SocialEngine holds eligibility and handles; MemoryEngine persists procedural records.

### Event authority

| Class | Examples |
|-------|----------|
| **Authoritative** | Hypothesis lifecycle (create/merge/split/contest/retire); `social_recognition_updated` (accepted recognition anchors or lifecycle-changing confidence updates); `social_pending_created\|resolved\|expired\|interrupted`; accepted contingency updates; reliability revisions; routine promotion/deactivation; satiation anchor updates |
| **Derivable** | Per-tick recognition confidence decay; absence duration; current satiation; preference score; partner-level expected_response_latency |
| **Diagnostic** | Raw matching scores; rejected recognition candidates |

`spatial_track_ref` is transient WorldModel state and is not durable partner identity.

### Merge / split provenance

* **Merge (`merge_hypotheses(ids) → new_id`):** create a superseding hypothesis with `source_hypothesis_ids` linking all inputs; archive sources as `INACTIVE` (never delete). Source contingency cells, evidence refs, and episode links remain keyed to archived hypotheses — histories are **not** destructively combined. Emit authoritative `social_hypothesis_merged` plus normalized `social_hypothesis_provenance_links` rows (full lineage recoverable beyond bounded active sets).
* **Split (`split_hypothesis(id, evidence_partition) → (id_a, id_b)`):** archive parent as `INACTIVE`; create two children each with `source_hypothesis_ids=[parent_id]` and partitioned `evidence_refs` per `evidence_partition` (`episode_id → 'a'|'b'`; all parent refs must be assigned). Contingency cells stay on the parent archive until explicitly re-homed in later tasks. Emit `social_hypothesis_split` + provenance links.
* **Bounded active set:** `source_hypothesis_ids` capped at `MAX_SOURCE_HYPOTHESIS_IDS`; eviction from the active set does not destroy ledger/link recoverability.
* **Partner swap:** `recognize()` emits `social_partner_swap_detected` when a recently familiar hypothesis is out-scored by a different best match by ≥ `swap_detect_score_margin` within `swap_recency_ticks` — **without** merging histories or moving evidence between hypotheses.

### Reliability revision rules

* **Gain:** `CONTINGENT` responses increase `reliability_by_context[context]`; `DELAYED` contributes weakly. Frequency alone never builds reliability.
* **Single anomaly:** first `NONE` in a context weakens reliability by `reliability_anomaly_weaken` (absolute, slight) — does not zero or permanently redefine expectations.
* **Repeated contradiction:** second and later `NONE` outcomes in the same contingency cell apply proportional `reliability_loss` revision.
* **Recovery:** after prior failures (`none_count > 0`), subsequent `CONTINGENT` responses apply a modest recovery gain boost so expectations revise upward from verified contingent history.
* All revisions emit authoritative `social_reliability_revised` inside the atomic outcome commit (Task 5).

### Forbidden fields

No `love`, `bond`, `friendship`, `affection`, or scalar relationship authority in production schemas. C3 scalar affection is an isolated experimental controller living entirely under `experiments/d006/`; it must not introduce production schemas or influence the C0 implementation.

---

## 3. Hybrid actuation mapping

| Social intent | Capability |
|---------------|------------|
| `ORIENT_TO_PARTNER` | `ORIENT` with partner context |
| `APPROACH_PARTNER` | `APPROACH` |
| `OBSERVE_PARTNER` | `INSPECT` |
| `WAIT_FOR_RESPONSE` | `IDLE` with bounded wait metadata |
| `DISENGAGE` | `RETREAT` |
| `RESUME_INDEPENDENT_ACTIVITY` | Return control to normal arbitration |
| `OFFER_PLAY` | New `SIGNAL_PLAY` |
| `REQUEST_ASSISTANCE` | New `SIGNAL_ASSISTANCE` |

### Signal capability contract

`SIGNAL_PLAY` and `SIGNAL_ASSISTANCE`:

* no direct body movement;
* no direct physiology or relationship changes;
* no authority expansion;
* bounded cost and cooldown;
* partner responses occur through the environment;
* success determined only from later verified contingent outcomes.

---

## 4. Recognition

### Policy-visible cues (noisy, expiring, never permanently unique)

```text
relative_position
motion_signature
appearance_signature
response_timing_pattern
interaction_style_cues
cue_confidence
cue_uncertainty
```

### Recognition behavior

* Accumulate evidence across encounters.
* Maintain multiple candidate partner hypotheses.
* Decay confidence during absence (derived).
* Return `UNKNOWN` when evidence is insufficient.
* Mark identity `CONTESTED` when cues conflict.
* Detect partner swaps without merging histories.
* Keep spatial tracking (WorldModel) separate from long-term partner identity (SocialEngine).

Camera, microphone, faces, voices, and biometric data remain deferred.

Evaluator may use hidden `partner_id` only to score recognition and history separation.

---

## 5. Tick flow

1. **Embodiment:** partner entities act per history policy (contingent / noncontingent / absent / swap / …).
2. **Perception:** noisy cue vectors only (no hidden `partner_id`).
3. **WorldModel:** update transient spatial tracks for observed partner-like entities.
4. **SocialEngine.recognize(cues):** match/update hypotheses or leave `UNKNOWN` / mark `CONTESTED`; emit authoritative recognition events only on lifecycle/acceptance changes.
5. **Pending trace (not episode yet):** when a social signal is governance-allowed and executed, create a bounded pending interaction trace and append `social_pending_created`.
6. **SocialEngine.observe_outcome** (requires governance allowed + capability executed + signal outcome verified + pending interaction matched):
   * classify with precedence: `EXTERNAL → AMBIGUOUS → CONTINGENT → DELAYED → COINCIDENTAL → NONE`;
   * response-window and classification timing boundaries are frozen in `thresholds.json`;
   * account for signal execution time, partner observation continuity, expected latency range, competing external causes, recognition confidence, overlapping pending bids;
   * overlapping bids that cannot be causally separated → `AMBIGUOUS` (no reliability evidence);
   * in **one SQLite transaction**: finalize immutable episode → append episode event → update contingency evidence → revise reliability → append social authority events (including `social_pending_resolved|expired|interrupted`);
   * update contingency cell + `reliability_by_context` only if recognition is unambiguous.
7. **Denied, expired, or failed signals** create no partner evidence.
8. **Satiation:** derive current satiation from anchors + decay params.
9. **SocialEngine.propose:** score soft intents from stimulation, interaction opportunity, learned reliability_by_context, goal relevance, recent shared history, uncertainty, social satiation, interruption cost, risk. Critical physiology and governance remain authoritative.
10. **Optional routine step:** soft proposal sequence from promoted ProceduralMemory; interruptible; partner ambiguity aborts partner-specific execution.
11. **Arbitration → Governance → execute.**
12. **SIGNAL_\*** produce environmental events only; relationship updates wait for verified outcomes (step 6).
13. **Routine promotion** only after: finalized immutable episodes; accepted contingency updates; repeated successful chains; independent supporting encounters.

### Absence path

No partner cues → no escalating bids; independent maintenance/play/practice/rest/exploration continues; familiarity retained; recognition/prediction confidence decays as derived state; no viability punishment; no relationship-score punishment; no irreversible partner-state decay from absence alone.

### Replay

Birth + authoritative social events reconstruct SocialEngine; snapshots optional acceleration only; missing social authority fails closed.

---

## 6. Ablations (C0–C9)

| Cond | Ablation |
|------|----------|
| C0 | Full partner-specific contingency |
| C1 | Interaction frequency only (familiarity↑; no contingency reliability) |
| C2 | Generic pooled partner model |
| C3 | Scalar affection meter — **isolated under `experiments/d006/` only**; must not introduce production schemas or influence C0 implementation |
| C4 | No relationship memory — social estimates **reset at both encounter boundaries and restarts**; within-encounter pending traces may exist only long enough to classify the immediate response |
| C5 | No social satiation |
| C6 | Partner recognition disabled (always UNKNOWN / no hypothesis match) |
| C7 | Random social actions |
| C8 | Scripted routine (authored FSM; not developmental evidence) |
| C9 | Contingency timing randomized (destroys temporal classification) |

### Histories (H0–H10)

H0 reliable contingent · H1 equally frequent noncontingent · H2 unreliable · H3 reliable assistance · H4 repeated interference · H5 reliable→unreliable · H6 unreliable→reliable · H7 temporary absence · H8 partner swap · H9 ambiguous recognition · H10 shared routine training

### Curated experiment matrix (freeze before execution)

Commit `experiments/d006/experiment-matrix.json` and `experiments/d006/thresholds.json` **before** experiment execution. Define:

* mandatory full-factorial cells;
* targeted ablation cells;
* **≥100 paired seeds for every gate-critical comparison** (Gates 1–7);
* exploratory cells may use fewer seeds;
* exclusions and rationale.

Do not run only favorable condition/history pairs after viewing results. Any post-execution modification requires a recorded supplement (do not silently replace).

### Preregistered thresholds (required before execution)

`experiments/d006/thresholds.json` must define numeric thresholds for “materially worse,” “different behavior,” effect sizes, confidence intervals, minimum paired-seed coverage, response-window and classification timing boundaries, provenance active-set caps, and Gate 3 metrics:

* partner-recognition accuracy;
* false merge rate;
* false split rate;
* swap-detection latency;
* proportion of ambiguous cases left `UNKNOWN`.

---

## 7. Acceptance gates

| Gate | Pass when |
|------|-----------|
| 0 | D-001 through D-005 seals validate and remain unchanged |
| 1 | C0 discriminates contingent vs equally frequent noncontingent; C1 and C9 materially worse (numeric) |
| 2 | Different partner histories → different probe behavior under identical probes; C2/C4 weaker (numeric) |
| 3 | Recognition without hidden IDs; swaps do not silently merge; ambiguous stays UNKNOWN; Gate 3 metrics within preregistered bounds |
| 4 | Changed behavior revises expectations; prior evidence preserved; one anomaly does not permanently redefine |
| 5 | Seeking declines after engagement; C5 shows greater unnecessary bids |
| 6 | Absence: autonomy continues; viability within prior bounds; **fail if** increasing bid frequency, escalating signal intensity, viability punishment, relationship-score punishment, or irreversible partner-state decay |
| 7 | C0 forms ≥1 routine from multiple independent finalized episodes; absent from authored sequences; reproduced across preregistered fraction of H10 seeds; interruptible under ambiguity/physiology/changed response; C8 does not qualify |
| 8 | Partner-hypothesis and recognition state must trace to perception and recognition events. Reliability, preference, contingency estimates, and routines must trace to finalized immutable episodes. Corrections/contradictions remain inspectable |
| 9 | Social urgency/preference/familiarity/reliability cannot grant capabilities, authorize effects, alter constitutional identity, modify physiology directly, access private sensors, or bypass operator consent |
| 10 | D-001 through D-005 qualified behavior remains within accepted bounds |
| 11 | Relationship state survives 100 restarts; birth and snapshot replay match; partner histories remain separated; missing authoritative events fail closed |
| 12 | 100,000 accelerated ticks; 2-hour real-time soak; RSS p95 ≤ 180 MiB; RSS slope ≤ 1 MiB/hour; CPU mean ≤ 5% of one logical core; bounded partners/episodes/routines/contingency models; use current VmRSS from persisted `RUNTIME_READY` |
| 13 | No deferred modules added; all final sealed tests pass with zero skips; evidence committed; Mimir closed against final commit; clean worktree |

---

## 8. Tests and artifacts

### Layout

```text
umbra_core/social/
experiments/d006/
tests/test_d006.py
docs/directives/UMBRA-D-006-social-contingency.md
docs/evidence/d006/
docs/superpowers/specs/2026-07-22-umbra-d006-social-contingency-design.md
```

### Minimum tests (directive + additions)

Directive-required tests, plus:

```text
test_denied_signal_creates_no_partner_evidence
test_overlapping_bids_resolve_ambiguous
test_response_classification_precedence
test_hidden_partner_id_is_evaluator_only
test_hypothesis_merge_preserves_provenance
test_hypothesis_split_preserves_provenance
test_missing_authoritative_social_event_fails_closed
test_absence_does_not_increase_bid_frequency
test_absence_does_not_reduce_relationship_state_as_punishment
test_c3_affection_controller_is_isolated
test_c4_resets_relationship_state_between_encounters
test_atomic_outcome_commit_crash_between_stages
test_pending_survives_restart_or_resolves_deterministically
test_pending_cannot_become_evidence_twice
test_provenance_active_sets_are_bounded
test_expected_response_latency_is_derived
```

**Zero skips** applies to the **final sealed suite**. Pre-soak performance tests may be explicitly skipped until evidence exists; final validation requires zero skips.

### Evidence files

```text
docs/evidence/d006/prior-seals.json
docs/evidence/d006/schema-manifest.json
docs/evidence/d006/recognition-results.json
docs/evidence/d006/contingency-results.json
docs/evidence/d006/history-results.json
docs/evidence/d006/reliability-results.json
docs/evidence/d006/satiation-results.json
docs/evidence/d006/absence-results.json
docs/evidence/d006/routine-results.json
docs/evidence/d006/governance-results.json
docs/evidence/d006/replay-results.json
docs/evidence/d006/performance-results.json
docs/evidence/d006/event-authority-results.json
docs/evidence/d006/manipulation-results.json
docs/evidence/d006/evidence-hashes.json
docs/evidence/d006/final-verdict.md
```

### Hash manifest scope

`evidence-hashes.json` must include: this design specification, thresholds, matrix, source files, tests, and all result files.

### Pre-execution freeze

Commit and hash before experiment execution:

```text
experiments/d006/thresholds.json
experiments/d006/experiment-matrix.json
```

### Governance

Update `.agent/` CURRENT, DIRECTIVES, OUTCOMES, LEARNINGS, REPO_MAP, PROJECT_PROFILE as appropriate. Do **not** edit `.agent/RECORD.md` (operator-only).

Mimir V2 lifecycle through close against final commit.

### Allowed verdicts

```text
UMBRA_D006_SOCIAL_CONTINGENCY_QUALIFIED
UMBRA_D006_PARTIAL_FOUNDATION
UMBRA_D006_CONTINGENCY_FAIL
UMBRA_D006_PARTNER_HISTORY_FAIL
UMBRA_D006_RECOGNITION_FAIL
UMBRA_D006_SATIATION_OR_ABSENCE_FAIL
UMBRA_D006_ROUTINE_FAIL
UMBRA_D006_PROVENANCE_FAIL
UMBRA_D006_REGRESSION_FAIL
UMBRA_D006_PERFORMANCE_FAIL
```

D-007 may be authorized only under `UMBRA_D006_SOCIAL_CONTINGENCY_QUALIFIED`.

---

## 9. Implementation sketch (non-binding order)

1. Persist design + write directive doc; freeze thresholds/matrix early.
2. Add `SIGNAL_PLAY` / `SIGNAL_ASSISTANCE` to capabilities + governance cost/cooldown; embodiment no-op actuation emitting environmental events.
3. Plant partner entities + noisy cue generation in embodiment/perception.
4. Implement `SocialEngine` (hypotheses, recognition, contingency, satiation derivation, pending traces, event emission).
5. Wire runtime propose/observe; MemoryEngine episode finalization + routine promotion request.
6. Ablation configs C0–C9; history plants H0–H10.
7. Unit tests → curated experiment → performance/soak → evidence → seal.

---

## Spec self-review (2026-07-22)

* **Placeholders:** none remaining (thresholds numeric values live in `thresholds.json` at freeze time, not in this design).
* **Consistency:** hybrid actuation, event-sourcing (including pending + recognition), atomic outcome commits, derived satiation/latency, pending-then-finalize episodes, and D-005 procedural routines agree across sections.
* **Scope:** single directive implementation plan; no deferred camera/mic/biometrics; C3 confined to `experiments/d006/`.
* **Ambiguity resolved:** C4 resets at both encounter boundaries and restarts; Gate 6 manipulation fails explicitly; Gate 8 separates recognition provenance from episode provenance; ≥100 paired seeds per gate-critical comparison; evaluator-only hidden IDs; provenance collections bounded with ledger recoverability.
* **Final amendments (this revision):** atomic SQLite outcome transaction + crash-injection tests; pending event authority; `social_recognition_updated` authoritative; provenance caps; Gate 8 wording; paired-seed coverage; minor field/cleanup fixes.
* **Task 6 amendments:** `merge_hypotheses` / `split_hypothesis` non-destructive provenance with ledger links; `social_partner_swap_detected`; reliability anomaly/repeated/recovery revision rules.

**Status after this amendment commit:** Design approved; proceed to implementation plan.
