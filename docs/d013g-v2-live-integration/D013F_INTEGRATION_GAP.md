# D-013F integration gap

D-013F validated the evaluator as a standalone component, but `run_formal_p0.sample()` still consumed the worker's V1 `formal_failure` file before V2 adjudication could occur.

The worker also had no live derivation for observation signatures, new evidence, corrective action, or recovery-blocked state. D-013G closes those two harness gaps without changing organism decisions.
