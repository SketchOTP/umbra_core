# Project Profile

Current authority: UMBRA-CLOSE-02U-ATTRIB TERMINAL / diagnostic-only from 68746231742a904112eed89d759a22f7f384e23b. Verdict `CLOSE02UATTRIB_SUPPORT_UNCERTAINTY_ROUTE_LOST`, secondary `CLOSE02UATTRIB_RECOVERY_HORIZON_EXHAUSTED`: the single dedicated observational R1/S16 seed 57531938 reproduction matched `NO_SAFE_ACTION` tick 1483 and retained critical fatigue tick 1484; the learned rest landmark remained visible but did not yield an executable route. No production changes, qualification retry, reseed, or automatic successor.

Previous authority: UMBRA-CLOSE-02U TERMINAL with verdict=CLOSE02U_KNOWN_R1_FAIL from d44b453ae2f091fb31f1498724ab16c1c0e02387. Diagnostics A/B passed; known R1 seed 57531938 failed at tick 1484 after NO_SAFE_ACTION at tick 1483. Permanent evidence=/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-close-02u-recovery-landmark-r1/; no automatic successor was authorized.
## Previous authority - UMBRA-CLOSE-02S terminal

As of 2026-08-28, CLOSE-02S is terminal with
`CLOSE02S_INTERRUPTIBLE_INTENT_CONTRACT_SUPPORTED`. Its non-production
architecture research supports the CLOSE-02T implementation candidate using
existing UMBRA semantics. CLOSE-02T is now the active implementation and
qualification directive.

## Repository
- Name: UMBRA-CORE
- Root: `/home/sketch/Projects/UMBRA-CORE`
- GitHub: `git@github.com:SketchOTP/umbra_core.git`
- Default branch: `master`

## Strategic documentation
- Canonical Notion: https://app.notion.com/p/3b3833cb27ff80309f1fe73e7af37fe6
- Authority 3.0 package: https://app.notion.com/p/3bf833cb27ff811aae15def88959797e
- Project goal authority: `.agent/PROJECT_GOAL.md`

## Technical profile
- Languages and formats: Python 3, shell, SQL/SQLite, JSON/JSONL, Markdown.
- Frameworks: stdlib-first organism runtime; pytest validation.
- Persistence: SQLite WAL event/state authority with snapshots and replay.
- Runtime environments: Linux on Atlas; reusable core intended for compatible digital and physical bodies.
- Primary test command: `python3 -m pytest`
- Governance validation: `python3 tools/validate_governance.py`
- Authority 3.0 validation: `python3 scripts/validate_authority_v3.py`
- D-012 process checks require a short AF_UNIX-safe base temp, for example `--basetemp=/tmp/u`.

## Important integrations
- GitHub remote `github` — committed implementation and publication authority.
- Canonical Notion project page — strategic state and Architect decisions.
- `\\\\atlas\ATLAS\100_ACTIVE\Projects\UMBRA-CORE` — canonical permanent evidence authority. Atlas Linux mount: `/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE`.
- `/mnt/storage1tb` remains transient/direct-attached scratch only.
- Mimir/Serena configuration — optional repository navigation support when configured and reachable; never a prerequisite for ordinary source inspection.

## Compatibility commitments
- Preserve constitutional identity, event-ledger authority, deterministic replay, governance boundaries, verified-outcome learning, and body-independent organism semantics.
- Preserve qualified D-001 through D-009 results and sealed historical evidence.
- Historical D-010 failures remain permanent evidence for their original generations; current D-010Q5 temporal continuity is qualified as `UMBRA_D010_TEMPORAL_CONTINUITY_QUALIFIED`. D-012 historical formal failures remain authoritative.
- Renderers, language systems, bodies, and external interfaces must not become organism authority.

## Safety / operational constraints
- No formal P0 or formal tag without an explicit Architect directive.
- Preserve historical evidence, thresholds, verdicts, tags, and append-only governance history.
- Do not edit `.agent/LIBRARY_REVIEW.md`; it is librarian-managed and intentionally untracked.
- Permanent evidence must be finalized on the Atlas shared drive. The retired `\rpi5\RPI5SharedDrive` path must not be used for new work. Active SQLite/WAL, AF_UNIX sockets, and process scratch remain on local/direct-attached storage such as `/mnt/storage1tb/umbra-scratch`; never run active SQLite/WAL directly on SMB. The 50 GiB evidence-capacity gate applies to the Atlas canonical evidence filesystem; scratch requires workload-specific headroom.
- Do not force-push, rewrite history, or alter unrelated `main`.

## Current scientific status

### Terminal authority: UMBRA-D-014H3A

D-014H3A closed from the accepted H3 closeout tip
d7877ca2fc24741434eebbdf60f257d6ac793c63. It is limited to reconciling the
historical R2 social-event runner with current authoritative habitat/social
semantics and stopped fail-closed before runner repair. H3 selector science,
fresh holdouts, organism qualification, formal D-014, D-013/AX, retries,
reseeds, and production decision changes were not started.

The canonical Atlas project path is /srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE.
The existing direct Atlas filesystem and Dewey layout are preserved; no
storage topology change, pool operation, or migration is part of H3A.

Initial source inspection found that the authoritative HabitatEngine
SOCIAL_ENTITY projection carries only hidden_partner_id, x, and y, while
legacy partner perception requires visibility, true cues, and response policy.
A complete authority-consistent bridge is absent from the current source
semantics. Verdict: D014H3A_CORE_SOCIAL_HABITAT_BRIDGE_MISSING. Evidence:
/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/d014h3a-r2-authority-repair-r1/.

### Terminal authority: UMBRA-D-014H3

D-014H3 began from exact baseline
40fd210c47d9a0dc180804e92ce5545a90cc50b1 as a fresh, shadow-only,
non-production integrated prospective action-selection generation. Phase A
governance reconciliation was performed, but the required R2 runner-authority
preflight stopped with D014H3_R2_RUNNER_UNRESOLVED.

The historical R2 runner calls Embodiment.set_occlusion after attaching the
authoritative HabitatEngine, so the call raises
HabitatWriteRejected: habitat_engine_is_sole_writer. The S10 authoritative
state has no social object and projects no partner; direct engine mutation of
partner:d014 fails with MutationRejected: missing_object:partner:d014.
No workaround was accepted because bypassing the engine or inventing a social
object would alter the frozen scenario semantics.

No H3 selector implementation, fresh holdout outcome, formal D-014 run/tag,
production change, retry, or reseed occurred. Permanent evidence is on the
Atlas share at
\\\\atlas\\ATLAS\\100_ACTIVE\\Projects\\UMBRA-CORE\\evidence\\live-evidence\\d014h3-integrated-prospective-selection-r1/.

### Terminal authority: UMBRA-D-014H2

D-014H2 closed from H1 closeout `7fa795ddd3a1b782382c51e9b7068d7ecd438f6d`
with verdict `D014H2_UNIFIED_POOL_BASELINE_FAIL`. The default-disabled trace
contract passed parity/replay and complete required-field checks. Real rows
translated through unchanged H1 with zero rejected proposals, overflows, or
trace-hash mismatches. Fixed R0 completed 8/8 x 7,200 without critical failure,
but known R1 reproduced fatigue failure at tick 372 and three R1 holdouts also
failed. The first R2 holdout stopped at an existing runner `HabitatWriteRejected`
at the scheduled occlusion; it and R2/R3 were not retried.

Closeout commit/master: `45034ef41ccb7f7e6328e8f666402951f5badf85`.
Evidence: `\\atlas\ATLAS\100_ACTIVE\Projects\UMBRA-CORE\evidence\live-evidence\d014h2-production-trace-translation-r1/`.
Production semantic changes: 0; no formal D-014/tag, D-013/AX, retry, reseed,
or remediation. Integrated viability remains unqualified and D-014I is not
authorized automatically.

### Terminal authority: UMBRA-D-014H1

D-014H1 stopped with D014H1_TRANSLATION_UNEXPLAINED from governance baseline
ce8807d9786eb93dfc7a25449e76b16a4cf0c854. The fresh unified-pool shadow was
frozen at 0308403870d41c0b1b2ba48c4340c21c94f6be1e; its 36 semantic rules were
exact, focused tests passed 5/5, and synthetic replay was byte-equal. Synthetic
source coverage passed 12/12, but no production-runtime trace adapter produced
a translation row. R0 organism outcomes, D-014H integration, and holdouts were
not run. Production authority remains zero; D-014I is not authorized.

Evidence root: /srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/d014h1-fresh-unified-pool-r1/.

- Qualified sequential baseline: D-009 seal `af35371`.
- Historical D-010 verdict remains `UMBRA_D010_PERFORMANCE_FAIL`; current D-010Q5 verdict is `UMBRA_D010_TEMPORAL_CONTINUITY_QUALIFIED`. Historical Gates 0-12/13 and parent-Mimir state remain permanent for that generation.
- D-010 verdict: `UMBRA_D010_PERFORMANCE_FAIL` remains the historical verdict; current D-010Q5 is qualified separately.
- D-011 is independently qualified under the D-009 predecessor.
- D-012B2 remains `UMBRA_D012B_P0_INTEGRITY_FAIL`.
- D-013AO is accepted as `D013AO_SHADOW_RECOVERABILITY_VIEW_QUALIFIED`.
- D-013AP is authorized only as a non-formal, fixed, negative-only, hysteresis-capped soft option-preservation qualification in its historical directive record; it is not active now.
- D-013/AX evidence is historical and not active.
- D-014 through D-014D are current integrated-viability evidence. D-014D is terminal with verdict `D014D_FAILURES_HAVE_DISTINCT_MECHANISMS`.
- D-014E reached D014E_EXECUTION_STOP_UNRESOLVED after a passing shadow gate and conditional implementation; required long validation is storage-blocked and D-014E is terminal.
- D-014E1 is terminal with `D014E1_R1_SCIENTIFIC_FAILURE`: R0 passed 8/8 x 7,200; R1 seed `57531938` failed at tick 372 with fatigue 0.951 after verified MOVE; R2/R3 were not run.
- D-014E2 is terminal from `767496ad5572ba57f6fe4acde59eccece56b8d25` with `D014E2_CAUSE_CONFIRMED_REQUIRES_BROADER_ARCHITECTURE`. Exact R1 reconstruction succeeded; three preregistered shadows produced zero substantive 7,200-tick rescues.
- D-014E2 retained no production correction, changed no thresholds/effects/habitat, used no hidden truth, reseeded, retried, created no formal tag, and did not reopen D-013/AX.
- D-014F is terminal from `edbd9ce168000d9d7b72b4de56d17144f51bbb83` as `D014F_PROSPECTIVE_OPPORTUNITY_SHADOW_FAIL`: objective S16 physical viability was shown by an evaluator-only bound, but the full-runtime policy-visible shadow was overwritten after arbitration and failed R1 plus fixed R0 compatibility. No production implementation was retained.
- D-014G1 is terminal as `D014G1_D014F_ARTIFACT_UNRECOVERABLE`: the exact D-014F prospective generator cannot be replayed from retained artifacts without semantic choices. No replay artifact or D-014G reintegration shadow was run.
- D-014H is terminal as D014H_UNIFIED_POOL_ARTIFACT_INSUFFICIENT: fresh preregistration, non-production source freeze, and replay passed, but the retained D-014G unified-pool artifact lacks executable baseline replay semantics; no organism outcome run or production authority occurred.
- Integrated long-horizon viability remains unqualified; UMBRA CORE remains incomplete.

## D-014H3B closeout

The current social/habitat authority bridge is preflight-qualified, not an
organism qualification. HabitatEngine remains the sole spatial writer;
environment-side social profiles persist with SOCIAL_ENTITY state; Perception
emits anonymous noisy cues; SocialEngine remains hidden-identity-free. Evidence
is permanent under `/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/d014h3b-social-habitat-bridge-r1/`.

## Source-of-truth boundaries
- Notion: strategic/project understanding and Architect acceptance/authorization.
- GitHub: committed implementation evidence.
- Codex working tree/runtime: live technical state.
- `.agent/PROJECT_GOAL.md`: sole authoritative UMBRA product goal.
- `.agent/INDEX.md`: Authority 3.0 state router.

## UMBRA-D-014H3B active routing

D-014H3B is active from exact baseline
f37521828f9127ab4714cb08150a18da383a326e. It is authorized to repair the
core bridge between authoritative HabitatEngine social entities and the
trusted perception membrane, while keeping SocialEngine hidden-identity-free.
The current H3A terminal finding, historical D-014 runner/evidence, D-006
relationship semantics, physiology, recovery, H3 selector, and formal D-014
boundaries remain protected.

Permanent H3B evidence belongs at
/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/d014h3b-social-habitat-bridge-r1/.


## UMBRA-D-014H3C active routing — 2026-08-26T09:48:06Z

H3B is accepted as the bounded social/habitat authority prerequisite at
5c18693283fc48bef738bd1e0ca5fad678ce211a. H3C is now authorized from that
exact tip for a fresh integrated, replay-first, development-only affordance
competition shadow. The evidence root is /srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/d014h3c-integrated-affordance-competition-r1/. Fixed R0 and the known
R1 seed gate the fresh sealed holdouts; H3C does not authorize production
selector changes, formal D-014, D-013/AX, automatic D-014I, retries, reseeds,
or storage migration.


## UMBRA-D-014H3C closeout — 2026-08-26T09:59:32Z

D-014H3C stopped at the required known-R1 gate. Fixed R0 passed 8/8 x 7,200;
known R1 seed 57531938 reproduced the accepted fatigue failure at tick 372.
Fresh holdouts remained sealed and unexecuted. The evaluator-only shadow
contract passed 6 focused tests; no production selector authority or organism
rescue was demonstrated. Evidence: /srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/d014h3c-integrated-affordance-competition-r1/. Return to Architect.

## Current status supersession — UMBRA-CLOSE-02-ATTRIB

As of 2026-08-28, the sole active directive is
`UMBRA-CLOSE-02-ATTRIB`, from governance baseline
`14d26a248f26d0167c85b819a17f7b51bdfb6292`. CLOSE-02-DECIDE remains terminal
with `CLOSE02DECIDE_EXECUTION_STOP_UNRESOLVED`; its preserved Control-A trace
through tick 3869 is read-only and Candidate B was not run under that
predecessor. This fresh diagnostic authorizes exactly one immutable Candidate-B
R0/S0 run at `20542be24c90317aefbb0df9cfdc2202b9d8942b`, seed `45878900`, with
observational tracing and a 500-tick ceiling or natural failure. No Control-A
rerun, production change, qualification, remediation, retry, reseed, formal
tag, R1/R2/R3, H3, D-013/AX, or threshold/effect change is authorized.

Permanent evidence root:
`/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-close-02-attrib-b-r1/`.

## UMBRA-CLOSE-02-ATTRIB terminal supersession

The one authorized Candidate-B diagnostic completed exactly once and ended
with `CLOSE02ATTRIB_FINAL_AUTHORITY_REGRESSION`. The historical R0/S0 seed
`45878900` phenotype was exactly reproduced at `no_safe_action` tick 219 and
critical tick 220 from candidate commit `20542be24c90317aefbb0df9cfdc2202b9d8942b`.
The preserved Control-A trace was not rerun and remains read-only through tick
3869. The first final-action divergence at tick 1 is the bounded attribution
basis. Recommendation: `REPLACE_CLOSE02_FINAL_AUTHORITY_ARCHITECTURE`.
No production change, qualification, retry, reseed, formal tag, or automatic
successor is authorized by this closeout. Evidence is permanently retained at
`/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-close-02-attrib-b-r1/`.

## Current authority — UMBRA-CLOSE-02S terminal

As of 2026-08-28, CLOSE-02S is terminal with
`CLOSE02S_INTERRUPTIBLE_INTENT_CONTRACT_SUPPORTED`. Its non-production
architecture research supports one bounded implementation candidate using
existing UMBRA semantics. It does not authorize production implementation,
organism runs, qualification, formal tags, H3, or D-013/AX. Recommendation:
`UMBRA-CLOSE-02T_INTERRUPTIBLE_INTENT_IMPLEMENTATION_CANDIDATE`; return to
Architect.
