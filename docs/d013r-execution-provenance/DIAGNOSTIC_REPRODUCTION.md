# D-013R diagnostic reproduction

The immutable D-013Q `RECOVERY_TRACE.jsonl` was replayed without changing the
formal evidence. At tick 120 the row contains:

| field | value |
|---|---|
| `selected_candidate` | `CHARGE` |
| `executed_capability` | `REST` |
| governance capability | `REST` |
| verified outcome capability | `REST` |
| verified success | `false` |
| verified reason | `not_at_rest` |

The pre-correction `classify_attempt()` selected `selected_candidate` before
the verified capability and therefore interpreted the attempt as `CHARGE`,
producing `denial_reason_not_authoritative`. The embodiment denial is valid
for REST; the evaluator misidentified the action.

The frozen D-013Q verdict remains permanently
`D013Q_P0_INTEGRITY_FAIL`.
