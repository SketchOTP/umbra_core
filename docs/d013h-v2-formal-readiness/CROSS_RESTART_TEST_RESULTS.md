# Cross-restart results

- Pathological cross-restart retry retained the denial episode and produced
  `RECOVERY_FAILED`.
- Corrective cross-restart recovery retained context and produced
  `VERIFIED_RECOVERY_SUCCESS`.
- A mismatched execution ID was rejected fail-closed while loading evaluator
  context.

All cases are `NON_FORMAL_TEST`; no formal worker campaign was launched.
