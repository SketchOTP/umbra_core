# UMBRA-D-004 — Intrinsic Play, Skill Practice, and Autonomous Curriculum

**Status:** ACTIVE  
**Depends on:** `UMBRA_D003_PREDICTIVE_WORLD_MODEL_QUALIFIED`  
**Blocks:** D-005 until `UMBRA_D004_INTRINSIC_DEVELOPMENT_QUALIFIED`

## Objective

Enable UMBRA to discover practice opportunities, select learnable goals via learning progress (recent vs prior competence windows), practice emerging skills, satiate mastered goals, dormancy-filter impossible/noisy tasks, relearn after regression, and engage in safe play — without LLM, authored curricula, or authority grants.

## Implementation map

| Area | Location |
|------|----------|
| Practice goals / competence / play | `umbra_core/development/` |
| Runtime loop integration | `umbra_core/runtime.py` |
| Development interventions I0–I10 | `umbra_core/embodiment.py` |
| Tests | `tests/test_d004.py` |
| Experiments | `experiments/d004/` |
| Evidence | `docs/evidence/d004/` |

## Hard constraints

No LLM; no world-truth access for policy; no authored developmental sequence in C0; no scalar happiness/curiosity meter; no infinite novelty; no personality/social/reflection goals; practice cannot grant capabilities.

## Allowed verdicts

See project directive. D-005 authorized only under `UMBRA_D004_INTRINSIC_DEVELOPMENT_QUALIFIED`.
