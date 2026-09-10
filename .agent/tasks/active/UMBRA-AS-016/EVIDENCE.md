# AS-016 evidence log

- Baseline reconciliation: local `HEAD` and `github/master` are
  `17859e03143b2278e612efeb3e96684f830b741f`.
- Retained R2 database copied to an isolated temporary forensic area with
  SHA-256 `3c94fa0c25f1b8eab95a58393e3c7a44c3183ed2340173f3f1cc46f53f1ab75e`;
  the original is untouched.
- The retained ledger records final denials and executed actions but not the
  candidate pool, ORIENT preflight, or rejected-candidate chain at tick 3537.
  Attribution of an ORIENT rejection in the formal seed is therefore
  insufficient.
- The retained R0 development failure is preserved separately in
  `AS016_R0_41616031_FAILURE_ATTRIBUTION_V1.json`: it establishes a one-step
  recovery-reserve false positive and does not claim a complete future route.
- Current AS-016 execution/regulation tests: `20 passed`; affected
  recovery/persistence/body lineage: `90 passed` twice.
- The post-repair excluded development surface completed R0--R3 at `4000/4000`.
  R2 exercised restart and authoritative partner occlusion/reappearance; R3
  exercised its body/profile transition. These are not formal qualification
  cases and their seeds are excluded from the formal manifest.
- The path-safe applicable suite is `1365 passed / 4 skipped / 7 failed`.
  All seven failed node IDs reproduce at the exact accepted baseline; candidate
  failures are `0`.
- Literal downstream CLI V2 passed lifecycle, boundedness, soak, and all five
  ablation variants with checkpoint/final-result readback. Literal population
  CLI preflight completed four `80`-tick development cases with durable
  per-case records.
- `test_close02x_prospective_recoverability.py` fails collection on the same
  accepted baseline because `prospective_recoverability_transition` is not
  exported or defined there; it is inherited collection debt, not an AS-016
  candidate result.
