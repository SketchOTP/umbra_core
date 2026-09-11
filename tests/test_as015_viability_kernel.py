from __future__ import annotations

from umbra_core.arbitration import Arbitrator, Candidate
from umbra_core.physiology import Physiology, verified_outcome_effect_branches
from umbra_core.recoverability.contracts import EXECUTABLE, NOT_EXECUTABLE
from umbra_core.recoverability.viability import (
    MAY_ROUTE,
    ROBUST_NOW,
    enumerate_regulatory_recovery_routes,
    may_route_candidates,
    robust_candidates,
)
from umbra_core.util import SeededRNG


def _phys(**updates: float) -> dict[str, float]:
    value = {"energy": 0.7, "fatigue": 0.2, "integrity": 0.9, "stimulation": 0.55}
    value.update(updates)
    return value


def _branches(candidate: Candidate):
    if candidate.capability == "CHARGE":
        return ({"energy": 0.14, "fatigue": -0.01, "stimulation": -0.005},)
    if candidate.capability == "REST":
        return ({"energy": 0.015, "fatigue": -0.08, "integrity": 0.055, "stimulation": -0.02},)
    if candidate.capability == "INSPECT":
        return ({"energy": -0.003, "fatigue": 0.002, "stimulation": 0.04},)
    return verified_outcome_effect_branches(candidate.capability)


def _routes(*, physiology: dict[str, float], needs: list[str], candidates: list[Candidate], executable):
    return enumerate_regulatory_recovery_routes(
        physiology=physiology,
        active_needs=needs,
        candidates=candidates,
        observations=[
            {"kind": "resource", "estimated_distance": 1.0},
            {"kind": "rest", "estimated_distance": 1.0},
            {"kind": "inspect", "estimated_distance": 1.0},
        ],
        authority_effect_branches_for=_branches,
        current_executability_for=executable,
    )


def test_charge_is_derived_as_current_fatigue_regulator_from_authority_effects() -> None:
    charge = Candidate("CHARGE", {"toward": "resource"})
    routes = _routes(
        physiology=_phys(fatigue=0.80),
        needs=["fatigue"],
        candidates=[charge],
        executable=lambda _: EXECUTABLE,
    )
    assert [(route.need, route.status, route.endpoint_capability) for route in routes] == [
        ("fatigue", ROBUST_NOW, "CHARGE")
    ]
    assert robust_candidates(routes) == (charge,)


def test_nonexecutable_terminal_does_not_create_a_robust_endpoint() -> None:
    charge = Candidate("CHARGE", {"toward": "resource"})
    approach = Candidate("APPROACH", {"toward": "resource", "heading_delta": 0.0, "step": 1.0})
    routes = _routes(
        physiology=_phys(fatigue=0.80),
        needs=["fatigue"],
        candidates=[charge, approach],
        executable=lambda _: NOT_EXECUTABLE,
    )
    assert robust_candidates(routes) == ()
    assert [(route.status, route.endpoint_capability, route.target_kind) for route in routes] == [
        (MAY_ROUTE, "CHARGE", "resource")
    ]
    candidate = may_route_candidates(routes)[0]
    assert candidate.capability == "APPROACH"
    assert candidate.params["toward"] == "resource"
    assert candidate.params["step"] == 1.0
    assert candidate.params["source"] == "policy_visible_recovery_approach"


def test_endpoint_discovery_has_no_authored_need_to_action_mapping() -> None:
    rest = Candidate("REST", {"toward": "rest"})
    charge = Candidate("CHARGE", {"toward": "resource"})
    routes = _routes(
        physiology=_phys(fatigue=0.80, energy=0.20),
        needs=["fatigue", "energy"],
        candidates=[rest, charge],
        executable=lambda _: EXECUTABLE,
    )
    assert {(route.need, route.endpoint_capability) for route in routes} == {
        ("energy", "CHARGE"),
        ("energy", "REST"),
        ("fatigue", "CHARGE"),
        ("fatigue", "REST"),
    }


def test_vector_safety_rejects_a_corrective_endpoint_that_leaves_another_dimension_critical() -> None:
    charge = Candidate("CHARGE", {"toward": "resource"})
    routes = _routes(
        physiology=_phys(fatigue=0.80, stimulation=0.051),
        needs=["fatigue"],
        candidates=[charge],
        executable=lambda _: EXECUTABLE,
    )
    assert robust_candidates(routes) == ()


def test_projection_uses_authoritative_physiology_saturation_before_safety_classification() -> None:
    rest = Candidate("REST", {"toward": "rest"})
    routes = _routes(
        physiology=_phys(fatigue=0.708, integrity=0.9764),
        needs=["fatigue"],
        candidates=[rest],
        executable=lambda _: EXECUTABLE,
    )
    assert robust_candidates(routes) == (rest,)


def test_may_route_requires_exact_target_bound_ordinary_pair() -> None:
    charge = Candidate("CHARGE", {"toward": "resource"})
    wrong = Candidate("APPROACH", {"toward": "rest", "heading_delta": 0.0, "step": 1.0})
    routes = _routes(
        physiology=_phys(fatigue=0.80),
        needs=["fatigue"],
        candidates=[charge, wrong],
        executable=lambda _: NOT_EXECUTABLE,
    )
    assert routes == ()


def test_may_route_uses_only_the_policy_visible_remaining_distance_as_a_step_ceiling() -> None:
    charge = Candidate("CHARGE", {"toward": "resource"})
    approach = Candidate("APPROACH", {"toward": "resource", "heading_delta": 0.0, "step": 1.0})
    routes = enumerate_regulatory_recovery_routes(
        physiology=_phys(fatigue=0.80),
        active_needs=["fatigue"],
        candidates=[charge, approach],
        observations=[{"kind": "resource", "estimated_distance": 0.25}],
        authority_effect_branches_for=_branches,
        current_executability_for=lambda _: NOT_EXECUTABLE,
    )
    candidate = may_route_candidates(routes)[0]
    assert candidate.params["step"] == 0.25
    assert candidate.params["source"] == "policy_visible_recovery_approach"
    assert routes[0].status == MAY_ROUTE


def test_counterexample_matrix_distinguishes_direct_endpoints_from_unknown_future_arrival() -> None:
    rest = Candidate("REST", {"toward": "rest"})
    charge = Candidate("CHARGE", {"toward": "resource"})
    approach_resource = Candidate("APPROACH", {"toward": "resource", "heading_delta": 0.0, "step": 1.0})

    fatigue_rest = _routes(
        physiology=_phys(fatigue=0.80), needs=["fatigue"], candidates=[rest], executable=lambda _: EXECUTABLE
    )
    fatigue_resource = _routes(
        physiology=_phys(fatigue=0.80), needs=["fatigue"], candidates=[charge], executable=lambda _: EXECUTABLE
    )
    both = _routes(
        physiology=_phys(fatigue=0.80), needs=["fatigue"], candidates=[rest, charge], executable=lambda _: EXECUTABLE
    )
    absent = _routes(
        physiology=_phys(fatigue=0.80), needs=["fatigue"], candidates=[], executable=lambda _: NOT_EXECUTABLE
    )
    distant = _routes(
        physiology=_phys(fatigue=0.80), needs=["fatigue"], candidates=[charge, approach_resource], executable=lambda _: NOT_EXECUTABLE
    )

    assert {route.endpoint_capability for route in fatigue_rest if route.status == ROBUST_NOW} == {"REST"}
    assert {route.endpoint_capability for route in fatigue_resource if route.status == ROBUST_NOW} == {"CHARGE"}
    assert {route.endpoint_capability for route in both if route.status == ROBUST_NOW} == {"REST", "CHARGE"}
    assert absent == ()
    assert robust_candidates(distant) == ()
    assert {route.status for route in distant} == {MAY_ROUTE}


def test_energy_integrity_and_stimulation_endpoints_are_all_effect_derived() -> None:
    charge = Candidate("CHARGE", {"toward": "resource"})
    rest = Candidate("REST", {"toward": "rest"})
    inspect = Candidate("INSPECT", {"toward": "inspect"})
    routes = _routes(
        physiology=_phys(energy=0.20, integrity=0.20, stimulation=0.20),
        needs=["energy", "integrity", "stimulation"],
        candidates=[charge, rest, inspect],
        executable=lambda _: EXECUTABLE,
    )
    assert {(route.need, route.endpoint_capability) for route in routes if route.status == ROBUST_NOW} == {
        ("energy", "CHARGE"),
        ("energy", "REST"),
        ("integrity", "REST"),
        ("stimulation", "INSPECT"),
    }


def test_stimulation_endpoint_is_rejected_when_it_breaks_another_component() -> None:
    inspect = Candidate("INSPECT", {"toward": "inspect"})
    routes = _routes(
        physiology=_phys(stimulation=0.20, energy=0.051),
        needs=["stimulation"],
        candidates=[inspect],
        executable=lambda _: EXECUTABLE,
    )
    assert robust_candidates(routes) == ()


def test_active_fatigue_recovery_uses_current_charge_without_a_fatigue_action_map() -> None:
    arbiter = Arbitrator()
    physiology = Physiology(energy=0.50, fatigue=0.80, integrity=0.90, stimulation=0.55)
    observations = [{"kind": "resource", "relative_direction": 0.0, "estimated_distance": 0.5}]

    selected = arbiter.select(
        physiology,
        observations,
        tick=10,
        rng=SeededRNG(15),
        authority_effect_branches=_branches,
        candidate_executability=lambda candidate: EXECUTABLE if candidate.capability == "CHARGE" else NOT_EXECUTABLE,
    )

    assert selected.capability == "CHARGE"
    assert selected.params["toward"] == "resource"
    evidence = arbiter.state.last_viability_kernel
    assert evidence is not None
    # CHARGE is selected through the ordinary recovery path, but its small
    # current effect does not itself certify repeated future CHARGE actions
    # without successor authority.  Selecting it must not manufacture a
    # multi-step preservation certificate.
    assert evidence["disposition"] == "ROBUST_ENDPOINT_COVERS_ACTIVE_NEEDS"
    assert evidence["selected_recovery_certificate"] is None
    assert evidence["endpoint_effect_source"] == "authority_effect_branches"
    assert evidence["opportunity_source"] == "ordinary_policy_visible_candidate"
    assert evidence["routes"] == [{
        "need": "fatigue",
        "status": ROBUST_NOW,
        "endpoint_capability": "CHARGE",
        "target_kind": "resource",
        "source": "current_authority_preflight",
        "blocked_by": None,
    }]


def test_uncertified_may_route_cannot_displace_currently_assessed_regulator() -> None:
    """Regression for V4C R0: no root-wide path claim may select another action."""
    arbiter = Arbitrator()
    physiology = Physiology(energy=0.17, fatigue=0.74, integrity=0.99, stimulation=0.74)
    observations = [
        {"kind": "resource", "relative_direction": 0.0, "estimated_distance": 0.5},
        {"kind": "rest", "relative_direction": 0.1, "estimated_distance": 0.5},
    ]

    selected = arbiter.select(
        physiology,
        observations,
        tick=176,
        rng=SeededRNG(15),
        authority_effect_branches=_branches,
        # Terminal REST is unavailable, so its approach remains MAY-only;
        # current CHARGE is an allowed effect-derived regulator.
        candidate_executability=lambda candidate: (
            NOT_EXECUTABLE if candidate.capability == "REST" else EXECUTABLE
        ),
    )

    assert selected.capability == "CHARGE"
    assert selected.params == {"toward": "resource"}
    evidence = arbiter.state.last_viability_kernel
    assert evidence is not None
    assert evidence["disposition"] == "ROBUST_ENDPOINT_COVERS_ACTIVE_NEEDS"
    assert evidence["selected_recovery_certificate"] is None


def test_kernel_enabled_recovery_does_not_call_legacy_energy_corridor() -> None:
    arbiter = Arbitrator()
    physiology = Physiology(energy=0.50, fatigue=0.80, integrity=0.90, stimulation=0.55)
    observations = [{"kind": "resource", "relative_direction": 0.0, "estimated_distance": 0.5}]

    def legacy_corridor(*_args, **_kwargs):
        raise AssertionError("legacy_energy_corridor_must_not_override_generic_kernel")

    arbiter._preserve_recoverability = legacy_corridor  # type: ignore[method-assign]
    selected = arbiter.select(
        physiology,
        observations,
        tick=10,
        rng=SeededRNG(15),
        authority_effect_branches=_branches,
        candidate_executability=lambda candidate: EXECUTABLE if candidate.capability == "CHARGE" else NOT_EXECUTABLE,
    )

    assert selected.capability == "CHARGE"


def test_kernel_is_inert_when_no_active_recovery_need() -> None:
    physiology = Physiology()
    observations = [{"kind": "resource", "relative_direction": 0.0, "estimated_distance": 0.5}]
    first_arbiter = Arbitrator()
    first = first_arbiter.select(physiology, observations, 10, SeededRNG(22))
    second = Arbitrator().select(Physiology(), observations, 10, SeededRNG(22))
    assert (first.capability, first.params) == (second.capability, second.params)
    assert first_arbiter.state.last_viability_kernel is None


def test_disabled_kernel_retains_current_terminal_executability_and_branch_safety() -> None:
    arbiter = Arbitrator()
    physiology = Physiology(energy=0.50, fatigue=0.80, integrity=0.90, stimulation=0.55)
    selected = arbiter.select(
        physiology,
        [{"kind": "resource", "relative_direction": 0.0, "estimated_distance": 0.5}],
        tick=10,
        rng=SeededRNG(15),
        authority_effect_branches=_branches,
        candidate_executability=lambda candidate: EXECUTABLE if candidate.capability == "CHARGE" else NOT_EXECUTABLE,
        viability_kernel_enabled=False,
    )
    assert selected.capability != "CHARGE"
    assert arbiter.state.last_viability_kernel is None
