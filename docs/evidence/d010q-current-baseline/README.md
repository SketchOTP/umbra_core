# UMBRA-D-010Q — Current-Baseline Temporal Continuity Requalification

- Baseline: `0d3234002a9ddd49fe31a226e2943c2ecf5552bf`
- Execution: `d010q-current-baseline-r1`
- Verdict: `UMBRA_D010_PERFORMANCE_FAIL`
- External dossier: `/mnt/storage1tb/project-archives/UMBRA-CORE/live-evidence/d010q-current-baseline-r1/`

## Result

The current-baseline functional generation completed exactly 1,900/1,900
rows with Gates 0–12 passing. The accelerated 100,000-tick boundedness and
restart check passed. The required S3 performance sequence then stopped
fail-closed before renderer-lifecycle execution because Atlas lacks
`libtk8.6.so` / `python3-tk`. P0, P1, and P2 were not executed; no dependency
installation, retry, seed substitution, or second generation occurred.

This is a truthful D-010Q qualification failure, not a current Gate-13 pass.
Historical `UMBRA_D010_PERFORMANCE_FAIL` remains permanent evidence and was not
rewritten. The D-010Q runtime inventory rebound the stale historical registry
to 42 current source sites without changing production semantics or historical
artifacts.

## Validation and integrity

- D-010 focused suite: 129 passed.
- D-001–D-009 and D-011 compatibility suite: 512 passed, 2 skipped.
- Path-safe full suite: 868 passed, 2 skipped.
- D-009 validator: PASS.
- D-010 validator: PASS.
- Authority 3.0: PASS.
- Governance: PASS.
- Production source, historical evidence, thresholds, protected records, and
  formal tags: unchanged.

See the external dossier for the frozen contract, protocol equivalence,
configuration hashes, raw functional ledger, accelerated result, terminal
failure, validation results, resource accounting, and evidence hashes.
