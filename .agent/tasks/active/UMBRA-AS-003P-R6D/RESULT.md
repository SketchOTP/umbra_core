# UMBRA-AS-003P-R6D — terminal result

## Verdict

`AS003PR6D_ROUTE_EVIDENCE_DISTINCTION_WITHOUT_PRECEDENCE`

R6D is a zero-organism architecture and relation-reachability audit from exact
baseline `ae4a6ca8d3c24c482a4a7ec2db9ec75cf2669a37`. It preserves the R6
`l2_precedes()` implementation and R6C's MAY-only route semantics. No production,
existing-test semantic, R6C, R6B-R1, AS-003L, or AS-002 behavior was changed.

## Finding

Finite verified route experiences are existential `MAY` witnesses. They establish
that a recorded route schedule is possible, but do not establish route-space
exhaustiveness, a future minimum or maximum, recurrence, or universal failure.
Consequently, when a known route witness misses a deadline, the open-world result
is `SCHEDULE_UNKNOWN`, not `NO_COMPLETE_SCHEDULE`.

The locked L2 relation therefore produced meaningful non-authoritative route
evidence distinctions (`COMPLETE_MAY_SCHEDULE` versus `SCHEDULE_UNKNOWN`) but no
route-causal precedence under lawful open-world semantics. The 96 route-causal
positives in the symbolic matrix occur only in the explicitly diagnostic
closed-world projection and are not authority evidence.

## Quantitative reachability result

- deterministic symbolic configurations: `1152`;
- `l2_precedes == true` overall: `960`;
- open-world `l2_precedes == true`: `432`, all non-route-causal or hard-authority cases;
- route-causal open-world precedence: `0`;
- route-causal closed-world diagnostic precedence: `96`;
- `COMPLETE_MAY` versus `SCHEDULE_UNKNOWN` distinctions: `96`;
- non-route-causal precedence: `288`;
- cases preempted by hard authority: `576`;
- retained seven-tick witness: fitting deadline → `COMPLETE_MAY`; missed deadline → `SCHEDULE_UNKNOWN`.

The R7 target disposition is `R7_ONLY_EVIDENCE_DISTINCTION_REACHABLE`; its
currently specified precedence target is not justified, so R7 was not started.

## Integrity accounting

- production delta: `0`;
- existing-test semantic delta: `0` (one additive pure R6D test module);
- organism creation/load/ticks: `0/0/0`;
- control/shadow/diagnostic/qualification runs: `0/0/0/0`;
- retries/reseeds: `0/0`;
- final pre-analysis pure runs: `9/9 PASS` twice;
- Authority 3.0: `PASS`;
- Governance: `PASS`;
- `git diff --check`: `PASS`;
- no successor started.

Pure runs 1–2 and 3–4 remain retained as append-only development records. Runs
1–2 exposed an incorrect expected matrix cardinality; the correction was recorded
before detailed attribution. Runs 5–6 are the final corrected 9/9 results.

## Evidence

Evidence root:

`/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003p-r6d-may-route-l2-reachability-r1/`

The root contains the state reconciliation, immutable open-world contract, closed/open
comparison, necessary conditions, symbolic reachability matrix, route-causality and
ablation analyses, retained-witness probe, R7 disposition, pure-run records, and
final manifest with SHA-256 readback inventory.

## Handoff

R6D does not authorize a live R7 pair and does not modify AS-003L, AS-002, or the
action-selection path. A future relation-design stage would need to decide whether
non-authoritative schedule evidence should remain a research distinction or whether
an independently justified, sound relation with a different loss semantics is
required. No automatic successor is authorized.
