# UMBRA-D-013L formal result

- Execution ID: `d013l-formal-ff67b87-001`
- Baseline: `ff67b87746392b75c087572b90d3d4e5f6950368`
- Runner starting-commit argument: `ff67b87`
- Contract: `P0_RECOVERY_CONTRACT_V2`
- Active runtime: `80.14683919772506` seconds
- Organism started: yes
- Run count: `1`
- Runner terminal verdict: `D013L_P0_INTEGRITY_FAIL`
- First failing invariant: `RECOVERY_FAILED:repeated_denial_without_new_evidence_or_correction`
- Failure tick: `139`

The run was validly launched and terminated on the authoritative fail-fast
recovery invariant. No retry, second seed, remediation, or code change was
performed. Integrated P0 viability is not revalidated by this run.
