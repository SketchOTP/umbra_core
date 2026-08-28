## UMBRA-CLOSE-02-ATTRIB active routing

`UMBRA-CLOSE-02-ATTRIB` is the sole active directive from exact governance
baseline `14d26a248f26d0167c85b819a17f7b51bdfb6292`. It authorizes exactly one
isolated Candidate-B R0/S0 diagnostic at commit
`20542be24c90317aefbb0df9cfdc2202b9d8942b` with seed `45878900`, using
observational tracing and a 500-tick ceiling or natural failure. The preserved
Control-A trace is reused read-only; Control A is not rerun. No production
changes, qualification, remediation, retries, reseeds, R1/R2/R3, formal tag,
H3, D-013/AX, or threshold/effect changes are authorized.

Permanent evidence root:
`/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-close-02-attrib-b-r1/`

The predecessor `CLOSE-02-DECIDE` is terminal with
`CLOSE02DECIDE_EXECUTION_STOP_UNRESOLVED`; its preserved A trace and
uncertainty remain unchanged.

## UMBRA-CLOSE-02-DECIDE terminal routing

UMBRA-CLOSE-02-DECIDE terminated with
CLOSE02DECIDE_EXECUTION_STOP_UNRESOLVED. Control A started once at
178f0e37855c42a3b97975189b7700b5b16b7506 and reached trace tick 3869 before
the external collector's 180-second wrapper limit. Candidate B was not
started, so no final-authority attribution is established.

Partial evidence:
/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-close-02-decide-r0-attribution-r1/CLOSE02_DECIDE_A_TRACE_PARTIAL.jsonl

No retry, production change, remediation, qualification, formal tag, or
successor directive occurred. CLOSE-02F, CLOSE-02Q, and CLOSE-02 remain
terminal historical directives.

---

## UMBRA-CLOSE-02F terminal routing

UMBRA-CLOSE-02F was the qualification directive from exact baseline
`c4f387433f42ffa5517b40c0667a97b6e03af4d0`. It is now terminal with
`CLOSE02F_R0_DEVELOPMENT_FAIL`: the first fresh R0 seed failed at tick 220
after first `no_safe_action` at tick 219. No later gate or formal population
was opened, and no automatic successor is authorized.

Its file-scoped Atlas durability and regime-fidelity preflights passed. The
qualification evidence is at
`/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-close-02f-final-authority-qualification-r1/`.
The qualification probe must use file `fsync`, atomic rename, containing
directory `fsync`, readback, hashing, and cleanup. `sync`, `sync -f`, and
`syncfs` were not used. CLOSE-02 and CLOSE-02Q remain terminal historical
records.

## UMBRA-CLOSE-02Q terminal routing

UMBRA-CLOSE-02Q stopped before qualification on
`CLOSE02Q_STORAGE_PREFLIGHT_FAIL`. CLOSE-02 remains terminal with
`CLOSE02_EXECUTION_STOP_UNRESOLVED`; its G1 was not run. No active directive
is inferred from this stop.

Canonical evidence:
/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-close-02q-final-authority-qualification-r1/

The configured Git remote is named github (not origin); publication checks use
github/master without changing remote configuration.


# Authority Project-State Index

## Project identity
- Project: UMBRA-CORE
- Authority schema: 3.0
- Canonical Notion: https://app.notion.com/p/3b3833cb27ff80309f1fe73e7af37fe6
- GitHub: https://github.com/SketchOTP/umbra_core
- Project goal: .agent/PROJECT_GOAL.md
- Project profile: .agent/PROJECT_PROFILE.md
- Current state: .agent/CURRENT.md

## Current pointers
- Current stage: Authority 3.0; CLOSE-02F R0 development failure
- Active directive: none; last terminal directive: UMBRA-CLOSE-02F
- Last task packet: .agent/tasks/completed/UMBRA-D-014H3J/; prior terminal packet: .agent/tasks/active/UMBRA-D-014H3I/
- Previous terminal task packet: .agent/tasks/active/UMBRA-D-014H3D/
- Parent terminal packet: .agent/tasks/completed/UMBRA-D-014H3B/
- Last accepted outcome: CLOSE02F_R0_DEVELOPMENT_FAIL
- Canonical permanent evidence: Atlas /srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE
- Last state sync: 2026-08-26T21:30:33Z

## UMBRA-D-014H3I terminal routing

D-014H3I froze a fresh experiment-only selector/wrapper contract from exact
baseline b122131db31679bbfedf153bb7a1c15265c7fcc0. The R0 population ran all
eight fixed seeds once; all eight ended in genuine physiological failure
after the structured NO_SAFE_ACTION path, with no harness exception. Failure
ticks were 272, 295, 294, 295, 183, 298, 171, and 295. R1/S16 and the sealed
H3D holdouts were not run because the R0 predecessor gate failed.

Terminal verdict: D014H3I_R0_GATE_FAIL. H3H was not retried. No production
default selector authority, formal D-014, D-013/AX, threshold/effect change,
hidden truth, historical evidence rewrite, retry, reseed, or storage change
occurred.

Permanent H3I evidence:
/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/d014h3i-no-safe-composition-r1/



## UMBRA-D-014H3H terminal routing

D-014H3H started from exact baseline
b2435089ccf11e3c3e354443115ee61934003aff. Focused tests, H3D compatibility,
R2/R3 authority preflight, Authority 3.0, and governance passed. The first
authorized R0 population invocation started with seed 41241905 and stopped
at the experiment-only callback with RuntimeError:
d014h3h_no_selected_candidate. The wrapper did not persist a failure
envelope, so no scientific viability result is claimed.

The frozen H3H contract prohibits retry, reseed, known-R1, and sealed-holdout
execution after this stop. Production-default selector behavior, thresholds,
effects, historical evidence, and sealed H3D holdouts remain unchanged.
Permanent H3H evidence:
/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/d014h3h-deterministic-authority-safe-selector-r1/

## UMBRA-D-014H3G terminal routing

D-014H3G is authorized from exact baseline
2be05c7f661abb1c4d8505eb932d74eadc30114b after accepted H3F execution-stop
verdict. First reproduce H3F R0/S0 seed 41241905 with complete diagnostic
capture. Only if the cause is resolved may H3G freeze candidate-specific
authority safety, prove focused fixtures, disabled parity, replay, and then
run the newly frozen selector-enabled R0, actual R1/S16 seed 57531938, and
the exact sealed H3D holdouts in the directive's gated order.

H3F evidence is historical and preserved. No retry of H3F, formal D-014,
D-013/AX, production-default selector authority, hidden-truth policy,
threshold/effect changes, storage changes, or H3D holdout regeneration is
authorized. Permanent H3G evidence:
/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/d014h3g-candidate-safety-selector-r1/

## UMBRA-D-014H3G terminal routing

D-014H3G performed one bounded R0/S0 seed 41241905 reproduction using
unchanged H3F selector behavior. The organism completed 7,200 ticks without
reproducing the historical unsafe-selector assertion. Terminal verdict:
D014H3G_UNSAFE_SELECTION_CAUSE_UNRESOLVED. The H3F causal envelope was not
obtained; no root-cause category, candidate-safety alignment, selector
population, known R1, or holdout result is claimed. No H3F retry occurred.

Permanent H3G evidence:
/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/d014h3g-candidate-safety-selector-r1/

## UMBRA-D-014H3F terminal routing

D-014H3F corrected the HabitatEngine snapshot-authority boundary and passed
the persistence, reattachment, disabled-parity, H3B R2 restart, R2/R3
preflight, and focused validation gates. Its single R0 population invocation
then stopped on seed 41241905 with
RuntimeError: d014h3d_selector_selected_unsafe_candidate at
umbra_core/runtime.py:1828 before a result envelope was persisted.

Terminal verdict: D014H3F_EXECUTION_STOP_UNRESOLVED. No scientific viability
result is claimed. No retry, reseed, known-R1, holdout, formal D-014, or
follow-on directive is implied. Permanent H3F evidence:
 /srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/d014h3f-habitat-restart-selector-robustness-r1/

## UMBRA-D-014H3E active routing

D-014H3D is terminal and accepted as partial causal-mechanism evidence with
verdict D014H3D_EXECUTION_STOP_UNRESOLVED. Its disabled-hook parity,
causal-injection, real-selector-divergence, replay, and H3D-enabled R0 8/8 x
7,200 results remain valid. The reported H3D known-R1 result is permanently
reclassified as seed 57531938 under S0, not R1/S16; its historical artifact is
not rewritten.

D-014H3E is the sole active directive from exact baseline
04fc267213aedb7f7e50185c9103a727075e2a8f. It must first correct regime
fidelity (R0=S0, R1=S16, R2=S10 with H3B lifecycle, R3=S12 with the frozen
body swap) and selector-input/proposal-capture fidelity. The unchanged H3D
selector semantics should be reused where its contract is sufficient. Freeze
the complete H3E contract and runner before organism outcomes; then require
H3E R0 8/8 x 7,200 and actual R1/S16 seed 57531938 x 7,200 before opening
the carried-forward sealed H3D holdouts.

No production-default selector authority, formal D-014, D-013/AX, retry,
reseed, threshold/effect change, storage change, or H3D historical rewrite
is authorized. Permanent H3E evidence is:
/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/d014h3e-regime-faithful-integrated-selector-r1/

## UMBRA-D-014H3D terminal routing

D-014H3D completed the frozen selector-completeness and causal-injection
gates from baseline f054f24af0d5847f3d4b96270184f72d09fdbf41. R0 passed 8/8
at 7,200 ticks and known R1 seed 57531938 passed at 7,200 ticks with the
experiment-only selector enabled, exact Governance to VerifiedOutcome
lineage, zero post-selection replacements, and no production-default
selector authority.

The fresh 3xR1/R2/R3 holdout manifest was sealed before outcomes, but the
frozen runner exposes no holdout execution mode and the frozen runtime only
defines the S0 population. It therefore cannot execute the required R2
H3B social lifecycle or R3 frozen body-change schedule without changing the
scientific harness after freeze. Terminal verdict:
D014H3D_EXECUTION_STOP_UNRESOLVED.

No fresh holdout outcomes, integrated robustness conclusion, formal D-014,
formal tag, D-013/AX work, retry, reseed, or production qualification claim
was made. H3C evidence and the invalid two-per-regime manifest remain
historical and unchanged.

Permanent evidence:
/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/d014h3d-causal-integrated-selector-r1/

 routing

D-014H3C stopped at the required known-R1 predecessor gate from exact starting
baseline 5c18693283fc48bef738bd1e0ca5fad678ce211a. Fixed R0 passed 8/8 x 7,200;
known R1 seed 57531938 reproduced fatigue failure at tick 372. Fresh sealed
holdouts were not executed. The evaluator-only shadow contract passed focused
tests, but no selector outcome or organism rescue is claimed.

Evidence: /srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/d014h3c-integrated-affordance-competition-r1/
Return to Architect. No D-014I, formal D-014, D-013/AX, or production selector
integration is inferred.

## UMBRA-D-014H3H active routing

D-014H3H is authorized from exact baseline
b2435089ccf11e3c3e354443115ee61934003aff after accepted H3G terminal
verdict. H3G's non-reproduction remains historical and does not establish a
cause for H3F. H3H must first audit behavioral candidate identity, exact
authority-effect branches, actual proposal capture, and existing endogenous
candidate scores, then freeze a fresh non-production selector contract before
any gated R0/R1/holdout outcomes.

The original H3D holdout manifest remains sealed, exact, and unexecuted.
Canonical H3H evidence:
/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/d014h3h-deterministic-authority-safe-selector-r1/

No production-default selector authority, threshold/effect changes, retries,
reseeds, storage migration, formal D-014, D-013/AX, or holdout regeneration
is authorized.
