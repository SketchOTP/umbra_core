# UMBRA-D-014H2 plan

1. Inspect the runtime and freeze the trace schema before live qualification.
2. Use the least invasive observer seam; prove disabled/enabled parity and
   deterministic replay.
3. Translate real rows through unchanged H1 and proceed only through gates
   explicitly authorized by H2.

Fail closed on incomplete source coverage, parity drift, replay mismatch, or
unexplained live translation.
