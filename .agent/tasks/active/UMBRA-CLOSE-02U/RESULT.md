# UMBRA-CLOSE-02U terminal result

Status: TERMINAL / returned to Architect

Verdict: `CLOSE02U_KNOWN_R1_FAIL`

Baseline: `d44b453ae2f091fb31f1498724ab16c1c0e02387`

The verified recovery-landmark implementation passed focused contract and
regression checks. Historical diagnostics A (`45878900`, 500 ticks) and B
(`22023239`, 3500 ticks) passed. The known R1/S16 diagnostic (`57531938`)
failed once at tick 1484 after `NO_SAFE_ACTION` at tick 1483, so the change
delayed but did not clear the fatigue failure.

The cloned runner executed the eight fresh R0 observations before the required
known-R1 gate. Those raw observations are retained but are not qualification
evidence. No fresh R1/R2/R3 or formal population ran after the first genuine
failure. No retry, reseed, remediation, or automatic successor is authorized.

Permanent evidence: `/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-close-02u-recovery-landmark-r1/`.
