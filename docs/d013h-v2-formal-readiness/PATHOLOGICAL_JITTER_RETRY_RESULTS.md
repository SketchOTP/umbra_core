# Pathological jitter retry

Scenario:

`SAFE_DENIAL` → new observation ID/time and ordinary distance jitter → no
corrective action → same blocked CHARGE retry.

Result: `RECOVERY_FAILED`.

The retry does not escape the evaluator because provenance novelty is not
material novelty.
