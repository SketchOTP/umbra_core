# UMBRA-AS-012 — terminal result

Verdict: `AS012_PROTOCOL_FAIL`.

The exact frozen boundedness entrypoint ran one fresh full-configuration
organism through `100000` ticks. It then failed during result publication at
`experiments/as012/downstream.py:331` because `Path.open("xb", encoding=...)`
is invalid. The result artifact was not published, so boundedness is not
qualified. The retained metric journal ends at tick `100000` with `521154`
events; it is preserved as protocol evidence, not promoted to a qualification
result.

No retry or reseed occurred. Real-time soak and causal ablation did not run.
Production delta is `0`. AS-010 full-configuration population `32/32` and
lifecycle PASS remain valid inherited evidence. Integrated viability and
CLOSE-03 remain unqualified and blocked. No successor started.
