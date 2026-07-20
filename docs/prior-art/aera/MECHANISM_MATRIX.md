# MECHANISM_MATRIX — AERA Track 5

Upstream skim `@77b57022` + independent contracts. Classifications target companion core reuse (clean-room).

| Mechanism | Claim (upstream) | Source | Seed vs learned | Class | Evidence | Limitation | UMBRA boundary |
|---|---|---|---|---|---|---|---|
| Timestamped facts/observations | Timed facts enter groups | `r_exec/factory.*`, `view.*` | Runtime inject / axioms | ADAPT | Independent obs stream | Not identity memory | Observation ≠ authority |
| Forward models (mdl) | LHS→RHS prediction | `mdl_controller.*` | Seed and/or TPX | ADAPT | C2 P0 pred↑; forward tests | Tabular structural only here | Models propose only |
| Inverse / abduction | Goals → LHS subgoals | `mdl_controller` abduce* | Drive seed + runtime | ADAPT | C2≫C3 goal success | Designer `m_drive` extrinsic | Needs endogenous drives |
| Confidence / strength | SR, inertia thresholds | `rate_model`, settings | Updated online | ADAPT | support/contradict ratio | Not homeostatic need | Confidence ≠ will |
| Contradiction / pred failure | PMonitor rates failures | `p_monitor.*` | Runtime | ADAPT | P3 recovery 1.0 vs C4 0.0 | Simple ratio heuristic | Must supersede obsolete |
| Model blacklist / invalidation | White/black ModelBase | `model_base.*` | Runtime | ADAPT | supersession tests | No developmental forgetting | Cap model count |
| Plan composition (imdl chains) | Nested goals + req mdls | seed + controllers | Seed or learned | ADAPT | C2≫C5 goals | Depth capped | Bound depth/nodes |
| Interruptible plans | Failed pred → revise | monitors | Runtime | ADAPT | interrupt test | Not full STHZ sim | Replan bounded |
| Dynamic priority / saliency | sln/act job queues | `group.*`, cores | Runtime | ADAPT | PriorityQueue + phys urgency | C6≈C2 on grab alone | Priority ≠ command |
| Resource limits | cores, thz, TPX buffers | `settings.h` | Config | ADAPT | max_models / depth caps | No OOM proof | Hard caps required |
| TPX model generation | CTPX/PTPX/GTPX | `pattern_extractor.*` | Learned | ADAPT | Independent observe() | No full TPX clone | No unrestricted codegen |
| Replicode language | Seed + reflective programs | `r_comp/*`, `*.replicode` | Designer | REJECT | License + complexity | — | Not UMBRA core lang |
| Unrestricted self-mod code | Generated executable ctrl | icpp / overlays | Mixed | REJECT | Policy + tests | — | No exec of generated code |
| Designer drives as autonomy | Periodic `m_drive` | `drives.replicode` | Designer | REJECT | as-is | — | Extrinsic pressure only |
| AERA runtime dependency | Full rMem product dep | whole tree | — | REJECT | CADIA + build | Upstream blocked | Reference only |
| Monolithic reasoning brain | AERA as entire creature | claims | — | REJECT | Scope | — | Mechanism ⊂ organism |
| Semantic/operational closure | Architecture claims | docs | — | REFERENCE | Unverified here | Upstream not run | Do not claim |
| Full scheduler / reflective exec | Rich job/sim semantics | cores, g_monitor | — | REFERENCE | Independent simplified | — | Adapt ideas only |

## Demo distinction

| File | Models | Goals | Learning |
|---|---|---|---|
| hello.world.1 | none | none | none |
| hand-grab-sphere | 9 seed mdls | designer drive | exact seed reasoning |
| hand-grab-sphere-learn | `m_drive` only | designer + babble cmds | TPX intended |

Independent reproduction implements abstract forward/inverse/confidence/revision/composition/interrupt/bounds — **not** a Replicode clone.
