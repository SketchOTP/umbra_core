# UMBRA-D-012B2 Formal P0 Verdict

## Verdict

`UMBRA_D012B_P0_INTEGRITY_FAIL`

Formal execution `d012-p0-s1-20260727T1624Z` was the single authorized
Supplement S1 rerun from frozen launch commit `bbb604e`. No relaunch occurred.

## First failure

The worker captured the first invalid physiological state at tick 181:

```text
energy before tick = 0.0525
selected recovery action = MOVE
verified outcome = success
energy after tick = 0.0485
critical lower bound = 0.05
```

The worker blocked the next tick immediately. The supervisor observed the
failure at 100.134 active seconds and completed cleanup without another
organism tick.

The B1 boundary alignment was present, but this execution never reached
`CHARGE`. Across 148 recovery-urgency ticks the selected recovery actions were
122 `MOVE`, 20 `REST`, and 6 `APPROACH`, with zero complete positive-energy
charge cycles. The available-resource distance at the triggering tick was
3.8042, so the corrected 1.5 charge boundary was not yet executable. This is
sufficient to fail viability and the required recovery-mechanism gate; this
directive does not authorize another diagnosis, fix, or rerun.

## Gate adjudication

- Gate 0 — PASS: read-only review `APPROVE`; Supplement S1 committed before launch.
- Gate 1 — PASS: clean entry, prior seals present, D-010 disabled, freeze hash matched, no live residue.
- Gate 2 — FAIL: energy crossed below 0.05 at tick 181.
- Gate 3 — FAIL: no urgency-to-positive-energy recovery cycle completed.
- Gate 4 — NOT PASSED: autonomous operation advanced through tick 181, then correctly stopped on viability failure.
- Gate 5 — NOT REACHED: controlled worker restart was scheduled after the fail-fast stop.
- Gate 6 — NOT REACHED: governed perception intake and adapter restart were scheduled after the fail-fast stop; durable raw payload count remained zero.
- Gate 7 — NOT REACHED: checkpoint and snapshot restart were scheduled after the fail-fast stop.
- Gate 8 — INCONCLUSIVE: nine pre-failure samples stayed within hard bounds, but the minimum resource window was not reached.
- Gate 9 — PASS: 182 focused/prior tests passed; full suite had only the frozen 79-error D-010 fingerprint; governance, schedule, and diff checks passed.
- Gate 10 — PASS: chain valid through sequence 731; no worker, socket, lock, ownership, or incomplete checkpoint remained; evidence hashes validate.

## Preservation and authorization

The original failed P0, B1 evidence, prior seals, and `.agent/RECORD.md` remain
unchanged. P1, P2, D-012C, additional remediation, and another P0 execution
remain unauthorized. D-012 remains active and unqualified.
