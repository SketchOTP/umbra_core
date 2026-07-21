# UMBRA-D-002V Final Verdict

**Verdict:** `UMBRA_D002V_PERFORMANCE_FAIL`

**Starting commit:** `a60b9258135867fed63e58109243043162142c3e`  
**Ending commit:** `5a82b580adf035b88acbdea3f6f8a63f9a55e672`  
**Date:** 2026-07-21  
**Mimir project:** `7777645d52a91b49`  
**Mimir task:** `74b43bba377d4c4f85245eb62ad26018`

## Parent seal status

D-002 functional verdict `UMBRA_D002_SENSORIMOTOR_SELF_MODEL_QUALIFIED` remains on record as **provisionally qualified pending validation**. This directive does **not** retract sensorimotor behavior evidence; it fails the preregistered current-VmRSS full-window Gate1.

## Gate summary

| Gate | Result |
|---|---|
| 0 Seal integrity (D-002 evidence hashes / architecture) | PASS |
| 1 Performance (current VmRSS full-window OLS) | **FAIL** — slope 1.052 MiB/h > 1.0 |
| 2 Event authority | PASS |
| 3 Replay | PASS |
| 4 Regression (zero failures / skips) | **FAIL** — 1 failed (`test_full_window_rss_slope_passes`), 84 passed |
| 5 Seal | see ending commit |

## Performance (frozen method)

- Method: `/proc VmRSS`, sample every 10s, full-window OLS, no warmup exclusion, no outlier rejection
- Duration: 7200.18 s
- CPU mean: 0.277% of one core
- RSS p95: 29.54 MiB
- RSS slope: **1.052 MiB/h** (threshold ≤ 1.0)
- Database: 44.74 MiB
- Crash-free / ledger / restart identity: yes
- Diagnostic (not Gate1): hour0–1 OLS ≈ 2.26 MiB/h; hour1–2 OLS ≈ 0.44 MiB/h

## Event authority

- AUTHORITATIVE: body_model_supersession, capability_degradation, capability_dormancy
- DERIVABLE: action_prediction, body_change_evidence
- DIAGNOSTIC (sampled every 10 ticks): prediction_error, self_attribution
- Bounded history: predictions/errors/attributions ≤ 256; change evidence ≤ 64; supersessions ≤ 32

## Replay

- Birth resimulation matches snapshot self-model hash / supersessions / affordances
- Missing authoritative mid-chain event and corrupted snapshot hash fail closed

## D-003

**Authorized:** NO

Blocking: Gate1 full-window current-VmRSS slope exceeds 1 MiB/h under frozen method.
