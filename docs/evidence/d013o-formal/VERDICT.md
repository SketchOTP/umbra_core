# UMBRA-D-013O formal result

- Execution ID: `d013o-formal-26cd2f8-001`
- Baseline: `26cd2f81e343772cb797f5d31fbaf30e918aace7`
- Runner starting-commit argument: `26cd2f8`
- Formal tag: `umbra-d013o-v2-formal-baseline-26cd2f8`
- Contract: `P0_RECOVERY_CONTRACT_V2`
- Active runtime: `150.1428255396895` seconds
- Organism started: yes
- Run count: `1`
- Terminal verdict: `D013O_P0_INTEGRITY_FAIL`
- First failing invariant: `RECOVERY_INTEGRITY_FAILURE:physiology_integrity_or_critical_boundary`
- Failure tick: `270`

The single module-entrypoint invocation launched the organism and terminated
on the authoritative recovery/physiology fail-fast condition. The first
failure is preserved in `FIRST_FAILURE.json`; the complete physiology and
recovery traces are preserved alongside the runner evidence.

The run was not retried, restarted, remediated, or changed after launch. This
is a valid organism-level integrity failure, not a preflight or invocation
failure. It does not qualify integrated P0 viability.
