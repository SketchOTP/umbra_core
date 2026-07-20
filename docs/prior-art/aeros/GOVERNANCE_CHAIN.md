# Governance chain

```
intent → admission → policy → contract → runtime_safety → override → execution → outcome_verification → audit
```

Final decisions: ALLOW | DENY | DEFER | REQUIRE_OPERATOR | FAIL_CLOSED.

Upstream AEROS: policy engine + runtime gateway (AGPL). Independent harness reproduces contracts without LLM.

**Note:** upstream policy evaluator defaults ALLOW when no rule matches — UMBRA should **fail closed** for unknown capabilities.
