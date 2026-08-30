# UMBRA-AS-003B result

Verdict: `AS003B_RETAINED_REPLAY_FAIL`

AS-003B froze exactly once at `5c2642ac9c1c0be6340d583caf594f5799ecda13`. The first preregistered retained replay produced `57 PASS / 1 FAIL`. The failed assertion was `tests/test_close02r_hierarchical_intent.py::test_no_intent_preserves_base_affordance_arbitration`: expected `INSPECT`, observed `ORIENT`.

The frozen protocol terminates on this failure. No Diagnostic A/B, organism execution, frontier mechanism analysis, comparator, subsystem/full suite, production/test modification, retry, reseed, known R1, fresh population, AS-004, or CLOSE-03 followed. This result does not classify the assertion as an AS-003 regression, an inherited baseline failure, or an AS-002 contract rejection.
