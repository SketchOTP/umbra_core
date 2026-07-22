# UMBRA-D-006 — Social Contingency and History-Dependent Relationships

**Status:** ACTIVE  
**Agent memory directive:** `D-20260722-umbra-d006-social-contingency`  
**Depends on:** `UMBRA_D005_MEMORY_CONSOLIDATION_QUALIFIED`  
**Authorizes D-007 only under:** `UMBRA_D006_SOCIAL_CONTINGENCY_QUALIFIED`  
**Starting commit:** `70dd08ee3d664b6eda1968ca7129a953622d45bc`  
**Mimir project:** `7777645d52a91b49`

## Design and preregistration

- **Design spec:** [`docs/superpowers/specs/2026-07-22-umbra-d006-social-contingency-design.md`](../superpowers/specs/2026-07-22-umbra-d006-social-contingency-design.md)
- **Frozen thresholds:** [`experiments/d006/thresholds.json`](../../experiments/d006/thresholds.json)
- **Frozen experiment matrix:** [`experiments/d006/experiment-matrix.json`](../../experiments/d006/experiment-matrix.json)

Thresholds and matrix are committed **before** experiment execution. Post-execution edits require a recorded supplement.

## Objective

Enable UMBRA to form **partner-specific expectations from contingent interaction and shared history** — not affection scores or interaction counts.

UMBRA must distinguish partners under uncertainty, learn responsiveness and reliability, prefer or avoid interaction from verified experience, develop bounded shared routines, satiate social interaction, adapt when partners change, and continue safely during absence.

## Implementation map

| Area | Location |
|------|----------|
| SocialEngine (recognition, contingency, satiation, pending) | `umbra_core/social/` |
| Signal capabilities (`SIGNAL_PLAY`, `SIGNAL_ASSISTANCE`) | `umbra_core/embodiment.py`, `umbra_core/governance.py` |
| Partner entities + noisy cues | `umbra_core/embodiment.py`, `umbra_core/perception.py` |
| Episode finalization + routine promotion | `umbra_core/memory/engine.py`, `umbra_core/runtime.py` |
| Authoritative social events | `umbra_core/events.py` |
| Atomic outcome transaction | `umbra_core/persistence.py` |
| Tests | `tests/test_d006.py` |
| Experiments | `experiments/d006/` |
| C3 affection controller (isolated) | `experiments/d006/affection_controller.py` |
| Evidence | `docs/evidence/d006/` |

## Hard constraints

- No LLM or language as central controller
- No emotion, attachment, or affection labels in production schemas
- No engagement-maximization objective; no guilt, jealousy, exclusivity, abandonment threats
- No direct command to bond, trust, fear, forgive, or miss someone
- Hidden `partner_id` is **evaluator-only** — never enters SocialEngine, MemoryEngine, arbitration, or routine formation
- Memory cannot grant authority; partner reliability cannot bypass governance
- Absence cannot cause death, irreversible damage, or relationship-score punishment
- C3 scalar affection lives only under `experiments/d006/` and must not influence C0 production paths

## Ablations and histories

**Conditions (C0–C9):** full contingency (C0), frequency-only (C1), pooled model (C2), isolated affection (C3), no relationship memory (C4), no satiation (C5), recognition disabled (C6), random actions (C7), scripted routine (C8), timing randomized (C9).

**Histories (H0–H10):** reliable contingent (H0), equally frequent noncontingent (H1), unreliable (H2), reliable assistance (H3), repeated interference (H4), reliable→unreliable (H5), unreliable→reliable (H6), temporary absence (H7), partner swap (H8), ambiguous recognition (H9), shared routine training (H10).

Gate-critical cells use **≥100 paired seeds** per `thresholds.json` / `experiment-matrix.json`.

## Acceptance gates (summary)

| Gate | Pass when |
|------|-----------|
| 0 | D-001 through D-005 seals validate unchanged |
| 1 | C0 discriminates contingent vs equally frequent noncontingent; C1 and C9 materially worse (numeric) |
| 2 | Different histories → different probe behavior; C2/C4 weaker (numeric) |
| 3 | Recognition without hidden IDs; swaps do not silently merge; ambiguous stays UNKNOWN |
| 4 | Changed behavior revises expectations; prior evidence preserved |
| 5 | Seeking declines after engagement; C5 shows greater unnecessary bids |
| 6 | Absence: autonomy continues; no escalation, viability punishment, or irreversible decay |
| 7 | C0 forms routines from independent episodes; C8 does not qualify |
| 8 | Hypotheses trace to perception/recognition; reliability/contingency/routines trace to finalized episodes |
| 9 | Social urgency cannot grant capabilities or bypass governance |
| 10 | D-001–D-005 qualified behavior within accepted bounds |
| 11 | Relationship state survives 100 restarts; birth/snapshot replay match; fail closed on missing events |
| 12 | 100k ticks; 2h soak; RSS p95 ≤ 180 MiB; slope ≤ 1 MiB/h; CPU mean ≤ 5% |
| 13 | Zero skips in final sealed suite; evidence committed; Mimir closed; clean worktree |

Full gate definitions and numeric thresholds: design spec §7 and `experiments/d006/thresholds.json`.

## Allowed verdicts

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
