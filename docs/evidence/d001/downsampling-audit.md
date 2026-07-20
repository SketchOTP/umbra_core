# D-001 Event Downsampling Audit

**Directive:** UMBRA-D-001C  
**Code:** `umbra_core/events.py`, `umbra_core/runtime.py`  
**Date:** 2026-07-20

## Policy

| Class | Rule |
|---|---|
| **Authoritative** | Emitted on every occurrence. Never cadence-skipped. |
| **Diagnostic** | May be omitted or sampled. Replay must not depend on them. |

## Authoritative event types (never omitted)

| Type | Why authoritative |
|---|---|
| `birth` | Identity genesis |
| `physiology_drift` | Physiology state transition each tick |
| `proposal` | Governance admission trail |
| `denial` | Governance fail-closed audit |
| `outcome_verified` | Verified action effects / outcome verification |
| `restart_recovery` | Restart continuity |
| `lifecycle` / `embodiment_bind` | Reserved lifecycle (when used) |

## Omitted / non-persisted diagnostic types

| Type | Status | Rationale |
|---|---|---|
| `observation` | Not persisted | Sensor membrane is recomputed from embodiment + seeded RNG during live ticks; materialised perception state lives in snapshots |
| `arbitration_scores` | Not emitted | Diagnostic only; selection is recoverable from physiology + observations + seed |
| `metrics_sample` | Not emitted | Operational telemetry only |

## Cadence / retention (operational, not omission)

| Mechanism | Value | Notes |
|---|---|---|
| Snapshot interval | default 200 ticks (soak uses 7200) | Materialised authoritative projection |
| WAL checkpoint | every 2000 ticks | Truncate WAL; does not delete events |
| Coverage set bound | 500 cells | In-memory metric bound only |

## Replay dependency

1. **Birth / seed replay:** Deterministic re-simulation from seed + config. Does not require diagnostic events.
2. **Snapshot restore:** Loads materialised state (identity, physiology, body, arbitration, governance, RNG). Does not require omitted diagnostics.
3. **Event chain validation:** Hash + sequence over whatever was written. Authoritative types above are always present after D-001C retention fix.

## Historical note (soak run)

The in-progress 6h soak was started under the pre-D-001C runtime that downsampled `physiology_drift` (every 10 ticks) and admitted `proposal` events (every 5 ticks). On that soak DB:

- `outcome_verified`, `denial` (when denied), `birth` were still always written.
- Snapshots remain the restart authority for materialised state.
- Post-soak validation uses snapshot restart + hash/sequence validation of the soak ledger as written.
- Going forward (post-seal code), authoritative types are never downsampled.

## Verdict

**PASS** for D-001C policy: authoritative vs diagnostic is explicit; replay does not require omitted diagnostics; code retains authoritative events every occurrence.
