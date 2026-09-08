# UMBRA-AS-014 result

Terminal verdict: `AS014_FRESH_R1_FAIL`.

Starting baseline: `a97171a2dab7c1750e2556727bce9e3648bb359a`. The frozen
implementation lock was `af89b5cfe16c304a74a60289bf8cd76fd6b81e26`; the
scientific lock SHA-256 was
`75a8b4a00193adbf073edc1b1ac188d3791f0754da2b4dd66893eaeea9825de1`.

The fresh population completed R0 `8/8` at `7200` ticks and the first R1 case
at `7200` ticks. Fresh R1/S16 seed `32550454` reached `NO_SAFE_ACTION` at tick
`346` and critical fatigue at tick `347`. The first failing route was the
`verified_outcome_branch_safety` gate. Its persistence checkpoint epoch was `0`
and hot tail was `1793`; checkpoint maintenance had not occurred and is not
causal to the failure. The frozen result stopped R1, R2/R3, lifecycle, 100k,
real-time soak, matched ablation, and CLOSE-03.

No repair, retry, reseed, or successor was started. Production changes were
frozen before scientific execution. The exact failure artifact SHA-256 is
`975f3e993c716e885fe79c6c5f7169f1ccef7ac9b88d12e63850e99c3e9a30c5`; the
failure-attribution artifact SHA-256 is
`fdc4366440f36eb4311b1dfa8c2620768b07a88309c156afea0a512f5bbf0863`.

The complete evidence manifest SHA-256 is
`bdb77f4d0adcc470249ea8048560841e3de7c4fc562592fcdba235fa5cac5813`.
The local/internal evidence root is
`/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-014-persistent-ledger-boundedness-completion-r1/`.
