# UMBRA-D-002 Final Verdict

**Verdict:** `UMBRA_D002_SENSORIMOTOR_SELF_MODEL_QUALIFIED`

**Starting commit:** `60de076e8f4fc5c8f73ef2cc98750b3036e06dea`  
**Date:** 2026-07-21  
**Mimir project:** `7777645d52a91b49`  
**Mimir task:** `17d78c89af9c4e11ad0597d4005b0993`

## Gate summary

| Gate | Result |
|---|---|
| 0 D-001 seal | PASS |
| 1 Prediction | PASS |
| 2 Attribution | PASS |
| 3 Body-change | PASS |
| 4 Adaptation | PASS |
| 5 Identity | PASS |
| 6 Replay | PASS |
| 7 Regulation | PASS (1.00) |
| 8 Governance | PASS |
| 9 Performance | PASS |
| 10 Scope | PASS |
| 11 Tests | PASS |

## Key metrics

- C0_I1 early→late body error: 0.1473 → 0.0751
- C0_I8 external attribution mean: 0.98; false-self: 0.0
- C0_I0 mean supersessions (false-change proxy): 0.09
- Soak: duration=7200.356724877027s CPU=0.3248499183684469% RSS_p95=29.49609375 MiB slope=0.0 MiB/h
- 100k RSS_p95=29.38671875 MiB restart_continuity=True

## Scientific claim authorized

A narrow non-LLM sensorimotor self-model can learn body action consequences, distinguish self-caused from external displacement without world truth, detect persistent body changes without treating isolated noise as body change, adapt predictions after body change while preserving `agent_id`, and remain compatible with D-001 regulation under the stated bounds.

## Claims not authorized

Complete self-awareness; consciousness; general world understanding; personality; emotion; relationship; complete companion.

## D-003

**Authorized:** YES
