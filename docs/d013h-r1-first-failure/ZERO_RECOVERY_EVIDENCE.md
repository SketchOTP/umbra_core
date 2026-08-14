# Zero-recovery evidence

The valid early-termination state is:

```yaml
evaluation_trace_records:
  init: 1
  recovery_evaluations: 0
```

The init-only trace is sufficient evidence of evaluator initialization for the
exact campaign. It is not a viability pass and does not fabricate a recovery
attempt.

Focused test coverage publishes the init-only V2 trace successfully.
