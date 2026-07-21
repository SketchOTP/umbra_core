# LEARNINGS.md

Append-only repo-specific lessons for UMBRA-CORE. Format:

```md
- YYYY-MM-DD | area:<module> | lesson:<specific repo fact under 25 words> | evidence:<path>
```

- 2026-07-20 | area:governance | lesson:PROJECT_GOAL is sole product source of truth; copied digital_cell/hermes agent files were reset for UMBRA-CORE | evidence:.agent/PROJECT_GOAL.md
- 2026-07-20 | area:mimir | lesson:mimir_project_register fails for this Linux checkout via Windows host path mapping; leave binding UNBOUND until fixed | evidence:.agent/PROJECT_PROFILE.md
- 2026-07-20 | area:program | lesson:UMBRA-D-000 blocks D-001; informed prior-art reuse required before organism kernel | evidence:docs/directives/UMBRA-D-000-prior-art-reproduction.md
- 2026-07-20 | area:prior-art | lesson:No OSS project combines homeostasis+identity+embodiment+non-LLM kernel; Hexis/AEROS are LLM shells | evidence:docs/directives/UMBRA-D-000-prior-art-reproduction.md
- 2026-07-20 | area:goal | lesson:Primary target is companion organism core; chemistry/protocell is optional non-gating research; D-000A rejected | evidence:.agent/PROJECT_GOAL.md
- 2026-07-20 | area:micropsi | lesson:Adapt Dörner modulators+WorldAdapter+Survivor needs; reject MicroPsi2 Theano/server as foundation | evidence:docs/prior-art/micropsi2/NOTES.md
- 2026-07-20 | area:mimir | lesson:Register via SSH remote+root_commit (client_attested) when host path mapping fails; project 7777645d52a91b49 | evidence:.agent/PROJECT_PROFILE.md
- 2026-07-20 | area:micropsi | lesson:reproduce_modulators.py is INDEPENDENT_MECHANISM_REPRODUCTION not full MicroPsi2 runtime execution | evidence:docs/prior-art/micropsi2/NOTES.md
- 2026-07-20 | area:hrrl | lesson:Adapt vector H+drift+drive-reduction signal+satiation; reject RL-as-brain and mujoco-py/PFRL foundation | evidence:docs/prior-art/homeostatic-rl/MECHANISM_MATRIX.md
- 2026-07-20 | area:hrrl | lesson:Yoshida homeostatic_shaped equals drive reduction; full trp_env needs mujoco_py (blocked here) | evidence:docs/prior-art/homeostatic-rl/UPSTREAM_REPRODUCTION.md
- 2026-07-20 Track3: Hexis continuity mechanisms (typed memory, provenance, transactional state, restartable workers) are ADAPT-worthy; LLM-heartbeat, Big-Five-as-individuality, Postgres-as-brain, action-energy-as-metabolism, and self-termination are REJECT for UMBRA companion core. Embedding outage blocks Hexis memory writes unless mocked.
- 2026-07-20 Track4: AEROS PersonaCore fields (risk_appetite, verbosity, etc.) hash into identity — do not import personality dials into UMBRA constitutional identity; keep constitutional vs adaptive split but redefine constitutional fields.
- 2026-07-20 Track4: aeros-core is AGPL-3.0-or-later by default; NOTICE lists Apache boundary surfaces — treat AGPL as reference-only; clean-room governance mechanisms for production; Apache reuse only after file-level confirm.
- 2026-07-20 Track4: Upstream policy evaluator defaults ALLOW on no-match — UMBRA should fail-closed for unknown capabilities while preauthorizing low-risk companion actions.
- 2026-07-20 Track5: AERA License.txt is HUMANOBS BSD with CADIA field-of-use → SOURCE_AVAILABLE_REFERENCE_ONLY; never vendor Replicode into product paths.
- 2026-07-20 Track5: Container CMake configures AERA (-m32) but compile fails in mem.tpl.cpp templates; record original failure before any rewrite.
- 2026-07-20 Track5: Independent inverse models strongly improve goal success vs no-inverse (C2 1.0 vs C3 0.0, 30 seeds); contradiction handling required for obsolete-model recovery (C4 fails).
- 2026-07-20 Track6: PEPA Sys3 goals/rewards are LLM-generated from authored Big Five text — useful loop structure survives without them; individuality requires lived history/memory, not personality prompts (evidence: c2_history_effect_play=0 vs C6 history_effect_play>0.04).
- 2026-07-20 Track6: anonymous.4open.science may serve SPA HTML 200 while `/api/repo/*` returns 401 not_connected — treat as UPSTREAM_BLOCKED, do not claim nav-module reproduction.
- 2026-07-20 Track6: bounded deterministic reflection (weight retune) can show measurable value vs no-reflection; LLM autobiographical reflection is not required for that gate.
- 2026-07-20 | area:architecture | lesson:D-000S freezes HYBRID_PRIMARY SQLite+vector physiology+constitutional identity+governed loop; Soar/Hyperon not required | evidence:docs/evidence/d000-synthesis/final-verdict.md
- 2026-07-20 | area:program | lesson:D-001 authorized only under UMBRA_D000S_FOUNDATION_ARCHITECTURE_QUALIFIED; foundation excludes LLM/UI/robotics/OEE | evidence:docs/directives/UMBRA-D-001-invariant-companion-core.md
- 2026-07-20 | area:d001 | lesson:Sticky serialized recovery focus + desperate locomotion costs needed for multi-deficit regulation; hide_physiology must disable reflexes for honest C3 ablation | evidence:docs/evidence/d001/physiology-results.json
- 2026-07-20 | area:d001 | lesson:Loading full event chain into Python for validate_chain inflates RSS; measure perf before full-chain load; downsample drift/proposal events | evidence:docs/evidence/d001/performance-results.json
- 2026-07-20 | area:d001c | lesson:CORRECTION — physiology_drift/proposal/denial/outcome_verified are AUTHORITATIVE and must emit every tick/decision; never downsample them for RSS/disk. Diagnostics only. | evidence:docs/evidence/d001/downsampling-audit.md
- 2026-07-20 | area:d001c | lesson:Run A (pre-fix) is valid Gate9 budget evidence under retention v0 only; full-window RSS slope ~1.33 MiB/h failed ≤1; cannot certify retention-v1 | evidence:docs/evidence/d001/soak-run-a-performance.json
- 2026-07-20 | area:d001c | lesson:Never average Run A with Run B or use Run A to offset Run B Gate9 failures; Run B alone qualifies D-001C; soak tests must bind Run B DB/closeout only | evidence:.agent/CURRENT.md
- 2026-07-21 | area:d001c | lesson:Retention-v1 every-tick authoritative events met Gate9 on Run B (RSS slope 0.557 MiB/h, DB ~70 MiB/6h); Run A v0 slope fail does not block QUALIFIED | evidence:docs/evidence/d001/soak-run-b-closeout.json
