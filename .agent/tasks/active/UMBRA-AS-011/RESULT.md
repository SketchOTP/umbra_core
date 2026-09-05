# UMBRA-AS-011 — terminal result

Verdict: `AS011_PROTOCOL_FAIL`.

The exact frozen boundedness command (Process Job `job-mtogx0pk-4c4dc451`) exited
with code `1` at `experiments/as011/downstream.py:98` because `bounded` was not
defined. The failure occurred before `initialize()` returned, so organism creation,
loading, and ticks were all `0`. No retry or reseed occurred.

Valid inherited evidence remains AS-010 full-config population `32/32` and lifecycle
PASS at `500` ticks. AS-011 Phase 0 and finalization preflight passed, but the fresh
boundedness run, real-time soak, and causal ablation are unqualified. Production and
existing-test semantic deltas are `0`; CLOSE-03 remains blocked and no successor
started.
