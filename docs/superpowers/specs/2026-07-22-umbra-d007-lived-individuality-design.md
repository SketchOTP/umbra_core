# UMBRA-D-007 Design: Lived Individuality and History-Shaped Temperament

**Date:** 2026-07-22  
**Project directive:** UMBRA-D-007  
**Agent memory directive:** `D-20260722-umbra-d007-lived-individuality`  
**Starting commit:** `79924c7fde7224a8a8321035444e1e538044b6bb`  
**Prerequisite:** `UMBRA_D006_SOCIAL_CONTINGENCY_QUALIFIED` (`9dd2022`)  
**Mimir project:** `7777645d52a91b49`  
**Status:** Design frozen; proceed to implementation

## Purpose

Establish that matched UMBRA organisms develop **measurable, coherent, persistent individuality** from different causal life histories. Dispositions are slow contextual estimates — not personality labels, character classes, or scalar affection.

## Locked decisions

1. **Packaging:** `umbra_core/individuality/` — `IndividualityEngine` as a bounded integration layer over D-001..D-006.
2. **Ownership:** owns disposition estimates, confidence/uncertainty, provenance refs, bounded arbitration modifiers, internal fingerprint summaries for continuity checks, replay/snapshot of individuality anchors. Does **not** own identity, physiology, world truth, embodiment, capability grants, episodic/procedural authority, social-partner truth, or final execution.
3. **Update rule:** dispositions update only from finalized verified experience (episodes, outcomes, transitions, mastery, procedural success/fail, social contingency episodes, recovery/uncertainty histories). Never from proposed/denied actions, raw frequency alone, user/evaluator labels, or hidden history IDs.
4. **Scoring:** bounded modifier term in normal arbitration; never selects/executes/overrides critical physiology/governance/embodiment.
5. **Ablations C2/C3:** diagnostic controllers under `experiments/d007/` only — never production schemas.
6. **Fingerprints:** evaluator-only; never written into organism state or policy inputs.
7. **Gate experiments:** drive `IndividualityEngine` with synthetic verified evidence for statistical power (D-006 precedent), plus organism-path integration tests for governance/autonomy/embodiment continuity.

## Hard constraints

* No LLM controller; no authored personality in production state.
* No scalar `personality_*`, `bond_level`, `affection`, `character_class`, etc.
* Human-readable temperament labels only in evaluator reports after measurement.
* Random seed never stored as a personality variable.
* History labels never enter runtime individuality state.
* Avatar/UI/robot chassis IDs absent from individuality state.
* Critical physiology overrides individuality modifiers.
* Missing authoritative individuality events fail closed on replay.

## Scientific claims

**Authorized (bounded):** history-dependent lived individuality and experience-shaped behavioral temperament.

**Not authorized:** consciousness, sentience, emotion, human personality/attachment, biological life, unrestricted agency, complete companion.

---

## 1. Architecture

```text
Verified experience (D-001..D-006)
  └─ outcome_verified / episodes / mastery / contingency / recovery
        ▼
IndividualityEngine
  ├─ DispositionEstimate[dimension × context_scope]
  ├─ slow evidence-weighted updates (+ contradiction revision)
  ├─ bounded provenance refs (active set) + ledger recoverability
  └─ bounded proposal modifiers
        ▼
Arbitration (vector scores + individuality term + stochasticity)
        ▼
Governance → Embodiment
```

### Disposition dimensions (required)

```text
exploration_tendency
novelty_tolerance
persistence_after_failure
uncertainty_caution
stimulation_tolerance
recovery_pacing
activity_timing_preference
social_initiative_by_context
```

Each estimate:

```text
dimension, context_scope, value, confidence, uncertainty, plasticity,
support_count, contradiction_count, supporting_evidence_refs,
contradicting_evidence_refs, last_update_tick, source_systems
```

Values ∈ [-1, 1], birth = 0 (neutral). Modifier contribution clipped to `modifier_abs_max`.

### Context families (preregistered generalization)

| Family | Scopes | May generalize within |
|--------|--------|------------------------|
| explore | safe_explore, novelty_probe | yes (bounded) |
| persist | solvable_task, practice | yes (bounded) |
| hazard | uncertain_hazard, integrity_risk | yes (bounded) |
| stim | high_stim, inspect_activity | yes (bounded) |
| recover | post_stim_recovery, rest_pacing | yes (bounded) |
| timing | diurnal_phase, routine_window | yes (bounded) |
| social | play_context, assistance_context | yes (bounded) |

Cross-family generalization strength = 0. Cross-unsafe (explore→hazard) = 0.

### Event sourcing

Authoritative:

```text
individuality_disposition_created
individuality_disposition_updated
individuality_disposition_revised
individuality_disposition_deactivated
individuality_profile_migrated
```

Snapshots accelerate recovery only. Birth replay reconstructs from events. Missing events → fail closed.

---

## 2. Learning contract

* Evidence-weighted EMA; confidence-sensitive; plasticity decays with support.
* Single anomaly: confidence weaken only (`anomaly_confidence_delta`); no personality rewrite unless `severe_safety=True`.
* Sustained contradiction (≥ `revision_min_contradictions` with weight) revises value toward contradictory mean.
* Frequency alone may raise familiarity counters in memory/habit systems; cannot alone create preference/persistence/caution/initiative/novelty/stimulation dispositions.
* Preferences/habits remain in MemoryEngine/Development; individuality may summarize refs only.

---

## 3. Runtime integration

After base scoring, before noisy argmax:

```text
cand.scores["individuality"] = clip(Σ_dim w_dim * disposition_value * relevance, ±modifier_abs_max)
cand.total += individuality  # skipped if critical physiology recovery path
```

C10 records modifiers but does not add to `total`. C1 has no individuality engine. C8 resets dispositions on restart. C5 blocks episodic refs. C6 blocks procedural habit refs. C7 pools social partner contexts. C9 shuffles outcome evidence across matched organisms (experiment harness). C4 updates only from action-frequency proxies (diagnostic; must be weaker).

Explainability log (diagnostic): needs, predictions, memories, habits, partner history, individuality, uncertainty, stochastic draw, governance.

---

## 4. Histories H0–H12

Frozen in `experiments/d007/experiment-matrix.json`. Alter opportunities/verified consequences only — never `set cautious=true` style interventions.

| H | Experience |
|---|------------|
| H0 | Balanced neutral |
| H1 | Safe exploration → useful outcomes |
| H2 | Uncertain exploration → negative outcomes |
| H3 | Persistence on solvable challenges rewarded |
| H4 | Effort on impossible challenges unproductive |
| H5 | High-stimulation tolerable/rewarding |
| H6 | Overstimulation → withdrawal/recovery needed |
| H7 | Specialization family A |
| H8 | Specialization family B |
| H9 | Reliable social play/assistance |
| H10 | Unreliable/interfering social |
| H11 | Stable activity-time/routine |
| H12 | Reversal of previously learned consequences |

Habitat plants via `Embodiment.apply_individuality_history` + harness evidence schedules.

---

## 5. Ablations C0–C10

| C | Meaning |
|---|---------|
| C0 | Full individuality |
| C1 | No individuality layer |
| C2 | Fixed authored trait vector (experiments-only) |
| C3 | Random trait drift (experiments-only) |
| C4 | Action-frequency-only profile |
| C5 | No episodic evidence to individuality |
| C6 | No procedural habit refs |
| C7 | Pooled social partner history |
| C8 | Reset dispositions on restart |
| C9 | Shuffled outcome evidence (harness) |
| C10 | Modifiers recorded, do not influence arbitration |

---

## 6. Evaluation

* ≥100 paired seeds for gate-critical cells.
* Evaluator fingerprint from held-out `probe-suite.json`.
* Thresholds frozen in `thresholds.json` before formal execution.
* Metrics: within-individual stability, matched-history similarity, between-history separation, classification, re-ID across restart/replay/embodiment remap, ablation collapse, entropy bounds.

## 7. Performance

* ≥100,000 accelerated ticks; ≥2h RUNTIME_READY VmRSS soak.
* RSS p95 ≤ 180 MiB; slope ≤ 1 MiB/h; CPU mean ≤ 5% of one core.
* Bounds on disposition records, contexts, evidence refs, fingerprint windows, pending updates, snapshots, ledger policy.

## 8. Minimum tests

See directive §14 / `tests/test_d007.py` — zero skips at seal.
