## UMBRA-AS-003P-R6B operational acquisition boundary — 2026-09-02

- A verified route learner can correctly bind and close a zero-movement terminal sample, but Q1 requires a continuous `APPROACH ... APPROACH -> terminal` episode. An ordinary emitted unrelated action must invalidate the active episode; this prevents false success but means the assay must acquire the complete route episode prospectively.
- The one-shot nominal assay did not meet Q1 and cannot be retried. Treat the result as a terminal acquisition/implementation failure, not as a production semantic rejection or as permission to make route evidence a behavioral reader.
- The focused protected suite had one inherited AS-003N firewall nonpass already present at the exact R6B baseline; R6B added no hypothetical import.

## UMBRA-AS-003P-R5A retained-root protocol facts — 2026-09-02

- `meta.latest_snapshot` is raw TEXT and must not be JSON-decoded; `meta.ledger_tip` remains JSON.
- The authoritative R5 root RNG digest hashes compact canonical JSON without a trailing newline. R5A's first verifier used the evidence-file newline convention and produced a verifier-only mismatch; the retained state and all archival file bytes were unchanged, and the correction is preserved append-only.

## AS-003N — conservative hypothetical composition

- A future-only evidence substrate can be implemented without new authority when it accepts only explicit immutable owner snapshots/tokens. Categorical feasibility must require supported finite timing, relevant state fields, route/opportunity persistence, and effect envelopes; probabilistic or unknown prerequisites stay `UNKNOWN`.
- Coupled physiological effects remain sound only as complete correlated branches. With current two-effect branch maximum and AS-003M's one-action-plus-four-service-witness constitutional limit, the exact predeclared ceiling is `2^5 = 32`; overflow must return `UNKNOWN`, never prune, sample, score, or combine independent per-field extrema.
- A deterministic dependency fingerprint is an invalidation contract, not a live cache authority: the caller supplies canonical dependency tokens, and any material token change invalidates the hypothetical state.

## 2026-08-30 — AS-003B prospective-evidence boundary

- Lost aggregate test observations must remain non-interpretable across successor generations; a fresh qualification may use only prospectively frozen evidence with durable per-test capture.
- `NOT_APPLICABLE` is not equivalent to absent shared evidence: dominance may skip a channel only if both candidates mark it not applicable; a one-sided case must block elimination just like UNKNOWN.

## 2026-08-30 — AS-003D investigation boundary

- A full-frontier observation is not one causal category: retained evidence must distinguish missing support, one-sided semantic applicability, and well-supported cross-proposition conflict before changing an action-selection architecture.

## 2026-08-31 — AS-003J owner ontology and calibration boundary

- A system can causally alter behavior without being a peer motivational owner; motivation, opportunity, association, capability, memory context, procedural habit, continuity, and hard authority require separate lifecycle/authority evidence.
- Shared owner labels such as viable/ideal/critical establish common qualitative regulatory anchors, not a continuous common control scale. Existing numeric urgency must be treated as local until its cross-drive semantics are independently established.
- Reducing the owner set does not solve habit/commitment arbitration; do not disguise a controller conflict as motivation or a salience bid.

## 2026-08-30 — AS-003D saturation attribution

- A partial order that requires joint support and no-worse status for every proposition applicable to either candidate can preserve epistemic caution yet be structurally unable to exert ordinary selection pressure when genuine organism interests conflict.
- In AS-003C frozen evidence, candidate-local stochasticity was residual in name but de facto ordinary authority: it resolved all 2,647 qualifying decisions and no distributed relation changed the full-pool stochastic winner.
- `@dataclass(frozen=True)` is insufficient for a pure consequence view when it exposes nested dict/list values; recursively freeze view payloads and thaw only trace copies.
- A frozen replay command must terminate the generation on its first nonpass even if the failed assertion appears to be a retained/legacy authority expectation; no causal attribution or repair is valid unless the governing protocol separately authorized it before freeze.

## 2026-08-30 — AS-003A retained-evidence boundary

- A recorded pytest aggregate cannot support individual failure attribution. Preserve command, node ID, assertion, output, and baseline differential as first-class durable evidence; otherwise a no-rerun attribution directive must terminate `EVIDENCE_INSUFFICIENT`.

## 2026-08-29 — Candidate-stable stochastic composition

- Candidate-level stochastic competition must bind noise to persisted organism seed, authoritative active tick, a versioned namespace, and source-neutral behavioral identity; shared sequential per-pool draws are a causal composition confound.
- Exact seeded trajectory assertions may change under an explicitly versioned stochastic substrate even when deterministic scoring and authority are unchanged; regression classification requires matched-baseline reproduction.

## 2026-08-28 — CLOSE-02T-ATTRIB start

The CLOSE-02T aggregate known-R1 artifact records the terminal envelope and
action totals but not the per-tick preventive-regulation, candidate eligibility,
authority, or selection lineage needed to attribute the tick-490/491 failure.
Do not infer preventive opportunity realization or safe-window loss from that
aggregate alone.
# LEARNINGS.md

- 2026-08-31 | area:AS-003G simultaneous context control | lesson: persistent categorical engagement prevents stateless re-election but cannot establish initial election or non-starvation for an incumbent and continuing rival. Event-keyed stochastic ordering is scale-free only as residual ordering of a genuinely unordered finite set; stochastic switching across time necessarily introduces hazard/dynamics semantics and must be calibrated rather than borrowing candidate-level CLOSE-02Z sigma. Activation age and time since service are shared clocks, not demonstrated shared motivational entitlement. | evidence: AS003G_CONTROL_SEMANTICS_LOCK.json, AS003G_STARVATION_PROOFS.json, AS003G_STOCHASTIC_AUTHORITY_ANALYSIS.json

Append-only repo-specific lessons for UMBRA-CORE. Format:

```md
- YYYY-MM-DD | area:<module> | lesson:<specific repo fact under 25 words> | evidence:<path>
```

- 2026-09-02 | area:AS-003P-R5A modal evidence | lesson:observer-safe modal profiles were identical across 57 exposed conflicts, so evidence strength alone supplied no action relation | evidence:AS003PR5A_AS003L_BLOCKER_RESULT.json

- 2026-09-01 | area:AS-003P-R5 protocol | lesson:synthetic SQLite preflight must verify real Store metadata encodings; latest_snapshot is raw TEXT, not JSON | evidence:AS003PR5_ROOT_PROTOCOL_FAILURE.json

- 2026-07-20 | area:governance | lesson:PROJECT_GOAL is sole product source of truth; copied digital_cell/hermes agent files were reset for UMBRA-CORE | evidence:.agent/PROJECT_GOAL.md
- 2026-07-20 | area:mimir | lesson:mimir_project_register fails for this Linux checkout via Windows host path mapping; leave binding UNBOUND until fixed | evidence:.agent/PROJECT_PROFILE.md
- 2026-07-20 | area:program | lesson:UMBRA-D-000 blocks D-001; informed prior-art reuse required before organism kernel | evidence:docs/directives/UMBRA-D-000-prior-art-reproduction.md
- 2026-07-20 | area:prior-art | lesson:No OSS project combines homeostasis+identity+embodiment+non-LLM kernel; Hexis/AEROS are LLM shells | evidence:docs/directives/UMBRA-D-000-prior-art-reproduction.md
- 2026-07-20 | area:goal | lesson:Primary target is companion organism core; chemistry/protocell is optional non-gating research; D-000A rejected | evidence:.agent/PROJECT_GOAL.md
- 2026-07-26 | area:governance | lesson:Active UMBRA authority must retain D-009 (`af35371`) as the qualified baseline and D-010 as `UMBRA_D010_PERFORMANCE_FAIL`; Digital Cell/protocell work is external, not optional UMBRA work | evidence:docs/governance/UMBRA-G-001-reconciliation.json
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
- 2026-07-22 | area:umbra_core/physiology,social | lesson:With social_enabled=True, stimulation dips critical (~tick44-45) identically for H0 and H7 — pre-existing arbitration quirk, not caused by absence handling | evidence:tests/test_d006.py::test_absence_does_not_damage_viability
- 2026-07-22 | area:tests/test_d006.py | lesson:_build_reliability() defaults contingent=3 even when only none= is passed; pass contingent=0 explicitly for a pure-NONE/unreliable history | evidence:tests/test_d006.py::test_different_histories_change_behavior
- 2026-07-22 | area:experiments/d006 | lesson:D-006 recognition/contingency gates must be exercised by driving SocialEngine directly with synthetic controlled cues (like the sealed unit suite), not raw PerceptionMembrane output — embodiment PartnerTrueCues.for_history salt (~0.17, ambiguous 0.01) is below sensor noise, so perceived cues collapse distinct partners; paired seeds vary only the partner-response RNG (should_respond/delay), so recognition discriminators (swap/ambiguity) are deterministic and report ~0 variance | evidence:experiments/d006/run_experiment.py::recognition_trial, umbra_core/embodiment.py::PartnerTrueCues.for_history
- 2026-07-22 | area:experiments/d006 | lesson:Gate 2 (history separation) needs a two-partner reliability-separation probe, not single-partner reliability: single partner reliability is identical for C0/C2/C4 at H0, but C0 keeps a contingent vs noncontingent partner separate (~0.6), C2 pooled collapses to one hypothesis (0.0), C4 no-memory cannot accumulate across encounters (~0.2) | evidence:experiments/d006/run_experiment.py::_two_partner_separation
- 2026-07-22 | area:experiments/d006 | lesson:Gate 6 viability across seeds must compare survival-critical excursions (energy/integrity/fatigue) only; the benign stimulation band jitters its critical-timing cross-seed under H7 vs H0 because absence changes non-social behavior, so exact critical-trace equality (the unit test proxy) holds only for specific seeds | evidence:experiments/d006/run_experiment.py::_viability_ok
- 2026-07-22 | area:experiments/d006 | lesson:deterministic pending/episode ids (identity.deterministic_id(seed,counter)) collide across two fresh SocialEngine+Store on the same seed/agent — episode_key social|{pending_id} then hits social_evidence_links UNIQUE; give auxiliary probes their own agent_id + fresh Store, and unlink resimulate/replay db files (they carry a birth event) before reuse | evidence:experiments/d006/run_experiment.py::_two_partner_separation,_replay_determinism
- 2026-07-22 | area:experiments/d006,umbra_core/embodiment,perception | lesson:Task 12 review (D-20260722-1522-d006-task12-review) sharpens the L63 lesson into a calibration defect, not just a test-methodology choice — the salt/noise gap is severe enough that even NOISE-FREE true cues fail: match_score(A,B)=0.90 for salt=0.17 exceeds recognition_match_threshold=0.55 (thresholds.json), so distinct partners collapse into one hypothesis (0 swaps) through the real perception pipeline. This means Gate 3 (recognition/swap/ambiguity) and Gate 2 (two-partner separation) are validated only at the SocialEngine-unit level; the embodiment-level behavior these gates are meant to certify is not demonstrated and, per live tick_once probe, currently fails. Fix requires recalibrating PartnerTrueCues salt / PerceptionMembrane noise sigma / recognition_match_threshold relative to each other, or explicitly downgrading Gate 2/3 in the sealed verdict — do not let Task 13 inherit an unqualified PASS | evidence:.superpowers/sdd/task-12-review.md, umbra_core/embodiment.py:53, umbra_core/perception.py:156, experiments/d006/thresholds.json:27
- 2026-07-22 | area:experiments/d006/run_seal | lesson:prior-seal validation must tolerate two committed evidence-hashes formats — flat {repo-relative-path:sha} (d001/d003/d004/d005) AND nested {"hashes":{bare-name:sha},"directive","verdict",...} (d002p); iterate only string values whose key startswith("docs/") and skip missing files (matches tests/test_d006.py::test_prior_seals_validate), else metadata keys force prior_seals_valid=False and a false non-QUALIFIED verdict | evidence:experiments/d006/run_seal.py::validate_prior_seals,docs/evidence/d002p/evidence-hashes.json
- 2026-07-22 | area:experiments/d006/run_performance | lesson:D-006 Gate 12 (social+memory+world, social_history H0) passes comfortably — 100k accelerated rss_p95~39MiB restart_continuity True; 2h RUNTIME_READY VmRSS soak rss_p95=40.5MiB slope=0.224MiB/h cpu=0.0035frac bounded, well under frozen 180/1.0/0.05 | evidence:docs/evidence/d006/performance-results.json
- 2026-07-22 | area:ops/soak | lesson:nohup-backgrounded soaks in this env can be reaped ~minutes in; run long soaks as a shell-tool-tracked background job (survives + emits completion notification) rather than nohup&; confirm the python child is alive and RUNTIME_READY anchor is post-warm | evidence:.soak/d006_soak, terminal 640482
- 2026-07-22 | area:umbra_core/embodiment,perception | lesson:L67 Critical resolved (D-20260722-1532-d006-task12-critical-fix) WITHOUT touching the frozen recognition_match_threshold(0.55). Two levers together made the real path robust where either alone was not: (a) PartnerTrueCues.for_history now uses an antipodal per-index identity basis over the 9 direct cue dims (motion/appearance/interaction; timing excluded — it is /32-rescaled and shared), giving noise-free inter-partner cue distance ~0.69; (b) PerceptionMembrane identity-signature noise floor 0.14 < spatial-position noise 0.33. Separation alone (big amplitude, old noise) still false-split single partners and let ambiguous H9 split (~5/10 seeds) because the noise floor caused own-match dips below threshold; reducing identity noise fixed own-match stability. Ambiguous H9 keeps a tiny (0.02) amplitude so partners genuinely collapse. Verified end-to-end (embodiment→perception→recognize→tick_once): H8 2 distinct hypotheses + swap, H9 stays single, 20/20 seeds | evidence:umbra_core/embodiment.py::PartnerTrueCues.for_history/_identity_offsets, umbra_core/perception.py::_noisy_partner_cue, tests/test_d006.py::test_organism_h8_distinct_partners_do_not_silently_merge, experiments/d006/run_experiment.py::_organism_recognition
- D-007: embedding individuality `event_log` in snapshots caused Gate13 RSS slope fail (~10 MiB/h); ledger-authoritative + empty snapshot event_log restored slope ~0.22 MiB/h (2026-07-23 soak evidence).
- D-007: real-time soak must sleep to `hz` (tight-loop soak invalidates cpu_mean_frac); match D-006 run_performance cadence.
- 2026-07-23 | area:d008/design | lesson:D-008 expression is a side-car derive-after-commit loop: governance→EmbodimentAdapter→Embodiment; PresentationState+FrameRing are non-authoritative; core/experiments never import ui/; C10 is a performance baseline (expression disabled), not a Gate1–10 scientific ablation; Tkinter formal soak requires real Canvas/event loop or fail-closed virtual display | evidence:docs/superpowers/specs/2026-07-23-umbra-d008-coherent-digital-embodiment-design.md

- 2026-07-24 | area:experiments/d008/run_performance | lesson:S3 adaptive soak early-window VmRSS rise matches D-007 first-45min (theil~1.4) and decelerates; pairwise-slope 2.5/97.5 percentiles are not a formal Theil-Sen CI and stay pathologically wide on stepwise RSS — only treat CI-straddle as ambiguous when the point estimate is near the limit (>0.6*limit). Extension gate must allow a partial final step up to max_measurement_seconds (measured+step>max blocked P0 at ~2700s). Bin raw 5s samples to 30s medians before Theil-Sen/segments. | evidence:docs/evidence/d008/performance-core.json,docs/evidence/d008/soak-P0.jsonl,docs/evidence/d007/soak-2h.jsonl


- D-009 Gate 8 revision_adaptation requires full preregistered S16 tick budget (1800); D009_TICK_CAP=240 yields honest FAIL (~0.08); full budget saturates to 1.0 — do not qualify under tick cap.
- D-009 seal suite must run under experiments/d009/with_tk_display.sh or D-008 Tkinter tests skip (zero-skip seal fails).

- D-010 Decision A: TemporalEngine is sole durable temporal authority. Runtime supplies trusted monotonic observations and orchestration order but cannot independently advance organism age. Age advances only on committed ticks; downtime reconciliation enters TemporalEngine; subsystems get immutable TemporalState views.

- D-010 Decision C (refined): hybrid recurrence evidence. Temporal anchors and finalized organism-observable evidence establish and promote hypotheses. Allowlisted authoritative events may seed CANDIDATE and support causal reconciliation only — cannot independently create predictive confidence. Freeze allowlist before formal experiments; policy gets expectations only.

- D-010 Decision D (Q3-C): bounded temporal score modifiers plus narrow governed WAIT. TemporalEngine exposes expectations only; Arbitration proposes WAIT during open confident windows; governance/physiology/interruption/expiration retain control; no ANTICIPATE capability; no indefinite escalation.

- D-010 Decision E (Q4-A): extend MemoryEngine procedural routines with optional temporal_binding. TemporalEngine expectations-only; Memory owns lifecycle; eligibility≠mandatory; every step re-enters arbitration/governance; no TemporalEngine launch path.

- D-010 Decision F (Q5-A refined): TemporalEngine-authoritative analytic downtime reconciliation. TemporalEngine emits DowntimeReconciliationPlan; Runtime validates; shared persistence applies allowlisted pure ElapsedTimeContracts atomically. No tick replay or fabricated experience; TemporalEngine never mutates other subsystems; organism_age may advance across trusted downtime, organism_active_ticks must not.

- D-010 Decision G (Q6-A): robust parametric recurrence estimator (organism age ticks; median/MAD or frozen robust equiv; one dominant period per hypothesis; S9 = separate recurrence IDs; no histogram/multimodal in D-010).

- D-010 Approach 1 approved: own-and-delegate umbra_core/temporal/ (Approaches 2–3 rejected).

- D-010 design §1 approved with 7 revisions: atomic TemporalAdvancePlan in tick txn; TickTemporalContext; state_version+canonical hash; no pending_waits in TemporalState; TrustedSample session-scoped monotonic; frozen age/active semantics; full production runtime.tick classification before formal runs.

- D-010 design §2 approved with 7 revisions: occurrence_id vs evidence_identity; deterministic recurrence_key; phase_anchor fitting; ObservationWindowEvidence for misses; TemporalObservationPlan atomic intake; ACTIVE→WAIT/UNCERTAIN→smaller modifier only; durable dedup compaction (no recount).

- D-010 design §3 approved with 8 revisions: WAIT only inside open window; durable WaitExecution; O-lane success only; durable WaitSuppression; fallback_bias not script; relative temporal_binding; interrupt≠miss; modifier caps + absence isolation from physiology/relationships.

- D-010 design §4 approved with 8 revisions: downtime_interval_id idempotency; tight TRUSTED_SHORT; conservative age_advance=0 + new session anchor; versioned ElapsedTimeContractRegistry; required vs optional contracts; Expectation/WaitRecoveryDeltas; replay recorded deltas not wall recalc; failure codes + bounds.

- D-010 design §5 approved with 8 revisions: TemporalAdvanceRecord in committed-tick event; D-009→D-010 epoch init age=0; standardized temporal envelopes; separate runtime caps vs ledger; formal-execution-manifest; harness-only controls; corrected Stage A/B freeze; P0/P1/P2 comparability.

- D-010 design: eight final amendments (replay-complete advance record; TemporalTransactionEnvelope; fitted next_index prediction; IN_TICK/POST_HOC observation; formal-execution-contract vs evidence manifest; TimeAnchor trust provenance; formal/dev seed split; test-manifest.json).

- D-010 Task 4 recurrence: `occurrence_by_id` stores lane per occurrence; period/jitter/phase_anchor/last_observed_tick derive from O-lane ticks only; A-lane seed upgraded by later O-lane envelope on same `occurrence_id` promotes `o_lane_occurrence_count` once (decrements `a_lane_seed_count`).

- D-010 Task 7 re-promote: `promote_environmental_routine` / `promote_social_routine` must call `_merge_temporal_binding_on_repromote` on existing skills — attach fresh binding or refresh params while preserving `strength`, `disabled`, and `last_bound_expectation_version`.

- D-010 Task 8 commit: `commit_downtime_reconciliation` must verify `verify_plan_canonical_hash(plan)` and match `_in_flight_reconciliation.canonical_plan_hash` before apply; tampered plan body fields fail closed with `RECONCILIATION_PAYLOAD_MISMATCH`.
- 2026-07-24 | D-010-R1 | TemporalEngine._committed_advance_ids must stay O(1) (latest id only); unbounded per-tick UUID retention caused Gate 13 RSS staircase (~1.5 MiB/h temporal vs ~0.1 without). apply_advance_plan already rejects last_advance_id reuse. Evidence: accelerated 7200-tick A/B + tracemalloc engine.py:221.
- 2026-07-25 | D-010-R1: S3 Gate 13 P0 slope is stochastic near the 1.0 MiB/h limit — identical P0 code (expression disabled, adaptive trim unreachable) measured 0.597 PASS then 1.199 FAIL across two full 3600s runs. Single-run P0 pass/fail near the limit is not reproducible evidence; growth is glibc RssAnon residency, not Python-heap. Evidence: docs/evidence/d010/rss-diagnosis/diagnostic-campaign-20260725.md
- 2026-07-25 | D-010-R1: adaptive expression trim (malloc_trim gated on >=0.4 MiB RSS growth, 50-tick cadence) resolved the P2 blocker 1.19 -> 0.635 MiB/h without sustained_segment_growth; fixed-cadence trim had reintroduced the sawtooth failure. Evidence: diagnostic-P2-20260725.json
- 2026-07-26 | D-011 evidence: `canon_json` returns bytes in this repository; bounded derived-payload validation must measure its byte length directly. The membrane snapshot is the existing durable restart seam for bounded external observations.
- 2026-07-27 | D-011C evidence: a hash chain alone cannot detect deletion of its final event; a separately persisted chain-tip anchor makes post-snapshot acceptance omission fail closed.
- 2026-07-27 | D-012 supervision qualification requires the organism runtime and writable SQLite owner to be a spawned OS worker, with PID plus process-start identity, generation-bound IPC, explicit dead-owner reclaim, and checkpoint copies only after worker quiescence and ownership release. In-process reconstruction is not process-continuity evidence.
- 2026-07-27 | D-012B formal C0 autonomy under the frozen D-012 configuration drives energy below its 0.05 critical bound in about 100 active seconds (tick 191 cleanup snapshot: energy 0.0015) before the five-minute partner opportunity. Longer campaigns are scientifically invalid until a separately authorized directive explains this configuration-level physiological failure without erasing the failed P0.
- 2026-07-27 | D-012B1: critical energy recovery stopped approach at perceived distance `<=2.2`, while `CHARGE` executes only at actual resource distance `<=feature.radius+0.3` (1.5 in S2). At actual 1.5259 it repeated seven admitted `not_at_resource` failures; aligning the transition to 1.5 produced a successful next-tick charge and energy 0.4285 at tick 191. Evidence: `docs/evidence/d012/p0-root-cause-verdict.md`.
- 2026-07-27 | D-012B2: aligning the CHARGE selection/execution boundary was necessary but insufficient under the exact formal lifecycle. The single S1 rerun produced 148 recovery-urgency ticks (122 MOVE, 20 REST, 6 APPROACH, 0 CHARGE) and crossed energy below 0.05 at tick 181. A bounded diagnostic with a reachable resource does not establish formal-schedule viability. Evidence: `docs/evidence/d012/p0b2-verdict.md`.
- 2026-08-18 | D-013AH: a recovery-preservation helper must remain proposal-only at the commit boundary. Validate its proposal before replacing an already-safe action; otherwise an unsafe heuristic can manufacture `no_safe_action` while the frozen current-rule safe set is nonempty. Evidence: `docs/evidence/d013ah-recovery-parity/`.
- 2026-08-18 | D-013AI: one-successor existence is a screening signal, not proof of an avoidable policy dead end. Require a policy-visible alternative plus bounded replay showing recovery or material avoidance; most post-AH SAFE2 alternatives merely reached the same boundary, while only energy-scale I7 produced meaningful recovery. Evidence: `docs/evidence/d013ai-successor-causality/`.
- 2026-08-18 | D-013AJ: local empty-safe-set evidence does not establish global environment impossibility. Reconstruct the qualified start and demonstrate existential and reachable-branch witnesses before attributing failure to the habitat; frozen S2 survives the full 7,200-tick P0 maximum, 14 prior environment labels become earlier trajectory-loss cases, and default-13035 retains a verified CHARGE continuation at its no-safe state. Evidence: `docs/evidence/d013aj-habitat-viability/`.

## 2026-08-18 — D-013AK authority reachability
- A conservative outcome envelope must remain conservative over outcomes that are actually reachable at final authority; unconditional generic failure branches can themselves create false denials.
- REST and CHARGE executability is deterministic at the body/habitat boundary. Sharing a pure preflight with execution prevents arbitration-time reachability from drifting away from authoritative execution semantics.
- Authority may narrow admissible outcome branches without becoming organism policy. In the tick-266 proof, observations, candidate order, and scores remained byte-for-byte equivalent while only safety admissibility changed.
- Closing a local false-empty safe set does not establish integrated viability. The fresh campaign retained later genuine trajectory losses in 8 default seeds and all 6 stress controls.
- Runtime-tick inventory remains a known D-010 defect. D-013AK introduced no new direct tick inventory sites and preserved the inherited 27-entry failure footprint.

## 2026-08-18 — D-013AL trajectory horizon
- Immediate admissibility can be correct while policy still exits the viable trajectory set. The first distinguishable consequences in the fresh cases occur 6–109 ticks later, so a one-step or fixed four-step model cannot represent the relevant recovery-route loss.
- Hidden habitat truth is valid for offline causal proof but must not enter organism policy. The runtime representation, if separately authorized, must remain derived from policy-provenanced perception, memory, physiology, and body state.
- A preserving candidate at one state is not itself an architecture prescription. The evidence supports a compact recoverability representation; it does not justify a tree search, MPC layer, generic shield, or arbitrary larger horizon.
- Delayed commitments form a distinct causal family and should not be silently folded into fresh-action selection. Their redesign remains separately gated.

## 2026-08-18 — D-013AM recoverability representation
- A learned expectation is not a safety support bound. SelfModel's expected motion, latency, cost, and reliability can describe likely body behavior, but they cannot conservatively certify that a recovery route remains reachable.
- Keep epistemic failure explicit. When verified progress or duration support is absent, a recoverability view must return `UNKNOWN_CAPABILITY_SUPPORT`, not silently convert confidence, probability, or observed extrema into authority.
- The cross-component skeleton is small and useful, but it is not yet architecture-ready: physiology slack, WorldModel opportunity support, and authority effects cannot project movement routes without a body-owned support primitive.
- The narrow ownership decision is `EXTEND_SELF_MODEL`. Only after that primitive is separately earned from verified consequences should a derived cross-component view be retried in shadow mode.

## 2026-08-18 — D-013AN verified capability support
- Finite empirical extrema are useful evidence only when their semantics remain explicit. `VERIFIED_OBSERVED_SUPPORT` must never be silently promoted to `HARD_CONTRACT`, and UNKNOWN is a valid result.
- Body capability progress should be signed along the applied intended direction; Euclidean displacement would incorrectly count sideways slip as recovery-route progress.
- Completion evidence belongs to organism lifecycle time: committed decision-tick lag, including delayed actuation, not wall-clock duration or expected latency.
- Bounded provenance must also be replay-stable. Random outcome UUIDs made independently reconstructed SelfModel hashes diverge; deterministic references to authoritative `outcome_verified` ledger sequence preserve both traceability and birth replay.
- Empirical support is body-schema-specific. Incompatible supersession must reset the active envelope to UNKNOWN rather than transferring experience across bodies.
- A shadow evaluator can distinguish observed motion from hard-contract stationary retention without claiming future safety. Directional comparisons between two movement actions remain UNKNOWN until route-relative semantics are separately authorized.

## 2026-08-19 — D-013AO recoverability view
- A compact recovery-route signal can generalize without becoming policy: the derived view distinguished supported destroying-versus-preserving actions while remaining byte-for-byte neutral to authoritative trajectories and RNG.
- Body-relative opportunity geometry must retain the schema under which it was observed. Relabeling remembered support with a replacement body schema silently converts stale coordinates into false current evidence.
- Fixed-size means bounded structure and bounded external text. Provenance arrays, provenance strings, semantic labels, and candidate labels all require explicit caps or normalization.
- Held-out accounting must separate qualifying action exits from no-boundary and unresolved replays. Only captured, causally supported cases may earn the gate; unresolved cases remain visible but contribute no positive evidence.
- Qualification caches are scientific inputs. Reuse is safe only when the frozen manifest, imported implementation tree, source harnesses, and complete prior-evidence input tree all match their recorded fingerprints.
- Verified observed support justifies at most a separately tested soft policy bias. It does not justify hard admissibility or a formal claim about future action outcomes.

---

## L-AUTHORITY-3-0-001 — Lossless migration of heterogeneous governance history
- Date: 2026-08-19T08:10:00-04:00
- Evidence source: AUTHORITY-3.0-MIGRATION-001; canonical Authority 3.0 package; governance validators.
- Confidence: VERIFIED

### Learning
Authority 3.0 does not require rewriting legacy UMBRA ledgers into synthetic uniform history. Preserve append-only ledgers as authored, archive exact replaced mutable snapshots and reusable rules, and use `INDEX.md` plus a concise current kernel to route future selective retrieval.

### Why it matters
This keeps negative results, old directives, scientific provenance, and operator history intact while eliminating parallel active routers and reducing mandatory context.

### Recheck trigger
Recheck if the canonical Authority package changes schema or if a future validator cannot distinguish active 3.0 policy from archived provenance.

---

## 2026-08-19 — D-013AP selection-path gap
- Evidence: `/mnt/storage1tb/project-archives/UMBRA-CORE/live-evidence/d013ap-soft-bias-r1/SELECTION_PATH_AUDIT.json`
- Confidence: VERIFIED

### Learning
Recoverability-informed option preservation cannot qualify an AP-admissible supported action-caused exit when the exit is selected by a direct critical-recovery constructor before ordinary candidate scoring. UNKNOWN-semantic exhausted rows remain neutral. Empty captured score maps are corroborating evidence that the ordinary score hook was not the causal selection path.

### Boundary
Do not broaden a negative-only soft bias into critical recovery reflexes under D-013AP. A selection-path correction requires a separate Architect decision.

## 2026-08-19 — D-013AQ critical-recovery choice-set boundary

- Evidence: `/mnt/storage1tb/project-archives/UMBRA-CORE/live-evidence/d013aq-critical-recovery-choice-set-r1`
- Confidence: VERIFIED

### Learning

An offline recoverability-preserving candidate is not automatically a same-focus policy alternative. In the three AP exits, `IDLE` was safe and authority-executable but did not repair the active fatigue need. The existing same-target approach candidate is exposed only through the immediate-safety fallback, while the direct critical branch constructs its action before ordinary scoring and hysteresis. The energy-specific preservation hook must not be generalized to fatigue, integrity, or stimulation without a separately proven choice set.

### Boundary

Do not apply the AP negative-only bias to direct critical-recovery construction. No evaluator counterfactual or D-013AR integration is justified by AQ. Return the finding to Architect.

## D-013AR - ordinary vector path insufficient
- The production predicate conflates active recovery need with actual criticality for direct-mode entry.
- Across all three target cases, actual-critical-only ordinary arbitration selected authority-invalid REST/CHARGE choices and failed earlier than production.
- No direct-mode gate correction is recommended from AR alone; return to Architect without production or formal work.


## 2026-08-19 - D-013AT priority handoff
- Existing energy precedence already preempts a sticky non-energy recovery focus once energy is in the recovery pool. The three tested target states were lower-priority fatigue APPROACH states immediately before that existing boundary.
- A one-tick IDLE counterfactual improved reserve by 0.0035 and reduced route cost by 0.006 in each target, but the route remained feasible and the later no-safe-action event was unchanged in all three cases. One body-intervention case reached energy activation/focus/recovery one tick later under IDLE, but both paths still reached the same later no-safe-action event.
- No policy-visible same-focus preserving alternative, one-step safety gap, repeated preemption starvation, or tunable deferral horizon was demonstrated. Retain the current recovery handoff and return to Architect.


## UMBRA-D-013AU — 2026-08-19

- Authorization: non-formal evaluator/diagnostic-only; exact baseline 2be4f5146144b033431b1e41cbaf4c09ea937322.
- Scope: recover and replay only the three already accepted AL/AO preserving witnesses.
- Stop: D013AU_PRESERVING_WITNESS_NOT_REPRODUCIBLE.
- Reason: accepted evidence preserved first IDLE alternatives and aggregate 7200-tick viability summaries, but no ordered witness actions, per-tick parameters, or verified outcomes.
- Boundary: no witness synthesis, prefix release, re-entry claim, production change, formal tag, or formal P0.
- Evidence: /mnt/storage1tb/project-archives/UMBRA-CORE/live-evidence/d013au-preserving-continuation-r1/, 14 hashed files.


## 2026-08-19 — D-013AV causal requalification
- Evidence: `/mnt/storage1tb/project-archives/UMBRA-CORE/live-evidence/d013av-causal-requalification-r1`
- AL/AO shadow recoverability distinctions do not by themselves establish an executable rescue policy or a causal production action-selection lever.
- Across three exact target reproductions, existing policy-visible one-action substitutions yielded only delay-only outcomes; no common substantive rescue mechanism met the two-target generality gate.
- Preserve AO as representation-only unless a future authorized study demonstrates a source-existing, authority-valid, one-decision, long-run causal rescue.

## 2026-08-20 — D-013AW closed-loop recovery-cycle diagnosis
- A recurring source-derived fatigue/MOVE/APPROACH/CHARGE sequence across three failing targets is not sufficient causal evidence when a viable matched default-family control shares the same motif and an adverse cycle.
- Closed-loop cycle accounting must distinguish recurrent pattern from failure-discriminating mechanism; all target cycles showed fatigue accumulation and integrity decline, but the control comparison did not isolate them as the cause of terminal failure.
- Retain AO as a shadow recoverability representation only. Do not promote this motif into a policy correction, planner, or formal-readiness claim.

## 2026-08-20 — D-013AXR execution-stop forensics
- An incomplete bounded search is not a scientific failure or pass. Without a durable logical branch ledger, aggregate summary, and continuation records, it cannot support any rescue or no-rescue conclusion.
- Parent-memory aggregation with uncaught future propagation is not durable scientific orchestration. Branch IDs must be manifest-keyed and completion records must be atomic and independently auditable.
- Outcome-dependent frontier scheduling and state-hash deduplication make lossless resume unsafe unless the exact completed and remaining sets are persisted.
- A clean rerun can preserve the same scientific protocol only as a separately authorized execution with a distinct ID after minimum harness reliability work; the failed attempt remains permanent evidence.

## 2026-08-20 — D-013AXH durable bounded-search harness

- A bounded scientific search needs durable logical branch identity and atomic completion records; execution IDs, PIDs, temporary paths, timestamps, and completion order must not affect scientific identity or aggregate results.
- Restart safety requires persisted execution, frontier, confirmation, and deduplication state. Rebuildable summaries must refuse completeness when any branch, parent, or confirmation remains pending, running, failed, or unexpanded.
- Duplicate results must be fail-closed: identical canonical results are idempotent, while conflicting results raise `NONDETERMINISTIC_DUPLICATE_RESULT`.
- Synthetic harness qualification is evidence about orchestration reliability only. It cannot convert the incomplete AX attempt into a scientific result or authorize an AX rerun.
- The AX protocol fingerprint remained unchanged and AX scientific branch execution count was zero; any clean rerun remains separately authorized work.


## 2026-08-24 — D-014E2 critical-recovery causal reconciliation

- Evidence: RPI5 canonical share at \\RPI5\RPI5SharedDrive\100_ACTIVE\Projects\UMBRA-CORE\evidence\live-evidence\d014e2-critical-recovery-r1
- Confidence: VERIFIED BOUNDED FAILURE

### Learning

Exact reproduction of D-014E1 R1 seed 57531938 localized a combined legacy critical-recovery defect: dynamic rest-opportunity invalidation exposed fixed-focus fatigue recovery; the direct fatigue fallback emitted MOVE search actions without reserve/horizon/progress metadata and bypassed ordinary candidate generation.

Three preregistered shadows tested reserve metadata, the existing urgent candidate slate, and complete verified effect-vector regulatory scoring. None produced a substantive 7,200-tick rescue, so no production correction is justified from D-014E2.

### Boundary

Do not treat the causal localization as a qualified remedy. Do not promote the shadow candidate slate or effect-vector scoring into production, and do not reopen D-013/AX or launch formal D-014 without a new Architect directive.


## D-014H2 evidence and storage learning (2026-08-24T17:00:00Z)

A production-native trace can remain behavior-neutral when it is default-disabled, side-effect-free, RNG/timing neutral, and sink-failure fail-closed. H1 translation must be kept separate from organism outcomes: all translated rows may be evaluator-selected while the current organism still fails the known R1 viability trajectory. Finalized traces and translations belong on `\\atlas\\ATLAS\\100_ACTIVE\\Projects\\UMBRA-CORE`; active SQLite/WAL/AF_UNIX scratch remains direct-attached only.
## 2026-08-24 — D-014H3 R2 runner authority

- Embodiment.set_occlusion is correctly rejected after an authoritative
  HabitatEngine is attached; runner scenario mutations must use the
  authoritative engine API.
- The existing D-014 S10 runner plants partner:d014 only in the legacy
  embodiment habitat before attaching an engine. The authoritative S10 engine
  state contains no social object and projects zero partners.
- A missing authoritative target cannot be repaired by bypassing the engine or
  inventing a social object without changing frozen scenario semantics.
- Therefore H3 must stop at D014H3_R2_RUNNER_UNRESOLVED until a separately
  authorized runner/scenario correction proves an unchanged authoritative R2
  state. No H3 selector or organism outcome may be inferred from this stop.

## 2026-08-26 — D-014H3A social/habitat authority investigation

- HabitatEngine can represent a SOCIAL_ENTITY and canonical habitat events can create/replay an authoritative spatial object.
- The current ImmutablePartnerView contains only hidden_partner_id, x, and y; it does not carry the authoritative object's occluded state or the legacy partner's cue/response semantics.
- PerceptionMembrane._perceive_partners consumes a legacy PartnerEntity with is_visible(), true_cues, and response_policy. No complete authority-consistent binding from the current social spatial projection to that partner semantic object was found during initial inspection.
- Do not fabricate partner cues, response policy, or occlusion behavior in a runner. If no existing bridge is proven, H3A must stop as a core social/habitat bridge gap.

## 2026-08-26 — D-014H3A terminal social/habitat bridge gap

- HabitatEngine spatial authority and legacy PartnerEntity cue/response semantics are not currently behaviorally composable. The spatial projection omits occlusion and the legacy perception path cannot consume ImmutablePartnerView.
- A runner-only repair would either bypass HabitatEngine, create a second writer, fabricate cue/policy truth, or silently change the historical R2 semantics. All are prohibited.
- H3 selector science must remain paused until a separately authorized core social/habitat integration change establishes the missing binding and its restart/replay semantics.

## D-014H3B active investigation — 2026-08-26

H3A's missing bridge is now the active architecture target. The investigation
must keep HabitatEngine as the sole owner of social spatial/existence/occlusion
facts, route hidden environment social truth only through trusted perception,
and keep SocialEngine limited to anonymous cue-derived PartnerHypothesis state.
No implementation choice is justified until current cue, response, occlusion,

## D-014H3B terminal learning — 2026-08-26

A HabitatEngine SOCIAL_ENTITY needs an environment-side cue/policy profile
persisted with authoritative state; a read-only projection alone cannot supply
legacy PartnerEntity semantics. The safe seam is a trusted sensing adapter that
preserves anonymous noisy cues and never exports entity_ref. Canonical creation
and visibility events plus state hashes provide deterministic restart/replay.


## 2026-08-26 — D-014H3C known-R1 gate

The accepted H3B social/habitat bridge did not introduce a focused or full-suite
regression. Fixed R0 completed 8/8 x 7,200, while known R1 seed 57531938
reproduced the accepted tick-372 fatigue failure after verified MOVE. A fresh
selector shadow contract can be replayable and policy-visible without
production authority, but it cannot be promoted or evaluated as an integrated
rescue when the known-R1 predecessor gate fails. Evidence: /srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/d014h3c-integrated-affordance-competition-r1/
- 2026-08-28 | area:attribution | lesson:Exclusive ordinary intent gating is a supported hierarchy-specific regression mechanism for matched seed 22023239; untested rescue remains unclaimed | evidence:/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-close-02r-attrib-fatigue-r1/CLOSE02RATTRIB_VERDICT.json
- 2026-08-28 | area:attribution | lesson:Known R1 failure reached active fatigue recovery without a policy-visible REST route before terminal no-safe action; no rescue is claimed | evidence:/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-close-02t-attrib-fatigue-r1/CLOSE02TATTRIB_VERDICT.json

- 2026-08-29 | area:integrated-viability | lesson:Verified restorative REST landmark continuity delayed the known R1 fatigue/no-safe phenotype from parent tick 491 to tick 1484 but did not establish long-horizon viability; the remaining blocker is not cleared | evidence:/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-close-02u-recovery-landmark-r1/CLOSE02U_VERDICT.json
- 2026-08-29 | area:qualification-integrity | lesson:CLOSE-02U raw fresh R0 observations ran before the known-R1 gate because the cloned runner order differed from the directive; they remain preserved but are excluded from qualification claims | evidence:/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-close-02u-recovery-landmark-r1/CLOSE02U_VERDICT.json

## D-20260828 — CLOSE-02S final-authority replan

The accepted CLOSE-02 and CLOSE-02R failures rule out both flattening a valid
native intention into the ordinary motor pool and exclusive intent gating that
removes preventive regulation. CLOSE-02S supports one non-production candidate:
preserve authority-valid intent actions; when existing vector urgency indicates
preventive attention, admit only existing base actions mapped to that dimension;
retain hard recovery and one final existing arbitration authority. This is a
contract recommendation, not an implemented correction or viability claim.

## 2026-08-29 — CLOSE-02U start

CLOSE-02T attribution identified a policy-visible recovery-route availability
loss: active fatigue recovery had no REST route through tick 489. CLOSE-02U
tests whether existing bounded WorldModel remembered-estimate semantics can
retain a verified restorative landmark generically, without changing final
arbitration or physiology semantics. No organism result is claimed at start.

## 2026-08-29 — CLOSE-02U-ATTRIB closeout

CLOSE-02U's learned rest landmark remained policy-visible through the dedicated
R1/S16 reproduction, so landmark continuity itself was not lost. The route was
not executable in time: REST was repeatedly denied as `not_at_rest`, while the
bounded remembered estimate retained substantial uncertainty/support extent.
REST first became immediately unsafe at tick 1482; `NO_SAFE_ACTION` followed at
tick 1483 and retained aggregate evidence records critical fatigue at tick
1484. Classify this as `CLOSE02UATTRIB_SUPPORT_UNCERTAINTY_ROUTE_LOST` with
secondary `CLOSE02UATTRIB_RECOVERY_HORIZON_EXHAUSTED`. Do not claim rescue or
authorize an automatic successor.

## 2026-08-29 - CLOSE-02V execution stop

The V translation and pure contract passed, and the bounded correction was frozen at `8350df72c5a3dc4fd9ee05276176233803a51ff5`. The first diagnostic invocation executed no organism ticks because the frozen runner attempted `development[known_R1]`, but the sealed development manifest intentionally stores fresh R0-R3 populations only; the known R1 diagnostic is separately fixed at seed `57531938`. This is an execution-wrapper contract mismatch, not a scientific outcome. Preserve the stop as `CLOSE02V_EXECUTION_STOP_UNRESOLVED`; require Architect review before any correction or retry.

## 2026-08-29 - CLOSE-02V-R partial execution audit

The original V invocation did execute organism work: diagnostic A completed 500 ticks and diagnostic B completed 3,500 ticks, both passing, before the later known-R1 manifest dereference stopped the wrapper. The correct audit result is `CLOSE02VR_PARTIAL_EXECUTION_CONFIRMED`, not zero-tick confirmation. Preserve both outputs as consumed evidence and do not treat them as V fresh development results.
## 2026-08-29 - CLOSE-02V-R scientific failure

The V-R wrapper recovery separated the prior execution-history problem from the scientific result. Fixed diagnostics A and B passed; the corrected known R1/S16 run then failed at tick 555 after `NO_SAFE_ACTION` at tick 554 and critical fatigue. The CLOSE-02V verified-denial-aware recovery candidate therefore remains unqualified. Do not proceed to fresh populations or automatically remediate; return to Architect.
## 2026-08-29 - CLOSE-02V-ATTRIB convergence checkpoint

V is materially worse than U on the same known R1/S16 seed: critical fatigue moved from tick 1484 to 555. V-specific liveness risk is supported, but V1 urgent contract gating and V2/V3 reacquisition were not isolated because the one allowed parity harness did not retain semantic off-run rows; UUID-bearing full-result comparison is not scientific parity. This is evidence that local recovery rules are interacting around the seed, not authorization for another local patch. Stop local recovery patching pending Architect replan.

## CLOSE-02W — prospective recoverability can reuse the existing derived view

The generic E/R/P/H contracts currently lack natural production producers for required attempts, retry reserve, progress, and horizon fields. However, UMBRA already has a stronger fixed-size `HOMEOSTATIC_RECOVERABILITY_VIEW_V1` that derives bounded per-dimension route margins from policy-visible world support, verified effects, learned motion support, drift, and critical bounds without hidden truth, rollout, or action authority. The supported future contract is candidate-relative: only a demonstrated supported-positive to supported-exhausted transition may constrain an ordinary candidate before active recovery; UNKNOWN must remain neutral. Retained failures across energy, fatigue, and stimulation support this beyond one seed, but no historical rescue is established.

## 2026-08-29 — CLOSE-02X known-R1 boundary

The prospective recoverability mechanism can be implemented as a bounded, policy-provenanced candidate constraint and can preserve both previously cleared R0 authority diagnostics. Its realization alone is not sufficient evidence of integrated viability: on the frozen R1/S16 seed `57531938`, three energy positive-to-exhausted constraints occurred, yet the organism still reached `NO_SAFE_ACTION` at tick 923 and critical fatigue at tick 924. Do not infer a specific cause or remediate without a new Architect decision.
## 2026-08-29 — candidate veto can alter unrelated liveness through stochastic competition

A source-neutral candidate filter can preserve its named regulatory option yet still change another dimension's liveness when stochastic perturbations are consumed per surviving candidate. In X, removing one energy-destructive REST candidate changed the seeded scoring stream even though the same action won that tick; later decisions, outcomes, geometry, and fatigue regulation diverged. Also, negative option preservation cannot act for a dimension that never establishes a supported-positive route: fatigue was attended immediately but support became definite only as already exhausted. Future architecture decisions must separate prospective support acquisition/positive preparation from candidate-destruction veto, and must treat candidate-pool-dependent stochasticity as behaviorally relevant composition semantics.

## 2026-08-29 — stochastic individuality must compose by candidate identity

Sequential per-surviving-candidate RNG draws make unrelated candidate filtering behaviorally nonlocal: the filter can leave the immediate winner unchanged while reassigning later candidates' noise and changing downstream trajectories. Candidate-scoring stochasticity should be bound to persisted organism basis, authoritative tick, a versioned namespace, and canonical source-neutral behavioral identity. Candidate list index/count/order and proposal provenance are implementation accidents, not qualified individuality semantics. Environmental/execution stochasticity remains a separate domain.

## 2026-08-29 — learned support is not yet an explicit support-acquisition reason

UMBRA already generates and positively values fatigue-regulatory REST/toward-rest candidates during preventive attention. SelfModel can learn APPROACH support from successful VerifiedOutcome, but ordinary competition has no bounded policy-visible relation tying an exact missing support field to an already-generated candidate that can acquire it. Eligibility-only is insufficient when the candidate is already eligible; changing selection would require a separately authorized semantic rather than an inferred epistemic bonus or priority.

## 2026-08-29 — producer representation and behavioral recruitment are separate architecture requirements

SelfModel's verified motion-support update supplies an attributable same-capability producer pathway under the active body schema, but it does not establish that an action caused coincident route-geometry refresh. More importantly, recording a producer relation is behaviorally inert unless a qualified consumer can recruit the candidate. UMBRA's generic `uncertainty_reduction` term is candidate-independent and therefore cancels in ordinary ranking; its fixed INSPECT/ORIENT additions are not tied to exact missing support or verified producer provenance. A future decision must define candidate-specific uncertainty semantics without smuggling in an arbitrary epistemic weight, priority, or planner.

## 2026-08-29 — post-selection prediction cannot repair preselection evidence attribution

An action-conditioned model is not a candidate-selection consumer merely because it predicts the selected action before execution. UMBRA's SelfModel and WorldModel are invoked after final arbitration and maintain one pending prediction for outcome comparison. They neither evaluate alternatives nor predict exact support-field transitions. Turning categorical UNKNOWN/supported states into numeric uncertainty would add semantics, not reuse them. The remaining capability therefore belongs to broader action-selection architecture, not another local uncertainty-score patch.
## 2026-08-30 — learned prediction needs a defensible preselection consumer

Moving learned SelfModel/WorldModel prediction before selection is technically feasible only as a pure, fixed-size, UNKNOWN-preserving query; the existing mutating prediction APIs cannot be called once per candidate. That alone is not enough. Feeding predictions into UMBRA's current summed score would combine learned evidence with heterogeneous authored terms whose units and calibration are not established. The scientifically minimal boundary is therefore not another score patch: replace ordinary scalar-total evaluation with bounded distributed competition while preserving proposal generation, hard constraints, candidate-stable stochasticity, one final authority, Governance, Embodiment, and verified selected-only learning.

## 2026-08-30 — incomparability can remain explicit without blocking one final action

Heterogeneous organism evidence need not be converted into common units to affect choice. A candidate can be eliminated only by supported dominance inside coherent proposition channels; UNKNOWN or a genuine cross-channel tradeoff keeps both alternatives on the frontier. Existing candidate-local stochasticity can then resolve that explicit incomparability without changing evidence, rewarding proposal duplication, or erasing a supported dominance relation. This preserves one final action while keeping hard authority outside ordinary competition.

## 2026-08-30 — broad tests can cross a scientific execution boundary

A broad pytest command is not necessarily pre-freeze pure validation. If any
collected test creates and ticks an organism, invoking that suite is organism
execution. Staged scientific directives therefore need an explicit pure-test
allowlist before freeze; runtime-instantiating tests belong only in their
preregistered post-freeze phase.

## 2026-08-30 — replay properties must outlive superseded implementation authority

When a qualified behavioral property was previously tested through a scalar ordinary scorer, replacing the scorer does not waive the property. A valid migration identifies the preserved authority invariant, cites the prior semantic supersession, and proves that the replacement neither hard-codes the new observed winner nor permits optional machinery to replace the ordinary authority path.

## 2026-08-30 — a compatible execution can still fail the distributed mechanism

Passing retained replay and safety-compatible diagnostics does not establish supported-dominance behavior. The frozen A/B traces must contain at least one actual supported elimination; a full nondominated frontier at every qualifying ordinary decision demonstrates that the mechanism was not realized and cannot be remedied after freeze.
## 2026-08-31 — AS-003E authorized causal-role partitioning boundary

- Architect accepted AS-003D’s finding that `SUPPORTED_DOMINANCE_DISTRIBUTED_COMPETITION_V1` is structurally insufficient as forward ordinary selection: channel separation and UNKNOWN/applicability protections stay historically useful, but universal no-worse dominance made CLOSE-02Z de facto selection authority.
- AS-003E must distinguish a subsystem being causal from that subsystem contributing an independent cross-candidate objective. The source/evidence role map is frozen before any projection so channel membership cannot be selected for a preferred result.
- The locked AS-003E comparison boundary does not remove a subsystem from the organism: it preserves source-neutral candidate specification, motivational context, continuity, hard authority, and selected-only learning as distinct causal roles. Only bounded immediate physiology, body executability, and one-step environmental effect propositions are projected as ordinary comparison evidence.
- AS-003E’s locked role partition alone did not restore supported-dominance discrimination: it retained 0 relations across 76,216 pairs and 2,647 full frontiers. Separating causal roles is still necessary, but no existing owner-neutral state says which non-hard concerns are active for ordinary comparison. That missing categorical activation semantics must be resolved before proposing a common numerical behavioral-control claim; normalizing heterogeneous channel values would be arbitrary weighting.

## 2026-08-31 — AS-003F motivational-context lifecycle boundary

- `ACTIVE/INACTIVE` can express owner-derived non-hard behavioral relevance without encoding relative importance when UNKNOWN remains evidence quality rather than a third rank; it must not suppress first experience.
- Context persistence requires a source-neutral engaged identity plus owner revalidation. Existing action/capability continuity cannot substitute for engagement, and persistence alone leaves initial election and starvation unresolved.
- A bounded corpus with five development-plus-memory coactivations is enough to expose missing simultaneous-context semantics but not enough to promote or globally reject stochastic context election across physiology, temporal, routine, social, and individuality owners.
# UMBRA-AS-003H — verified episode learning does not identify voluntary release — 2026-08-31

- Verified outcomes can supervise action consequences and owner lifecycle endings, but not an active context's voluntary yield to an active rival; the latter needs its own independently grounded event proposition.
- A model fitted to controller-generated release times is self-imitation, even if the model is a statistically valid hazard estimator.
- Event clocks provide a body-independent reconsideration boundary but do not establish a release cause. A parameter-free probability/distribution only hides the calibration choice.
- If non-hard continuous rivals must eventually switch without arbitrary hazard or fairness scheduling, UMBRA needs one calibrated common behavioral-control claim rather than another standalone switching model.
# UMBRA-AS-003I — common salience semantics are not calibration — 2026-08-31

- A cross-owner behavioral-access bid can be defined without becoming outcome utility, but its common meaning does not supply owner adapters or numeric anchors.
- Existing quantified physiology and development state cannot be exported as common salience merely because they are numeric; that would privilege instrumented owners.
- Verified associations can modulate an owner's expression but cannot learn relative cross-owner salience from outcomes without circular wins or forbidden counterfactual reward.
- Any future common-control work must establish calibration semantics first; event-tie stochasticity, categorical engagement, and hard authority remain separate boundaries.
## AS-003K start — resolver discipline

The four true drives share critical/viable/ideal categorical concepts, but shared Python representation and the existing owner-local urgency arithmetic do not establish cross-drive behavioral comparability. A partial order and any prospective-horizon candidate must be evaluated against frozen semantic controls before their apparent discrimination can be treated as lawful.
## AS-003K — regulatory class and horizon boundary

Shared critical/viable categories are lawful cross-drive *state classes*, not a total behavioral preference. A per-drive time-to-loss-of-viable-state calculation can be coordinate-invariant if it refers to the same post-action regulatory event and all physical terms transform together. Neither fact gives a lawful four-owner conflict resolver: category ties preserve ordinary action-relevant differences, and aggregating per-drive horizons manufactures a bottleneck scalar or alters hard safety.
## AS-003L start — feasibility is not preference

Scheduling terminology does not automatically preserve UMBRA boundaries. Deadline, service demand, laxity, resource serialization, opportunity support, and preemption must each be independently grounded before any feasibility relation can be treated as distinct from a hidden priority or scalar optimizer.
## AS-003L — bounded enumeration can still be planning

An explicit finite upper bound does not make future action-order construction a read-only preselection proposition. Under UMBRA's coupled effects, pending actuation, route alternatives, and changing supported opportunities, deciding joint schedulability by service-order enumeration is a multi-step planning act even with only four drive owners.
## AS-003M start — planning is an allowed capability, not automatic authority

The project-goal planning clause supersedes a blanket local `NO PLANNER` guard but not the safeguards against utility authority, fabricated future truth, imagined learning, unbounded search, or bypassing recovery, Governance, or Embodiment. A lawful planner can only provide read-only prospective evidence for the current action and must be revalidated from real verified outcomes.
## AS-003M — planning needs an evidence-composition substrate

Boundedness does not make planning lawful by itself. A prospective witness needs an immutable hypothetical state, a pure categorical transition, evidence/provenance that only weakens with depth, support for coupled effects/timing/routes/opportunities/pending commitments, and material-change invalidation. Existing one-step predictive views and a bounded authored scalar plan queue are not substitutes; hypothetical calls must never enter prediction, learning, persistence, or VerifiedOutcome writers.
## AS-003O start boundary

- The accepted AS-003N substrate is not a planner. AS-003O must prove that actual owner sources can populate it soundly, including categorical uncertainty, correlated outcomes, opportunity duration, and total path-frontier limits, before any shadow integration can be considered.
## AS-003O — source backing is a separate proof obligation

- A current owner observation can lawfully populate an exact root envelope as `VERIFIED_OBSERVED_SUPPORT`; that says nothing about future persistence and must not be renamed `HARD_CONTRACT`.
- Present opportunity, learned mean, and confidence are not a valid-through guarantee. A robust continuation claim needs an authoritative root-relative horizon, categorical route/completion/capability support, and an immutable commitment snapshot from the same material source state.
- Robust continuation quantifies differently over choices and outcomes: current/service choices are existential, while every supported outcome branch must have a witness. Exact P2 inclusion is safe only for aligned branch identities; no count, probability, slack, or score is a substitute.
## 2026-09-01 — AS-003P execution-wrapper boundary

- Script importability is part of a no-retry one-shot protocol. A harness that imports a repository namespace before placing the repository root on `sys.path` can consume the generation even when it executes zero organism ticks.
- Preserve the distinction: the frame/modal implementation is target-tested (`41/41` twice), but observer neutrality and actual-source usefulness remain unknown. Do not promote pure fixtures to operational evidence.
- For future Architect-authorized generations, import-path execution must be proven without organism creation before the one-shot command is frozen. This is a recommendation boundary, not authority to repair or rerun AS-003P.

## 2026-09-01 — matching actions and RNG does not prove observer neutrality

- A default-off/write-only diagnostic can preserve selected actions, candidate
  identities, timeline physiology, and RNG while still changing authoritative
  accepted model state or events. Observer qualification must therefore compare
  complete authoritative event/state and subsystem hashes, not only behavior.
- Shadow-derived scientific profiles are invalid when their acquisition changes
  authoritative state, even if every frame is syntactically complete. Preserve
  raw capture as protocol evidence, but do not use it to answer the architecture
  question or tune a successor.
- 2026-09-01 | area:observer-parity | lesson:sorting raw UUID dictionary keys
  before value-only first-occurrence tokenization is not administrative-ID
  canonicalization; raw keys remain unequal and traversal order can bind tokens
  to different semantic records. Owner maps need owner-specific semantic
  multisets or relation-preserving graph labels frozen before execution.
- 2026-09-01 | area:world-model | lesson:`WorldModel.to_state()` and
  `state_hash()` are complete persistence/integrity representations and are
  intentionally sensitive to generated IDs; `accepted_state()` is structural
  replay evidence but is too narrow to replace field-level observer parity.
- 2026-09-01 | area:temporal-events | lesson:independent non-seeded session IDs
  legitimately change trusted-sample and temporal state hashes even when all
  primary temporal/event semantics match; derivative hashes must be reported
  separately from their source values.
## AS-003P-R3 — prospective comparator scope can reveal a new identity boundary

- Administrative-ID invariance must be owner/source-declared before execution, but the same discipline can expose an identity field that remains classified authoritative. A mismatch must terminate the generation even when behavior, timeline, and RNG are equal; reclassifying the field after seeing the pair would invalidate the prospective gate.
- A parity-gated shadow trace is not scientific modal evidence merely because complete bytes exist. When parity fails, retain the trace but do not compute or publish modal distributions, exposure claims, or action-selection recommendations.
# AS-003P-R4 — fresh body names versus replacement identity

- A generated identifier may be authoritative and behaviorally important through equality relations without requiring literal equality across independent experimental births. For adapter `body_instance_id`, independent replicas require owner-scoped bijective relation preservation; restart/replay of the same organism requires exact literal continuity.
- Attachment generation is a lifecycle/version token, not a physical-replacement identity: it increments for attach, detach, and compatible profile swap.
- Current `detach()` plus `attach()` cannot create a distinct adapter body instance because detach retains the old name and attach reuses it.
- SelfModel body replacement and adapter/habitat body attachment are separate identity surfaces without one authoritative replacement transaction. This prevents an end-to-end claim that a new physical body replaced the old one while the organism remained the same.
- Common-root branching is the least-confounded future observer design, but it must not bypass an unresolved source identity contract.

# AS-003S — atomic body replacement requires prospective owner state

- A true physical-body replacement is not detach plus attach: the durable claim
  must mint a new body entity and change every material body relationship in one
  consistency boundary while preserving constitutional identity.
- Preparing cloned SelfModel/adapter/occupancy state and committing the dedicated
  replacement event with a matching full snapshot permits rollback before COMMIT
  and exact restart recovery if live application is interrupted afterward.
- Possession cannot be silently migrated as part of identity repair. An old-body
  held object and every pending execution surface are replacement preflight gates.
- Attachment generation remains a lifecycle token; physical body ID, SelfModel
  binding/schema, and compatible profile swap are distinct identity dimensions.
## 2026-09-01 — Public repository evidence surface

- A technically strong evidence repository can remain externally opaque when its default
  branch or root landing page does not expose the authoritative lineage. Validate the live
  GitHub default branch and rendered README, not only committed Markdown.
- A public claim table should distinguish bounded qualification, bounded evidence,
  permanent failure, and unqualified research questions; globally green badges or summary
  prose can erase meaningful inherited test debt and scientific boundaries.
- Frozen architecture dossiers can remain useful historical evidence while lagging current
  implementation. A concise evidence guide should label that boundary and route current
  claims to source and result packets instead of silently presenting frozen documents as
  live architecture truth.

## 2026-09-01 — Common-root observer experiment boundary

- When independently born replicas contain legitimate fresh identities, the cleaner
  causal observer design is one prepared authoritative root cloned before treatment.
- Preexisting organism, body, model, Habitat, event-prefix, and RNG identity must be
  exact across common-root branches; only source-declared post-fork administrative
  names may use relational equivalence.
- Modal evidence is scientifically interpretable only after the prospectively frozen
  observer comparator reports zero semantic differences.

## 2026-09-02 — Retained modal labels cannot recover dropped timing evidence

- Equal top-level continuation labels can hide materially different candidate
  successor states; retain branch-level effects and witnesses when future relational
  attribution is anticipated.
- Opportunity persistence alone is not schedulability evidence. A lawful deadline
  comparison also needs source-backed route movement demand, completion demand, and
  their binding to the specific opportunity.
- A point-zero timing field must not be treated as zero execution demand when the
  source route envelope was never captured; the conservative result is UNKNOWN.
- Repository-root module invocation matters for pure research tooling: an initial
  path-context import failed before evidence publication, then the corrected module
  invocation proceeded without runtime import or scientific retry.
## UMBRA-AS-003P-R6A start boundary — 2026-09-02

- R6's `distance_support_upper_bound` and SelfModel movement intervals are
  plausible ingredients, but neither is automatically a future traversable
  route guarantee. Preserve source modality, body-schema binding, geometry
  assumptions, and provenance; missing route demand remains `UNKNOWN`.
- R6A must distinguish a source join from a new learned route-demand primitive
  and must not use the historical R6 aggregates as tuning evidence.
## AS-003P-R6A source-contract boundary — 2026-09-02

- Body-relative radial support is not a route-length guarantee. A quotient of
  distance support by observed APPROACH progress can be a research MAY
  projection under explicit geometry assumptions, but cannot support robust L2
  scheduling from current source semantics.
- Verified SelfModel progress/completion intervals remain observed support. A
  body-schema match prevents stale transfer but does not establish future
  dynamics, route absence, or opportunity-specific binding.
- WorldModel affordance evidence is a lawful ingredient for INSPECT only when
  joined to a specific policy-visible entity instance and an ACTIVE belief.
  Kind-level affordance and Habitat execution truth must remain separate.
- The smallest missing upstream fact is a verified, bounded,
  opportunity-specific route-demand/timing envelope with provenance, failure
  modes, and body-schema binding; do not repair the gap with a scalar, weight,
  planner, or hidden world truth.
# 2026-09-02 — R6B verified route-learning boundary

- R6A established that radial opportunity distance plus historical APPROACH support
  cannot lawfully provide a robust opportunity-specific route-demand bound.
- The smallest authorized next primitive is a WorldModel-owned,
  opportunity- and body-schema-bound `VerifiedRouteExperience`, learned only from
  verified route episodes and retaining raw movement/completion/terminal/failure
  observations without scalarization.
- Ambiguous binding, denied/unverified actions, route switches, body changes,
  interruptions, and incomplete episodes must not create completed evidence.
- R6B is default-off and write-only with respect to existing action selection and
  planning surfaces; historical R5A/R6/R6A evidence is not tuning input.
