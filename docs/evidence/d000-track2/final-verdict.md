# Final verdict — UMBRA-D-000 Track 2

```text
UMBRA_D000_TRACK2_PARTIAL_MECHANISM_QUALIFICATION
```

## Why this verdict

- **Qualified:** vector internal state, viable ranges, autonomous drift, drive-reduction learning signal, satiation, competition, interoceptive policy access, physiology/policy separation, overshoot-sensitive drive (formal causal gates pass).
- **Partial / blocked:** full Yoshida MuJoCo/PFRL embodied runtimes did not execute; anticipation is a minimal forward-model proxy (not full CTCS-HRRL learning); continuous-time paper stack UNRESOLVED as executable prior art.
- **Not a failure of causality:** deprivation, satiation, competition, autonomy, and ablations passed in the formal suite; Yoshida `homeostatic_shaped` equations smoked independently.

## Gates (summary)

| Gate | Status |
|---|---|
| 0 Governance | PASS (Mimir resolve + context; D-001 blocked; GOAL hash unchanged; MicroPsi label corrected) |
| 1 Source integrity | PASS (pinned commits; license gaps recorded honestly) |
| 2 Formal correctness | PASS |
| 3–8 Causal | PASS (see causal-results.json / ablation-results.json) |
| 9 Upstream | PASS-with-block (attempts + source-derived run; full env blocked) |
| 10 Companion relevance | PASS (documented) |
| 11 Ledger | PASS |
| 12 Scope | PASS (no production kernel; no Track 3 open; D-001 blocked) |

## Track 3 authorization

**NO** — D-000 continues; operator/process opens Track 3 (Hexis) separately.  
**D-001 authorized: NO**
