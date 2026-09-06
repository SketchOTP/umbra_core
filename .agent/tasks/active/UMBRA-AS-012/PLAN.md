# UMBRA-AS-012 — Exact-entrypoint boundedness, soak, and causal closure

Baseline: `b4cc014c3545e19fa0e755407fe2a466e23e72a5`

Permanent predecessor: `AS011_PROTOCOL_FAIL`.

Scope is experiment/test/evidence/governance only. The inherited AS-010
full-configuration population `32/32` and lifecycle PASS are not rerun.

Terminal boundary:

- exact-entrypoint preflight passed;
- one frozen boundedness run reached 100000 ticks but failed during result publication;
- soak and matched causal ablation did not run.

Production semantic change, historical evidence rewrite, post-lock repair,
retry, reseed, and automatic CLOSE-03 remain prohibited.
