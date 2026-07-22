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
- 2026-07-21 | D-002 | ru_maxrss full-window slope is allocator-warmup dominated; Gate9 RSS slope should use post-warmup plateau (here post-30min slope=0 while full-window maxrss looked like 3 MiB/h).
- 2026-07-21 | D-002 | Body-change evidence must ignore movement_slip and near-wall truncated moves; otherwise I0 false supersession explodes.
- 2026-07-21 | D-002 | Prediction improvement metrics must filter to locomotion errors and skip early warmup ticks.
- 2026-07-21 | D-002V | `ru_maxrss` is peak (VmHWM), not current RSS; Gate9 leak slope must use `/proc` VmRSS (or equivalent current RSS).
- 2026-07-21 | D-002V | Full-window current-VmRSS OLS can fail ≤1 MiB/h on allocator warmup (here ~2.26 MiB/h hour1, ~0.44 hour2, full-window 1.052) even without a continuing leak; do not post-hoc switch to post-warmup after seeing results.
- 2026-07-21 | D-002V | `prediction_error` / `self_attribution` may remain DIAGNOSTIC (sampled) when birth resimulation reconstructs body-model hash without those ledger rows; `body_schema_supersede` stays AUTHORITATIVE.
- 2026-07-21 | D-002P | Full-window VmRSS OLS is dominated by early SQLite/page residency + history population; late-window slope can be ~0 while full-window fails. Prefill+in-place reuse alone insufficient; fixed-size structural warm before RUNTIME_READY moves residency before the measurement boundary without an RSS-plateau delay.
- 2026-07-21 | D-002P | Replacing prefilled pad objects with newly allocated live entries after RUNTIME_READY recreates the early growth the prefill was meant to absorb — mutate slots in place instead.
- D-003: superseded transition models are removed from the active map but remain inspectable via the bounded supersessions ring; otherwise SUPERSEDED rows unbounded past max_models.
- D-003: planning must only override arbitration when energy urgency is high and a supporting observation is present; unrestricted ORIENT/plan prefixes thrash recovery.
- D-004: learning progress = recent_window_success − prior_window_success; raw prediction error / novelty are ablations not intrinsic value (arXiv:1301.4862 IMGEP).
- D-004: practice must not override recovery arbitration (energy urgency >0.45); otherwise LP looks worse than random because CHARGE recovery is displaced.
- D-004: Gate1 fair compare uses waste-adjusted learnable_gain/nonlearnable when distractors present — C0 zeros nonlearnable attention while C1 farms and wastes.
- D-004: full-vector viable_frac is misleading (fatigue=0 below viable_low); Gate7 uses energy-band recovery probe.
- D-005: when memory_enabled owns experiment `condition`, force self/world model configs to C0 — otherwise world-model ablations silently zero encoding under C2.
- D-005: memory_growth for forgetting gates should exclude compressed archives; compare active episodes+beliefs+procedural so C0 archival bounds storage vs C7.
- D-005: each distinct encoded episode_id is independent evidence; encoding fingerprints only satiate storage, not belief confirmation.
- 2026-07-22 | area:d006 | lesson:Store.atomic_social_outcome wraps stage writers in one BEGIN IMMEDIATE..COMMIT; apply in-memory model mutation only in on_commit (post-COMMIT) so crash_after_stage rollback leaves no partial durable OR in-memory state | evidence:umbra_core/persistence.py,tests/test_d006.py::test_atomic_outcome_commit_crash_between_stages
- 2026-07-22 | area:d006 | lesson:sqlite3 isolation_level=None (autocommit) needs explicit BEGIN IMMEDIATE; append_event hash-chains correctly inside the txn since reads see uncommitted rows on the same connection | evidence:umbra_core/persistence.py
- 2026-07-22 | area:d006 | lesson:no double-evidence = pending status gate (resolve once) + durable UNIQUE(hypothesis_id,context,signal,episode_id,relation) on social_evidence_links | evidence:tests/test_d006.py::test_pending_cannot_become_evidence_twice
- 2026-07-22 | area:d006 | lesson:classification precedence EXTERNAL>AMBIGUOUS>CONTINGENT[1,8]>DELAYED[9,24]>COINCIDENTAL>NONE(timeout 32); only CONTINGENT (weakly DELAYED) builds reliability_by_context; overlapping same-context+signal bids → AMBIGUOUS | evidence:experiments/d006/thresholds.json,umbra_core/social/engine.py
- 2026-07-22 | area:d006 | lesson:any capability added to embodiment.CAPABILITIES must also be added to BodySchema.bootstrap()'s caps tuple, or SelfModel.capability_status() defaults it "dormant" and Organism.tick_once()'s dormant-capability guard silently rewrites the candidate to IDLE before governance ever sees it — this defeated SocialEngine.propose()'s SIGNAL_PLAY/SIGNAL_ASSISTANCE candidates for any organism with the default self_model_enabled=True | evidence:umbra_core/self_model/engine.py,tests/test_d006.py::test_full_tick_recognizes_proposes_governs_and_opens_pending
- 2026-07-22 | area:d006 | lesson:routine_handles has no cleanup path when a hypothesis is retired/merged/split — _prune_hypotheses only bounded the active hypothesis count, so handles for retired hypothesis_ids stayed ACTIVE forever and grew unbounded across the full lifetime; fix is to interrupt_active_routine() on every evicted hypothesis, then FIFO-prune non-ACTIVE handles against a MAX_ROUTINE_HANDLES cap | evidence:umbra_core/social/engine.py::_prune_hypotheses,_prune_routine_handles,tests/test_d006.py::test_partner_and_routine_counts_are_bounded
- 2026-07-22 | area:d006 | lesson:birth-vs-birth resimulate() replay-equality checks must exclude fields sourced from Governance's proposal_id (plain uuid4, never seeded) even though the owning ids (hypothesis_id, pending_interaction_id) are already seeded via identity.deterministic_id — PendingInteraction.execution_id is the one non-deterministic field in SocialEngine's otherwise-deterministic state | evidence:umbra_core/social/engine.py::accepted_state,tests/test_d006.py::test_birth_and_snapshot_replay_match
