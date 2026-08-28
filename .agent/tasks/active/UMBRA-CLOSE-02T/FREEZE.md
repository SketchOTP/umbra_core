# CLOSE-02T freeze

Freeze commit: this file's commit is the immutable qualification-contract
freeze for UMBRA-CLOSE-02T.

Implementation source commit before freeze:
`d5db6e09003be3a72d012f32ced6f2b159fd7e87`

Qualification runner freeze commit:
`96f212bfbc720509fd9b69fe2c88e28a43d3046d`

The runner is a qualification-only wrapper around the existing production-
native lifecycle. It has its own CLOSE-02T identity and reads only the
pre-registered CLOSE-02T seed manifests; it does not alter `umbra_core`.

The frozen contract is the accepted CLOSE-02S interruptible-intent contract.
Its production translation and regulatory mapping are tracked under
`experiments/research/non-production/`, while the source fingerprint,
contract, regime, schedule, thresholds, development seeds, formal seeds,
execution manifest, and freeze hashes are stored under the canonical Atlas
evidence root:

`/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-close-02t-interruptible-intent-r1/`

All development and formal seed manifests were generated before any
organism outcome. Development seeds are formal-ineligible. No organism run,
retry, reseed, threshold change, effect change, or contract change is part of
this freeze.
