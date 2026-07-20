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
| Hexis persistence/heartbeat/memory | adapt (partial) | MIT | docs/prior-art/hexis/ | Track 3 PARTIAL |
| AEROS identity/governance | adapt (partial) | AGPL-3.0 / Apache-2.0 | docs/prior-art/aeros/ | Track 4 PARTIAL; AGPL reference-only |
| AERA causal learning | adapt (partial) | HUMANOBS BSD+CADIA (reference-only) | docs/prior-art/aera/ | Track 5 PARTIAL; runtime reference-only |
| PEPA layered autonomy (Sys1/2/3 structure, arbitration, bounded reflection, embodiment filtering, unprompted persistence) | adapt (partial) | UNVERIFIED_NO_REACHABLE_REPO | docs/prior-art/pepa/ | Track 6 PARTIAL; clean-room only |
| PEPA Big Five / LLM goals-rewards / LLM reflection / OEE-over-fixed-skills / PEPA-as-brain | reject | n/a | docs/prior-art/pepa/ | Authored personality ≠ individuality |
| PEPA MCTS/BERT, quadruped nav, elevator/stairs, daily hierarchy | reference | unreachable code | docs/prior-art/pepa/ | Paper + blocked anonymous.4open |
| OpenLife | reject | not released | | Conceptual only |
| Soar / OpenCog Hyperon | TBD | | | Only if gaps remain after D-000 synthesis |
| Chemistry / protocell (D-000A) | reject (as gate) | n/a | PROJECT_GOAL optional section | Deferred optional research; do not execute D-000A |


## Track 3 — Hexis (persistence / memory / identity) — 2026-07-20

Verdict: `UMBRA_D000_TRACK3_PARTIAL_MECHANISM_QUALIFICATION`  
Pin: QuixiAI/Hexis `@50f5194da6b938e54ab87796ffc33d429b78bd89` (MIT, package 1.0.5)

| Mechanism | Class | Confidence | UMBRA boundary |
|---|---|---|---|
| Transactional durable cognitive state | ADAPT | 0.85 | Embedded ledger OK; not Postgres-required |
| Stateless restartable workers | ADAPT | 0.80 | Workers ≠ identity owner |
| Typed memory classes | ADAPT | 0.90 | Keep authority/physiology out of memory |
| Episodic provenance + belief revision | ADAPT | 0.88 | Inference ≠ observation |
| Procedural success/failure history | ADAPT | 0.80 | Embodiment-compatible policies |
| Working memory TTL/capacity | ADAPT | 0.85 | No automatic permanence |
| Correction/supersession | ADAPT | 0.88 | History inspectable |
| Strategic memory | REFERENCE | 0.75 | Cannot override authority |
| Heartbeat OODA scheduling | REFERENCE | 0.85 | Schedule ≠ organism motivation |
| PostgreSQL exclusive authority | REFERENCE | 0.80 | Optional scale tier |
| Apache AGE graph | REFERENCE | 0.70 | Optional index |
| Character cards / Big Five as individuality | REJECT | 0.92 | Configured presentation only |
| LLM conscious decision loop | REJECT | 0.95 | Language expresses, does not command |
| Database-is-the-brain literal | REJECT | 0.90 | Storage ≠ organism |
| Action energy as metabolism | REJECT | 0.90 | Computational budget only |
| Self-termination architecture | REJECT | 0.95 | Forbidden |
| Model-produced self-description as identity fact | REJECT | 0.90 | D4 non-authoritative |

Evidence: `docs/evidence/d000-track3/`, `docs/prior-art/hexis/`.

## Track 4 — AEROS (identity / capability / governance / embodiment) — 2026-07-20

Verdict: `UMBRA_D000_TRACK4_PARTIAL_MECHANISM_QUALIFICATION`  
Pins: s20sc/aeros-core `@3e46d82bf5cd829df8d00061b865b7eb709e278d` (AGPL-3.0-or-later, 0.15.0); historical s20sc/aeros `@f3a5ef0d976fadc78e3914b23af55ac532b7d2e5` (Apache-2.0)

| Mechanism | Class | Confidence | UMBRA boundary |
|---|---|---|---|
| Cognition/execution separation | ADAPT | 0.90 | Clean-room; no LLM required |
| Typed structured intents | ADAPT | 0.88 | Free text ≠ authority |
| Capability admission + contracts | ADAPT | 0.90 | Capability ≠ identity |
| Policy + runtime safety chain | ADAPT | 0.85 | Fail-closed unknown; preauthorize low-risk |
| Body-binding continuity | ADAPT | 0.85 | One primary embodiment default |
| Postcondition verification | ADAPT | 0.80 | No self-certify |
| Hash+sig audit w/ version binds | ADAPT | 0.88 | Clean-room ledger |
| Shadow/canary/rollback + signed lifecycle | ADAPT | 0.87 | Upgrade ≠ learning |
| Identity across body/model change | ADAPT | 0.90 | Constitutional fields only |
| Clone vs migration | ADAPT | 0.85 | Clone = new id |
| Learned ≠ authority | ADAPT | 0.92 | NONE may grant permissions |
| ECM packaging / marketplace / fleet / MCP / ROS / dreaming | REFERENCE | 0.80 | Not core companion |
| PersonaCore/Adaptive split | REFERENCE | 0.85 | Axis useful; traits not constitutional |
| LLM planner as cognition | REJECT | 0.95 | Language expresses only |
| Authored persona as identity | REJECT | 0.92 | Configured presentation |
| AGPL runtime product dependency | REJECT | 0.95 | Clean-room only |
| Upgrade as organism learning | REJECT | 0.90 | Distinct from development |
| Unrestricted operator override | REJECT | 0.90 | Bounded only |
| Self-reported success as proof | REJECT | 0.85 | Verify independently |

Evidence: `docs/evidence/d000-track4/`, `docs/prior-art/aeros/`.

## Track 5 — AERA (causal learning / planning) — 2026-07-20

Verdict: `UMBRA_D000_TRACK5_PARTIAL_MECHANISM_QUALIFICATION`  
Pin: IIIM-IS/AERA `@77b570226d12052828ff5b7ee0ca968bf1702221` (HUMANOBS BSD + CADIA Clause — SOURCE_AVAILABLE_REFERENCE_ONLY)

| Mechanism | Class | Confidence | UMBRA boundary |
|---|---|---|---|
| Learned forward models | ADAPT | 0.88 | Propose only |
| Inverse model goal reasoning | ADAPT | 0.90 | Needs endogenous goals |
| Confidence from evidence | ADAPT | 0.85 | ≠ will |
| Contradiction-driven revision | ADAPT | 0.90 | Supersede obsolete |
| Interruptible planning | ADAPT | 0.80 | Bounded replans |
| Bounded model composition | ADAPT | 0.85 | Hard depth caps |
| Dynamic priority scheduling | ADAPT | 0.70 | Priority ≠ command |
| Non-axiomatic / cumulative learning | ADAPT | 0.85 | Under Track3/4 memory rules |
| Replicode / full scheduler / closure claims | REFERENCE | 0.85 | Ideas only |
| Replicode as core; AERA runtime dep; generated code exec; designer drives-as-autonomy; monolithic brain; models grant authority | REJECT | 0.95 | Forbidden |

Evidence: `docs/evidence/d000-track5/`, `docs/prior-art/aera/`.

## Track 6 — PEPA (persistent autonomy) — 2026-07-20

Verdict: `UMBRA_D000_TRACK6_PARTIAL_MECHANISM_QUALIFICATION`  
Paper: arXiv:2603.00117**v3** | Upstream nav: anonymous.4open.science **BLOCKED** (HTTP/API 401)

| Mechanism | Class | Confidence | UMBRA boundary |
|---|---|---|---|
| Sys1/Sys2/Sys3 separation | ADAPT | 0.88 | Structure only; no LLM Sys3 |
| Internal↔external arbitration | ADAPT | 0.90 | Never auto-override safety |
| Bounded non-LLM reflection | ADAPT | 0.86 | Weight retune ≠ diary |
| Embodiment / charging filters | ADAPT | 0.90 | Body constrains goals |
| Skill execution ≠ goal gen | ADAPT | 0.85 | Closed skills ≠ OEE |
| Unprompted persistence | ADAPT | 0.92 | Active when unobserved |
| History individuality via memory | ADAPT | 0.90 | Not Big Five |
| MCTS / BERT / nav skills / daily hierarchy | REFERENCE | 0.65–0.75 | Unreachable / optional |
| Big Five individuality; LLM rewards/reflection; generated-goals-as-autonomy; OEE-over-fixed-skills; personality=aliveness; PEPA-as-brain | REJECT | 0.90–0.95 | Forbidden for core |

Evidence: `docs/evidence/d000-track6/`, `docs/prior-art/pepa/`.
