# UMBRA-AS-012 — Exact-entrypoint boundedness, soak, and causal closure

Baseline: `b4cc014c3545e19fa0e755407fe2a466e23e72a5`

Permanent predecessor: `AS011_PROTOCOL_FAIL`.

Scope is experiment/test/evidence/governance only. The inherited AS-010
full-configuration population `32/32` and lifecycle PASS are not rerun.

Open gates:

- exact-entrypoint preflight for boundedness, soak, and all four ablations;
- one fresh 100000-tick boundedness run;
- frozen real-time soak;
- one matched-seed R1/S16 causal ablation set.

Production semantic change, historical evidence rewrite, post-lock repair,
retry, reseed, and automatic CLOSE-03 are prohibited.
