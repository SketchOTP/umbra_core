# D-001 Architecture Audit

**Directive:** UMBRA-D-001  
**Architecture authority:** `docs/architecture/` (D-000S freeze)  
**Date:** 2026-07-20

## Module ownership check

| Module | Implemented | Write authority respected |
|---|---|---|
| Identity | `umbra_core/identity.py` | Yes — immutable birth; adaptive fields rejected |
| Physiology | `umbra_core/physiology.py` | Yes — policy/arbitration read-only; outcomes apply effects |
| Perception | `umbra_core/perception.py` | Yes — observations only; no world truth to policy (except C6 ablation) |
| Embodiment | `umbra_core/embodiment.py` | Yes — habitat/body world truth |
| Arbitration | `umbra_core/arbitration.py` | Yes — proposes only; vector scoring |
| Governance | `umbra_core/governance.py` | Yes — admit→verify chain; fail-closed |
| Persistence | `umbra_core/persistence.py` | Yes — SQLite WAL ledger + snapshots |
| Runtime | `umbra_core/runtime.py` | Yes — frozen loop order |

## Policy write prohibition

Arbitration and governance never call `Physiology.set_var` / `intervene`. Physiology updates only via `tick_drift` and `apply_outcome_effects` after verified outcomes.

## Scope exclusions verified

No modules for: advanced memory, causal planning, relationships, personality, LLM, reflection, UI, physical actuation, reproduction, evolution.

## Deviations from frozen architecture

1. **Event density:** Drift/proposal events are downsampled (every 10 / every 5 ticks) to keep RSS/disk bounded under 100k-tick runs. Outcome events remain per action. Hash chain and replay-from-seed remain authoritative for materialised state.
2. **Causal learning / memory formation stages** from full `ORGANISM_LOOP.md` are deferred (D-001 foundation excludes them). Loop runs drift→perceive→arbitrate→govern→execute→verify→physiology update→persist.

## Clean-room

No AGPL AEROS, Hexis product, or AERA Replicode code vendored. Stdlib + SQLite only.
