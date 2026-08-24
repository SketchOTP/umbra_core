# UMBRA-D-014G  Unified Candidate Proposal / Single Final Selection Authority

- Status: active
- Baseline: c198b46413731444222e8e1fa8495d932f2aa836
- Parent: D014F_PROSPECTIVE_OPPORTUNITY_SHADOW_FAIL
- Mode: non-formal, shadow-first authority-topology investigation

## Objective

Enumerate candidate creation and replacement sources, freeze one proposal-pool
and final-selection contract, preserve current semantics when the prospective
mechanism is disabled, and test whether the frozen D-014F prospective proposal
can survive the full runtime once all sources enter one final selection
boundary.

## Boundaries

No production physiology, drift, outcome, habitat, identity, temporal,
learned-model, recovery-threshold, D-013/AX, formal-D-014, or formal-tag work.
No hidden truth, scripted rescue, scalar survival controller, or generic
RL/MPC/CBF/HJ controller.

## Initial live findings

umbra_core/runtime.py calls Arbitrator.select() at the primary selection site,
then later assigns cand from development practice, memory retrieval, social
proposal, world-model planning, dormant-capability handling, and final
safety/no-safe-action handling before Governance.propose().
