# AS-014 external prior-art disposition

This review supplies architecture context only. It does not prove UMBRA-specific
semantics, and it introduces no dependency.

| Source / mechanism | What it establishes | UMBRA disposition | Cost / limitation |
| --- | --- | --- | --- |
| [Microsoft: Event Sourcing](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing) | Append-only event streams provide auditability; snapshots can reduce reconstruction work by replaying only the later stream. | **REFERENCE** for checkpoint-plus-tail recovery. | Snapshot evolution and recovery verification remain application responsibilities. |
| [Kurrent streams](https://docs.kurrent.io/server/v25.0/features/streams) | Stream retention uses age/count/truncation policies and physical scavenging; deleting a middle event is not a valid stream operation. | **REFERENCE** for prefix-only retention and bounded hot streams. | External event-store adoption is **REJECTED**: UMBRA needs its existing SQLite authority, schemas, and crash model. |
| [SQLite VACUUM](https://www.sqlite.org/lang_vacuum.html) | Deleted SQLite pages are not generally returned to the filesystem without explicit reclamation; `VACUUM` rebuilds, while `VACUUM INTO` produces a compact consistent output. | **REFERENCE** for physical reclamation after a logically valid checkpointed deletion. | Requires exclusive/controlled maintenance and sufficient temporary space; it cannot make an unsafe logical deletion safe. |
| [SQLite auto-vacuum](https://www.sqlite.org/pragma.html#pragma_auto_vacuum) | Auto-vacuum modes govern reclamation of freed pages. | **REFERENCE** only; no unconditional global pragma change. | Full auto-vacuum can fragment; enabling it post hoc requires `VACUUM`. |

## Selected architecture

**PATH B — bounded authoritative hot log** is selected. The retained AS-013
database attributes 794.2 MiB of its 807.5 MiB main file to `events`; therefore
diagnostic cleanup or SQLite page reclamation alone cannot provide a bounded
operational lifetime.

AS-014 will implement a compacted-prefix checkpoint, a bounded absolute-sequence
tail, protected current snapshot material, bounded promoted active provenance,
and explicit physical reclamation. Normal restart will validate the checkpoint
anchor plus tail. Full replay from birth will remain available only when a
verified cold archive covers the compacted prefix; otherwise it will fail
explicitly rather than fabricate a history.

## Rejected alternatives

* **Delete rows then VACUUM** — loses current attachment/provenance and breaks
  the existing genesis-chain invariant.
* **Compress an ever-growing hot ledger** — changes bytes per event, not the
  unbounded lifetime growth law.
* **Replace SQLite with an event-store product** — excessive scope and would
  replace already-qualified authority semantics rather than repair them.
* **Treat storage pressure as a behavioral signal** — forbidden infrastructure
  leakage into organism policy.
