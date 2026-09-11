from __future__ import annotations

from umbra_core.arbitration import Arbitrator, Candidate
from umbra_core.embodiment import Embodiment
from umbra_core.governance import authority_effect_branches, project_verified_outcome
from umbra_core.physiology import Physiology, project_verified_transition, verified_outcome_effect_branches
from umbra_core.recoverability.contracts import EXECUTABLE, NOT_EXECUTABLE
from umbra_core.recoverability.viability import (
    DIRECT_RECOVERY_PATH_NOT_PROVEN,
    PROVEN_DIRECT_RECOVERY_PATH,
    ROBUST_NOW,
    direct_regulatory_recovery_path_status,
    enumerate_regulatory_recovery_routes,
    preserves_robust_recovery_reserve,
)
from umbra_core.util import SeededRNG


def _branches(embodiment: Embodiment, candidate: Candidate):
    return authority_effect_branches(
        candidate,
        embodiment,
        None,
        resolve_params=lambda params: dict(params),
    )


def _state(**updates: float) -> dict[str, float]:
    state = {"energy": 0.7, "fatigue": 0.2, "integrity": 0.9, "stimulation": 0.55}
    state.update(updates)
    return state


def _synthetic_current_authority(candidate: Candidate):
    """Current executable effects for the pure multi-need counterexample.

    A default Embodiment has no colocated resource, so it cannot lawfully serve
    as a CHARGE reserve. This fixture instead states the source contract under
    test: both ordinary candidates are already executable at their observed
    opportunities.
    """
    effects = {
        "ORIENT": {"energy": -0.001, "fatigue": 0.001, "stimulation": 0.005},
        "CHARGE": {"energy": 0.14, "fatigue": -0.01, "stimulation": -0.005},
    }
    return (dict(effects[candidate.capability]),)


def test_orient_preflight_matches_immediate_and_delayed_execution_dispatch() -> None:
    embodiment = Embodiment()
    candidate = Candidate("ORIENT", {"heading": 1.0, "toward": "inspect"})
    immediate = embodiment.preflight_primitive(candidate.capability, dict(candidate.params))
    assert immediate == {
        "capability": "ORIENT",
        "params": dict(candidate.params),
        "energy_cost_scale": 1.0,
        "adapter_certified": False,
        "ok_raw": True,
        "reason": "ok",
        "delayed": False,
    }
    immediate_branches = _branches(embodiment, candidate)
    assert immediate_branches == ({"energy": -0.001, "fatigue": 0.001, "stimulation": 0.005},)
    immediate_raw = embodiment.execute_primitive(
        candidate.capability, dict(candidate.params), SeededRNG(1601)
    )
    assert immediate_raw.get("delayed") is not True
    assert project_verified_outcome(candidate.capability, immediate_raw) == (
        True,
        immediate_branches[0],
    )

    physiology = Physiology(energy=0.7, fatigue=0.2, integrity=0.9, stimulation=0.051)
    assert not Arbitrator._introduces_critical_boundary(
        candidate, physiology, effect_branches=immediate_branches
    )

    embodiment.body.actuator_delay = 2.0
    delayed = embodiment.preflight_primitive(candidate.capability, dict(candidate.params))
    assert delayed is not None and delayed["reason"] == "delayed" and delayed["delayed"] is True
    delayed_branches = _branches(embodiment, candidate)
    assert delayed_branches == ({},)
    delayed_raw = embodiment.execute_primitive(
        candidate.capability, dict(candidate.params), SeededRNG(1602)
    )
    assert delayed_raw["delayed"] is True
    assert project_verified_outcome(candidate.capability, delayed_raw) == (False, {})
    assert Arbitrator._introduces_critical_boundary(
        candidate, physiology, effect_branches=delayed_branches
    )


def test_projected_transition_uses_effect_clamp_then_drift_clamp() -> None:
    result = project_verified_transition(
        _state(fatigue=0.01), {"fatigue": -0.08}
    )
    assert result["fatigue"] == 0.002


def test_nonterminal_regulators_are_derived_from_current_authority_effects() -> None:
    embodiment = Embodiment()
    orient = Candidate("ORIENT", {"heading": 0.0, "toward": "inspect"})
    idle = Candidate("IDLE", {})
    routes = enumerate_regulatory_recovery_routes(
        physiology=_state(stimulation=0.20, integrity=0.20),
        active_needs=["stimulation", "integrity"],
        candidates=[orient, idle],
        observations=[],
        authority_effect_branches_for=lambda candidate: _branches(embodiment, candidate),
        current_executability_for=lambda _: EXECUTABLE,
    )
    assert {
        (route.need, route.endpoint_capability, route.status)
        for route in routes
    } == {
        ("stimulation", "ORIENT", ROBUST_NOW),
        ("integrity", "IDLE", ROBUST_NOW),
    }


def test_regulator_cannot_starve_a_different_active_need_without_a_reserve() -> None:
    orient = Candidate("ORIENT", {"heading": 0.0, "toward": "inspect"})
    charge = Candidate("CHARGE", {"toward": "resource"})
    state = _state(energy=0.20, stimulation=0.20)
    source = _synthetic_current_authority
    assert not preserves_robust_recovery_reserve(
        candidate=orient,
        physiology=state,
        candidates=[orient],
        observations=[],
        authority_effect_branches_for=source,
        current_executability_for=lambda _: EXECUTABLE,
    )
    assert preserves_robust_recovery_reserve(
        candidate=orient,
        physiology=state,
        candidates=[orient, charge],
        observations=[],
        authority_effect_branches_for=source,
        current_executability_for=lambda _: EXECUTABLE,
    )


def test_direct_regulatory_path_is_proven_only_when_current_effects_reach_viability() -> None:
    """A source-visible MAY route cannot displace a proven direct regulator."""
    charge = Candidate("CHARGE", {"toward": "resource"})
    assert direct_regulatory_recovery_path_status(
        physiology=_state(energy=0.25),
        candidates=[charge],
        observations=[],
        authority_effect_branches_for=_synthetic_current_authority,
        current_executability_for=lambda _: EXECUTABLE,
    ) == PROVEN_DIRECT_RECOVERY_PATH


def test_one_step_reserve_cannot_hide_a_source_visible_route_after_multineed_loss() -> None:
    """Regression for retained AS-016 R0 tick 2178, without its RNG trace.

    REST and ORIENT each correct a current need, and the old one-step check
    could report ORIENT as preserving.  Neither leaves a second safe action
    that covers both energy and stimulation.  A current, policy-visible
    APPROACH remains MAY-only, but it must not be suppressed by that false
    robust-reserve claim.
    """
    orient = Candidate("ORIENT", {"heading_delta": 0.2, "toward": "resource"})
    rest = Candidate("REST", {"toward": "rest"})
    charge = Candidate("CHARGE", {"toward": "resource"})
    approach = Candidate("APPROACH", {"heading_delta": 0.2, "step": 1.0, "toward": "resource"})
    state = _state(energy=0.058, fatigue=0.011, integrity=0.9992, stimulation=0.081)
    effects = {
        "ORIENT": ({"energy": -0.001, "fatigue": 0.001, "stimulation": 0.005},),
        "REST": ({"energy": 0.015, "fatigue": -0.08, "integrity": 0.055, "stimulation": -0.02},),
        "CHARGE": ({"energy": 0.14, "fatigue": -0.01, "stimulation": -0.005},),
        "APPROACH": (
            {"energy": -0.004, "fatigue": 0.003, "stimulation": 0.004},
            {"energy": -0.003, "fatigue": 0.003},
        ),
    }

    def branches(candidate: Candidate):
        return effects.get(candidate.capability, verified_outcome_effect_branches(candidate.capability))

    def executability(candidate: Candidate) -> str:
        return NOT_EXECUTABLE if candidate.capability == "CHARGE" else EXECUTABLE

    direct = [orient, rest, charge, approach]
    # The retained defect: the immediate successor merely listed corrective
    # endpoints, though none had a safe continuation for both active needs.
    assert preserves_robust_recovery_reserve(
        candidate=orient,
        physiology=state,
        candidates=direct,
        observations=[],
        authority_effect_branches_for=branches,
        current_executability_for=executability,
        continuation_depth=1,
    )
    assert not preserves_robust_recovery_reserve(
        candidate=orient,
        physiology=state,
        candidates=direct,
        observations=[],
        authority_effect_branches_for=branches,
        current_executability_for=executability,
    )
    assert direct_regulatory_recovery_path_status(
        physiology=state,
        candidates=direct,
        observations=[],
        authority_effect_branches_for=branches,
        current_executability_for=executability,
    ) == DIRECT_RECOVERY_PATH_NOT_PROVEN

    arbiter = Arbitrator()
    chosen = arbiter.select(
        Physiology(**state),
        [
            {"kind": "resource", "relative_direction": 0.2, "estimated_distance": 8.726},
            {"kind": "rest", "relative_direction": -2.85, "estimated_distance": 0.421},
        ],
        tick=2178,
        rng=SeededRNG(1616),
        authority_effect_branches=branches,
        candidate_executability=executability,
    )

    assert chosen.capability == "APPROACH"
    assert chosen.params["source"] == "policy_visible_recovery_approach"
    assert arbiter.state.last_viability_kernel is not None
    assert arbiter.state.last_viability_kernel["disposition"] == "MAY_ROUTE_SELECTED_NO_VECTOR_DIRECT"
    assert arbiter.state.last_viability_kernel["direct_regulatory_path_status"] is None
