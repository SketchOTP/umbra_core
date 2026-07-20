# SELECTION_LEDGER.md

Filled during UMBRA-D-000. Do not invent classifications without reproduction/audit evidence.

Prior-art order: MicroPsi → homeostatic RL → Hexis → AEROS → AERA → PEPA → Soar/Hyperon (if needed). Chemistry/protocell: deferred, non-gating.

| Component | Classification | License | Evidence path | Notes |
|---|---|---|---|---|
| MicroPsi Dörner/Psi modulators | adapt | MIT | docs/prior-art/micropsi2/NOTES.md | INDEPENDENT_MECHANISM_REPRODUCTION (stdlib equations); not full MicroPsi2 runtime |
| MicroPsi Sensor/Actor + WorldAdapter | adapt | MIT | docs/prior-art/micropsi2/NOTES.md | Body/brain I/O split |
| MicroPsi Survivor need datasources | adapt | MIT | docs/prior-art/micropsi2/NOTES.md | energy/water/integrity decay |
| MicroPsi2 server/Theano/UI | reject | MIT | docs/prior-art/micropsi2/NOTES.md | Obsolete stack; not foundation |
| MicroPsi node-net as sole substrate | reference | MIT | docs/prior-art/micropsi2/NOTES.md | Theory useful; not required |
| HRRL vector internal state + viable ranges | adapt | paper CC-BY / formal | docs/prior-art/homeostatic-rl/MECHANISM_MATRIX.md | Track 2 formal gates pass |
| HRRL autonomous drift | adapt | formal | docs/prior-art/homeostatic-rl/ | Continues without user (I9) |
| HRRL drive-reduction learning signal | adapt | eLife + Yoshida shaped | docs/prior-art/homeostatic-rl/ | Signal only — not sole will |
| HRRL satiation + overshoot | adapt | formal | docs/prior-art/homeostatic-rl/ | Contain attention-loop analogues |
| HRRL need competition via relative drive | adapt | formal | docs/prior-art/homeostatic-rl/ | Reject frozen priority as sole selector |
| HRRL anticipatory forward model | adapt | formal proxy | docs/prior-art/homeostatic-rl/ | Not full CTCS learner |
| Physiology/policy separation | adapt | formal | docs/prior-art/homeostatic-rl/ | Policy reads H; never writes H |
| Hard-coded lowest-need controller | reject | formal C2/R4 | docs/prior-art/homeostatic-rl/ | Negative control only |
| Fixed external reward as sole motive | reject | formal C1 | docs/prior-art/homeostatic-rl/ | Compulsive consume under abundance |
| One scalar happiness / one global reward authority | reject | analysis | docs/prior-art/homeostatic-rl/COMPANION_RELEVANCE.md | Flattens organism |
| RL policy as complete brain | reject | scope | docs/prior-art/homeostatic-rl/ | Policy ⊂ organism |
| Yoshida mujoco-py/PFRL production dependency | reject | upstream blocked | docs/prior-art/homeostatic-rl/UPSTREAM_REPRODUCTION.md | Reference only |
| Curiosity↔homeostasis coupling | reference | P4 | docs/prior-art/homeostatic-rl/ | Not independently proven Track 2 |
| Multi-agent homeostatic coupling | reference | deferred | docs/prior-art/homeostatic-rl/SOURCES.md | Track 6 candidate |
| Hexis persistence/heartbeat/memory | TBD | MIT | | Track 3 |
| AEROS identity/governance | TBD | AGPL-3.0 / Apache-2.0 | | |
| AERA causal learning | TBD | modified BSD | | |
| PEPA public code | TBD | (verify) | | |
| OpenLife | reject | not released | | Conceptual only |
| Soar / OpenCog Hyperon | TBD | | | Only if gaps remain |
| Chemistry / protocell (D-000A) | reject (as gate) | n/a | PROJECT_GOAL optional section | Deferred optional research; do not execute D-000A |
