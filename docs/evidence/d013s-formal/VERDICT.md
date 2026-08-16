# UMBRA-D-013S formal verdict

## Terminal result

`D013S_P0_INTEGRITY_FAIL`

Exactly one formal V2 invocation was executed from annotated baseline tag
`umbra-d013s-v2-formal-baseline-0586057`, targeting
`05860573b141323640c78419a6ddae3736e9473a`. The runner argument was
`--starting-commit 0586057` and the execution ID was
`d013s-formal-0586057`.

The organism started and terminated at active runtime `230.24413538817316`
seconds with the exact first failure:

`RECOVERY_INTEGRITY_FAILURE:physiology_integrity_or_critical_boundary`

The failure occurred at tick 414. The authoritative first-failure artifact is
`FIRST_FAILURE.json`; the complete recovery evaluator chronology is in
`P0_RECOVERY_EVALUATION_TRACE.jsonl`, with physiology and recovery traces
preserved separately.

## Observed state at fail-fast

- minimum and terminal energy: `0.04849999999999971`
- minimum fatigue: `0.20800000000000002`; terminal fatigue: `0.8045000000000009`
- minimum integrity: `0.8976000000000003`; terminal integrity: `0.9794000000000023`
- minimum stimulation: `0.2319999999999998`; terminal stimulation: `0.31299999999999983`
- critical boundary crossed: `true`
- selected/executed/governance/verified capability at failure: `APPROACH`
- identity preserved: `true`
- persistence/read-only validation: `PASS`
- process cleanup: `PASS`

The failure is a valid organism-level integrity/critical-boundary failure. It
does not qualify integrated P0 viability. No historical verdict is superseded.
