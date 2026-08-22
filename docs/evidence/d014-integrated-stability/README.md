# D-014 current-stack integrated stability qualification

Verdict: `UMBRA_D014_PHYSIOLOGICAL_VIABILITY_FAIL`

The single authorized formal invocation used execution ID
`d014-integrated-stability-r1` and stopped at the first genuine scientific
failure. Five R0 runs completed 7,200 ticks. R0 seed `41241905` failed at tick
813 when fatigue reached `0.9525000000000022`, above the existing critical high
boundary `0.95`, after a verified failed REST outcome (`reason=not_at_rest`).

The matrix therefore contains 6/32 attempted rows, 5 complete and 1 failed;
the remaining 26 rows were not invoked. No retry, reseed, remediation,
production change, threshold change, or continuation occurred. The real-time
resource soak was not run after the scientific failure.

Evidence: `/mnt/storage1tb/project-archives/UMBRA-CORE/live-evidence/d014-integrated-stability-r1/`.
The tracked pointer is `docs/evidence/d014-integrated-stability/README.md`.

Notion closeout was not updated in this session because no Notion connector was
available.
