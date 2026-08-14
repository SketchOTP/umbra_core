# Continuity Contract

The repository-defined model is one execution with two ordered segments:
`cc3-d009-c0-s10-seed7:pre` and `cc3-d009-c0-s10-seed7:post`. Both share one
definition fingerprint, seed, database, organism identity, and execution ID.

| Field | Classification | Basis |
|---|---|---|
| organism identity | MUST_MATCH_EXACTLY | `load_organism` verifies the stored identity |
| identity / birth commitment | MUST_MATCH_EXACTLY | `Store.load_identity` and `verify_identity` |
| event sequence and hash chain | MUST_CONTINUE_MONOTONICALLY | persistent ledger sequence/hash fields |
| last committed snapshot | EXPECTED_TO_RECONSTRUCT | latest verified snapshot is loaded |
| habitat state hash | MUST_MATCH_EXACTLY at boundary | C0 restores saved authoritative habitat |
| tick counter | MUST_CONTINUE_MONOTONICALLY | loaded organism resumes from snapshot state |
| RNG state | EXPECTED_TO_RECONSTRUCT | `load_organism` imports persisted RNG state |
| execution provenance | MUST_MATCH_EXACTLY | one execution ID and definition fingerprint |
| verified outcome history | MUST_CONTINUE_MONOTONICALLY | ledger/state history is not replaced |
| memory / world-model internals | DIAGNOSTIC_ONLY | enabled by D-009 but not separately qualified here |
| controlled interruption | NOT_EXERCISED | no process interruption injected |
| unexpected crash recovery | NOT_EXERCISED | no crash path claimed |

Expected changes are limited to post-restart tick, event sequence/hash, and
normal continued organism state evolution.
