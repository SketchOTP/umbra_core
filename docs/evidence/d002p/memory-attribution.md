# D-002P Memory Attribution

**Directive:** UMBRA-D-002P  
**Parent result preserved:** `UMBRA_D002V_PERFORMANCE_FAIL` (full-window VmRSS OLS 1.052 MiB/h)  
**Starting tip:** `97e5df2175817b9122f5724aaedd2c320d12510c`

## Classification of D-002V growth

D-002V diagnostics showed hour0–1 ≈ 2.26 MiB/h and hour1–2 ≈ 0.44 MiB/h. Growth was dominated by **bounded startup population**, not an ongoing behavioral leak. Remaining avoidable sources were remediated before the RUNTIME_READY-anchored revalidation.

## Structure ledger

| Structure | Owner | Initial | Maximum | Growth rule | Retention | Authoritative? | Steady-state | Remediation |
|---|---|---|---|---|---|---|---|---|
| `SelfModel.predictions` | `self_model/engine.py` | 0 → maxlen pads at init | 256 | 1/tick on predict | ring overwrite | No (snapshot live-only) | 256 slots | `BoundedRing`; prefill pads before `RUNTIME_READY` |
| `SelfModel.errors` | `self_model/engine.py` | pads at init | 256 | 1/verified outcome | ring overwrite | No | 256 | same |
| `SelfModel.attributions` | `self_model/engine.py` | pads at init | 256 | 1/observe | ring overwrite | No | 256 | same |
| `SelfModel.change_evidence` | `self_model/engine.py` | pads at init | 64 | residual detectors | ring; clear on supersede | No (DERIVABLE) | ≤64 | same |
| `SelfModel.supersessions` | `self_model/engine.py` | 0 | 32 | on schema rewrite | ring | Yes (ledger + snapshot) | ≤32 | `BoundedRing` |
| `SelfModel.archive` | `self_model/engine.py` | 0 | 32 | on supersede/replace | ring | Snapshot | ≤32 | `BoundedRing` |
| `_obs_range_window` | `self_model/engine.py` | 0 | 40 | 1/tick note | ring | No | ≤40 | preallocated slots; not zero-filled |
| `metrics.prediction_errors` | `runtime.py` | — | — | **removed** | — | No | n/a | duplicate of `SelfModel.errors`; replaced by scalar `last_prediction_error` |
| `metrics.cells` / `visited_cells` | `runtime.py` / `arbitration.py` | 0 | 500 | exploration | trim to 400 when >500 | No | ≤500 | unchanged bound |
| Snapshots table | `persistence.py` | 1 | **2 retained** | every 200 ticks | prune oldest | Latest only for restart | 2 rows | `prune_snapshots(keep=2)`; ledger remains durable history |
| SQLite events | `persistence.py` | birth+ready | unbounded on disk | authoritative emits | WAL + checkpoint | Yes | disk growth expected | not counted as RSS leak; `wal_checkpoint(TRUNCATE)` every 500 ticks |
| SQLite page cache | `persistence.py` | ~4 MiB pragma | fixed | — | connection lifetime | No | ~4 MiB | unchanged |
| Perception observations | `perception.py` | 0 | O(features) | perceive/expire | by kind + TTL | No | small | unchanged |
| Proposal / delayed queues | `runtime.py` | None | 1 each | tick | cleared on complete | Snapshot | O(1) | unchanged |
| Logging / soak samples | harness | 0 | 720 | 10s | jsonl on disk | No | disk | not in process after flush |

## Window notes (pre-remediation D-002V)

| Window | Dominant effect |
|---|---|
| 0–10 min | Allocator + history list growth toward bounds; SQLite page residency |
| 10–30 min | Continuing fill of 256-history and coverage sets |
| 30–60 min | Near steady ring size; residual allocator noise |
| 60–120 min | Low residual slope (~0.44 MiB/h in D-002V hour2) |

## Post-remediation expectation

After `initialize_bounded_collections()` at `RUNTIME_READY`, prediction/error/attribution rings are at capacity. Measurement window should therefore exclude startup population. Snapshot prune removes unbounded snapshot-table growth. Duplicate metrics list removed.

No unexplained growth owners remain in the in-process sensorimotor path.
