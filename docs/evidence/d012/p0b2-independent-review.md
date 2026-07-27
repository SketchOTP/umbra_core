# UMBRA-D-012B2 Pre-launch Read-only Review

## Verdict

`APPROVE`

This was a distinct read-only review pass after implementation, performed in
the same Codex session because no delegated reviewer was authorized. It is not
represented as an external human review.

## Findings

- The preserved P0 ledger and B1 timeline locate the failure at ticks 185–191:
  admitted `CHARGE` attempts failed `not_at_resource` after approach stopped at
  the former 2.2 arbitration boundary.
- Commit `fc68540` changes one production comparison from 2.2 to 1.5. That
  matches the existing embodiment execution boundary; it does not weaken the
  frozen `energy >= 0.05` viability criterion.
- `p0-formal-config.json` and `opportunity-schedule.json` retain hashes
  `bbb8c180...` and `fc6101bd...`; event order and 20/30/60-minute policy are
  unchanged.
- The S1 additions are observation and fail-fast controls only: per-tick
  physiology/recovery evidence is written by the worker, and a triggering
  failure blocks the next tick before supervisor cleanup.
- The original P0 verdict, original hash bundle, B1 hash bundle, and
  `.agent/RECORD.md` retain hashes `4a13107f...`, `e787c316...`, `32570943...`,
  and `a0d61b22...`.
- Pre-launch regression: 182 passed across D-012, D-001, D-009, and D-011.
  Governance validation, frozen schedule validation, and `git diff --check`
  passed.
- D-010 remains disabled. P1, P2, D-012C, real devices, direct harness state
  mutation, and further remediation are outside the launch.

The repair addresses the proved root cause, preserves prior qualified behavior,
and supplies the per-tick evidence needed for the single authorized rerun.
