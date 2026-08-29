# UMBRA-CLOSE-02X — Prospective Recoverability Implementation Candidate

Status: TERMINAL — `CLOSE02X_KNOWN_R1_FAIL`
Classification: PRODUCTION IMPLEMENTATION + GATED INTEGRATED QUALIFICATION
Start baseline: `9b7a3c5232edffe7fcc00ff04c0e2dbd2f0b9b59`
Parent: `UMBRA-CLOSE-02W`
Parent verdict: `CLOSE02W_PROSPECTIVE_RECOVERABILITY_CONTRACT_SUPPORTED`

## Objective

Restore pre-V/U recovery behavior, implement the exact bounded candidate-relative per-dimension prospective recoverability contract using existing `HOMEOSTATIC_RECOVERABILITY_VIEW_V1`, freeze it, and execute the mandated diagnostics/development/formal gates in exact order.

## Hard boundaries

- UNKNOWN, absent evidence, and already-exhausted margin are neutral.
- The view evaluates only already-generated candidates and never executes or invents an action.
- No active/critical recovery change, planner, rollout, global scalar, hidden truth, source priority, new threshold/weight, retry, reseed, H3, D-013/AX, or automatic CLOSE-03.
- First genuine scientific or acceptance-gate failure terminates the generation.

## Evidence

`/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-close-02x-prospective-recoverability-r1/`
