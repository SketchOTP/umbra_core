# UMBRA-D-013Q formal verdict

## Terminal result

`D013Q_P0_INTEGRITY_FAIL`

Exactly one formal V2 invocation was executed from annotated baseline tag
`umbra-d013q-v2-formal-baseline-0d2ace2`, targeting
`0d2ace2c18eee818c8a2c5d4f182273e961423b7`. The runner argument was
`--starting-commit 0d2ace2` and the execution ID was
`d013q-formal-0d2ace2`.

The run started the organism and terminated at active runtime
`70.10386792896315` seconds with the exact first failure:

`RECOVERY_INTEGRITY_FAILURE:denial_reason_not_authoritative`

The failure occurred at tick 120. The authoritative first-failure artifact is
`FIRST_FAILURE.json`; the complete recovery evaluator chronology is in
`P0_RECOVERY_EVALUATION_TRACE.jsonl`.

## Observed state at fail-fast

- minimum energy: `0.2945000000000009`
- terminal energy: `0.2945000000000009`
- minimum fatigue: `0.20800000000000002`
- terminal fatigue: `0.5675`
- minimum integrity: `0.8976000000000003`
- terminal integrity: `0.9978000000000002`
- minimum stimulation: `0.2509999999999998`
- terminal stimulation: `0.2509999999999998`
- critical boundary crossed: `false`
- identity preserved: `true`
- persistence/read-only validation: `PASS`
- process cleanup: `PASS`

The formal failure was an integrity failure before integrated viability could
be positively qualified. No D-013L repeated-denial loop was observed before
the fail-fast point, and no D-013O critical-boundary failure recurred before
the fail-fast point; neither historical verdict is superseded.

## Scientific boundary

This result does not qualify integrated P0 viability. It does establish a
valid single-run D-013Q integrity failure under the frozen V2 contract.
D-013L remains `D013L_P0_INTEGRITY_FAIL`, D-013N remains
`D013N_FORMAL_RUN_INVALID`, D-013O remains `D013O_P0_INTEGRITY_FAIL`, and
D-010 remains the historical performance/inventory failure.
