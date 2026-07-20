# UMBRA-D-001 Final Verdict

**Verdict:** `UMBRA_D001_PARTIAL_FOUNDATION`

**Starting commit:** `813b9d6a3f1cbee159d0e421bf745a2039626dcf`  
**Ending commit:** `cc174daa6a1b1c2163bbff0e6c89585124b360d8`  
**Date:** 2026-07-20  
**Mimir project:** `7777645d52a91b49`  
**Mimir task:** `32cbec622ee34877977ba95ff10becf8` (closed v3)

## Gate summary

| Gate | Result | Notes |
|---|---|---|
| 0 Governance | PASS | Mimir resolved; D-001 only active; architecture intact |
| 1 Identity | PASS | 100/100 restarts preserve agent_id; corruption fail-closed |
| 2 Persistence/replay | PASS | Birth replay match; snapshot match; hash/sequence validation |
| 3 Causal physiology | PASS | Interventions change actions; C3/C4 underperform C0 |
| 4 Autonomous regulation | PASS | Recovery rate 1.0 across 500 matched trials (≥95%) |
| 5 Satiation/competition | PASS | Seeking declines after correction; no fixed need monopoly |
| 6 Embodiment | PASS | Policy lacks world truth; body-dependent actions |
| 7 Governance | PASS | Denials; bypass fail-closed; outcomes verified |
| 8 Autonomous existence | PASS | No user/LLM/network in loop |
| 9 Performance | PARTIAL | 100k ticks + RSS p95≤200 + CPU≪5% at 2 Hz short soak; **6h soak still RUNNING** |
| 10 Scope | PASS | No memory/planning/LLM/UI/robotics modules |
| 11 Seal | PARTIAL | Evidence present; 6h soak incomplete → not QUALIFIED |

## Why not QUALIFIED

Gate 9 requires a completed 6-hour real-time soak. Soak process is running (`docs/evidence/d001/soak-6h.jsonl` → summary on completion). Short 180s soak already shows CPU ~0.1% of one core and flat RSS ~39 MiB.

## Scientific claim authorized

A minimum persistent non-LLM companion core with constitutional identity, vector physiology, uncertain perception, embodied primitives, vector arbitration, governed execution, and SQLite WAL replay can regulate under matched disturbances and outperform random/scripted/ablated controls — without personality, language, or advanced memory.

## Claims not authorized

Living organism; consciousness; genuine emotion; personality; relationship; learning; complete companion.

## D-002

**Not authorized** until `UMBRA_D001_INVARIANT_COMPANION_CORE_QUALIFIED` after completed 6h soak seal.
