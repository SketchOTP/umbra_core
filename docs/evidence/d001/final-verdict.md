# UMBRA-D-001 Final Verdict

**Verdict:** `UMBRA_D001_INVARIANT_COMPANION_CORE_QUALIFIED`

**Starting commit:** `813b9d6a3f1cbee159d0e421bf745a2039626dcf`  
**Foundation commit:** `e9fed18ec8c1a72db05b2efe6d93502a2ba6d7c9`  
**Retention-v1 / Run B commit:** `8d68995d114504e1265eef1941a0b46588b0893e`  
**Seal commit:** `8653381ad6b41ad1153f781266df582fc1a46215`  
**Date:** 2026-07-21  
**Mimir project:** `7777645d52a91b49`  
**Mimir tasks:** D-001 `32cbec622ee34877977ba95ff10becf8` (closed); D-001C `a9d8858e78824663ae88103cf735c025` (closed at seal)

## Gate summary

| Gate | Result | Notes |
|---|---|---|
| 0 Governance | PASS | Mimir resolved; architecture intact |
| 1 Identity | PASS | Restarts preserve agent_id; corruption fail-closed |
| 2 Persistence/replay | PASS | Birth/snapshot match; hash/sequence validation |
| 3 Causal physiology | PASS | Interventions change actions; ablations underperform |
| 4 Autonomous regulation | PASS | Recovery rate 1.0 across matched trials |
| 5 Satiation/competition | PASS | Seeking declines after correction |
| 6 Embodiment | PASS | Policy lacks world truth; body-dependent actions |
| 7 Governance | PASS | Denials; bypass fail-closed; outcomes verified |
| 8 Autonomous existence | PASS | No user/LLM/network in loop |
| 9 Performance | PASS | Run B 6h soak: duration, CPU, RSS p95, RSS slope ≤1, DB bounded |
| 10 Scope | PASS | No memory/planning/LLM/UI/robotics modules |
| 11 Seal | PASS | Run B closeout + 45/45 tests (0 skips); evidence committed |

## Gate 9 — Run B (qualifying)

Retention policy: `v1_authoritative_every_tick`  
Provenance: `docs/evidence/d001/soak-run-b-provenance.json`  
Closeout: `docs/evidence/d001/soak-run-b-closeout.json`

| Metric | Value | Gate |
|---|---|---|
| Duration | 21600.15 s | ≥ 6h |
| Ticks | 43177 | — |
| CPU mean | 0.147% | ≤ 5% |
| RSS p95 | 27.79 MiB | ≤ 200 |
| RSS slope (full window) | 0.557 MiB/h | ≤ 1 |
| DB size | 69.5 MiB | ≤ 1 GiB |
| Drift / tick | 1.0 | ≈ 1 |
| Gov / tick | 1.0 | ≈ 1 |
| Ledger / restart / snapshot | PASS | — |

## Run A (non-qualifying)

Retention v0 performance-only / **negative** RSS-slope evidence (`~1.33 MiB/h`). Not used to offset Run B. DB under `/tmp` was absent at closeout (no restart/replay from Run A).

## Scientific claim authorized

A minimum persistent non-LLM companion core with constitutional identity, vector physiology, uncertain perception, embodied primitives, vector arbitration, governed execution, and SQLite WAL replay can regulate under matched disturbances, meet the 6h performance budget under authoritative-every-tick retention, and outperform random/scripted/ablated controls — without personality, language, or advanced memory.

## Claims not authorized

Living organism; consciousness; genuine emotion; personality; relationship; learning; complete companion.

## D-002

**Authorized** to begin when opened under `UMBRA_D001_INVARIANT_COMPANION_CORE_QUALIFIED`. Not started by this seal.
