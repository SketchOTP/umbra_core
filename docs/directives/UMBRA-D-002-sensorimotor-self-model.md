# UMBRA-D-002 — Develop the Sensorimotor Self-Model and Adaptive Body Schema

**Status:** ACTIVE  
**Parent:** UMBRA-D-001 `UMBRA_D001_INVARIANT_COMPANION_CORE_QUALIFIED`  
**Authorization:** D-002 AUTHORIZED: YES (Run B sole qualification evidence; Run A negative context only)

## Objective

Extend the qualified companion core with a narrow sensorimotor self-model that learns body capabilities, action consequences, self/external attribution, body-change detection, and adaptation — without identity change, LLM control, or a general world model.

## Entry gate

- D-001 seal commit `8653381` + note `405640b`
- 45 tests, 0 skips
- Clean worktree at start; starting SHA recorded in `docs/evidence/d002/d001-seal.json`

## Implementation map

| Concern | Location |
|---|---|
| Body schema / prediction / attribution / adaptation | `umbra_core/self_model/` |
| Plant interventions I0–I11 | `umbra_core/embodiment.py` |
| Loop integration | `umbra_core/runtime.py` |
| Tests | `tests/test_d002.py` |
| Experiments | `experiments/d002/` |
| Evidence | `docs/evidence/d002/` |

## Hard constraints

No LLM; no hardware; no world-truth in policy/attribution; no general world model; no social/personality/emotion; predictions cannot grant authority; body changes preserve `agent_id`.

## Allowed verdicts

See directive body / `docs/evidence/d002/final-verdict.md`.
