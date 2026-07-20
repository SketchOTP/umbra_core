# MECHANISM_MATRIX

Every examined mechanism receives one of: ADOPT | ADAPT | REFERENCE | REJECT | UNRESOLVED.

| Mechanism | Classification | Evidence | Limitations | Proposed UMBRA boundary | Confidence |
|---|---|---|---|---|---|
| Vector-valued internal state (multi-need \(H\)) | **ADAPT** | formal phys; Yoshida interoception | Scale/choice of variables open | Physiology module owns \(H\); not a UI meter | high |
| Viable ranges (not only point setpoints) | **ADAPT** | formal viable intervals; satiation tests | Exact bounds need calibration | Prefer intervals for companion needs | high |
| Autonomous physiological drift | **ADAPT** | I9 / C6 ablation | Drift rates are design params | Deterministic authority; continues without user | high |
| Drive reduction reward \(D_t - D_{t+1}\) | **ADAPT** | R2 tests; Yoshida `homeostatic_shaped` | Scalarizes vector drive unless careful | Learning **signal** only — not sole will | high |
| Nonlinear / overshoot-sensitive drive | **ADAPT** | D3 overshoot reward negative | Function shape TBD | Prefer convex drive over linear-only | med |
| Need-dependent outcome valuation | **ADAPT** | deprivation + temp reversal tests | Must not become commanded emotion | Value depends on \(H\); no GO_HAPPY | high |
| Satiation (seeking declines after recovery) | **ADAPT** | I8 C4 vs C1 | Attention-seeking analogues need caps | Explicit satiation on social/interaction channels later | high |
| Motivational competition (relative deficits) | **ADAPT** | I1 vs I2 preference flip | Hard-coded priority fails as sole selector | Soft competition via drive, not frozen list | high |
| Anticipatory regulation | **ADAPT** | C4 vs C7 under delay | Formal uses forward model, not full CTCS learner | Predictor separate from physiology authority | med |
| Interoceptive access for policy | **ADAPT** | C5 ablation impairs | Over-exposure → exploit sensors | Policy may read \(H\); may not write \(H\) | high |
| Physiology / policy separation | **ADAPT** | no policy assign; intervene only in exp | Must enforce in future kernel API | Hard boundary in architecture | high |
| Hard-coded lowest-need controller (R4/C2) | **REJECT** | negative control | Useful as baseline only | Never production motivation | high |
| Fixed external reward as sole motive (R0/C1) | **REJECT** | compulsive consume under abundance | OK for toy games | Not companion will | high |
| One scalar “happiness” as sole state | **REJECT** | collapses competition/satiation semantics | — | Forbid as sole regulatory variable | high |
| One global reward as sole motivational authority | **REJECT** | flattens personality/expression risk | Drive reduction OK as **one** signal | Multiple authorities: phys, memory, relation | high |
| RL policy as complete creature brain | **REJECT** | scope + identity/online-train risks | Useful submodule | Policy ⊂ organism, not organism | high |
| Production dep on mujoco-py/PFRL stacks | **REJECT** | upstream blocked; author outdated warning | Research reference OK | Do not vendor as foundation | high |
| Unlimited online retraining | **REJECT** | identity drift risk | Offline / bounded updates later | No continuous unconstrained retrain | med |
| Death as only negative outcome | **REJECT** | R3 weaker than drive reduction | Critical bounds still useful | Graded drive, not binary death-only | high |
| Point setpoints for every psychological var | **REJECT** | over-constrains companion affect/relation | Physiological vars may use ideals | Prefer viable ranges for psych needs | med |
| Curiosity ↔ homeostasis interaction | **REFERENCE** | architectural only (P4) | Not independently proven here | Track later; bounded novelty C8 exploratory | low |
| Multi-agent homeostatic coupling | **REFERENCE** | deferred Track 6 | Not implemented | Relationship track candidate | n/a |
| Continuous-time HRRL full paper stack | **UNRESOLVED** | paper analogue only | No dedicated upstream run | Revisit if continuous-time needed | low |
| Embodied Yoshida MuJoCo agents (as runtime) | **REFERENCE** | static + equation smoke | Full env blocked | Reference for reward formulations | med |
| Direct policy mutation of physiology | **REJECT** | violates separation tests | — | Forbidden | high |
