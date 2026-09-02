"""Pure locked cases for the AS-003P-R6 development relation."""

from __future__ import annotations

from dataclasses import replace

from experiments.as003pr6.l2_schedulability import (
    CandidateBranch,
    Modality,
    RegulatoryObligation,
    RegulatoryServiceEnvelope,
    ScheduleClass,
    effect_branch,
    evaluate_candidate,
    l2_precedes,
)


ROOT = tuple(sorted({"energy": 0.5, "fatigue": 0.4, "integrity": 0.7, "stimulation": 0.4}.items()))


def obligation(owner: str, deadline: int = 5) -> RegulatoryObligation:
    capability = {"energy": "CHARGE", "fatigue": "REST", "integrity": "REST", "stimulation": "INSPECT"}[owner]
    direction = -1 if owner == "fatigue" else 1
    return RegulatoryObligation(owner, dict(ROOT)[owner], deadline, ("locked-deadline",), (capability,), direction, ("root",))


def service(capability: str, *, modality: Modality = Modality.MUST, horizon: int | None = 5, route: int | None = 0, completion: int | None = 0, branches: tuple[dict[str, float], ...] | None = None, identity: str | None = None) -> RegulatoryServiceEnvelope:
    owners = {"CHARGE": ("energy",), "REST": ("fatigue", "integrity"), "INSPECT": ("stimulation",)}[capability]
    default = {"CHARGE": ({"energy": 0.2},), "REST": ({"fatigue": -0.2, "integrity": 0.1},), "INSPECT": ({"stimulation": 0.2},)}[capability]
    return RegulatoryServiceEnvelope(
        identity or capability.lower(), capability, owners, capability.lower() + "-opportunity",
        Modality.MUST, modality, horizon, Modality.MUST, route, completion,
        tuple(effect_branch(row) for row in (branches or default)), ("locked-service",),
    )


def result(obligations, services, *, elapsed=0, supported=True, hard=False):
    branch = CandidateBranch(ROOT, elapsed, supported, hard)
    return evaluate_candidate((branch,), (tuple(obligations),), tuple(services))


def test_all_obligations_schedulable() -> None:
    got = result([obligation("energy"), obligation("fatigue"), obligation("integrity"), obligation("stimulation")], [service("CHARGE"), service("REST"), service("INSPECT")])
    assert got.branches[0].classification is ScheduleClass.COMPLETE_MUST


def test_one_hard_deadline_impossible() -> None:
    got = result([obligation("energy", 0)], [service("CHARGE")])
    assert got.branches[0].classification is ScheduleClass.NONE


def test_different_complete_orders_do_not_create_preference() -> None:
    obligations = [obligation("energy"), obligation("fatigue")]
    a = result(obligations, [service("CHARGE"), service("REST")])
    b = result(obligations, [service("REST"), service("CHARGE")])
    assert not l2_precedes(a, b) and not l2_precedes(b, a)


def test_may_versus_must_complete_has_no_preference() -> None:
    a = result([obligation("energy")], [service("CHARGE")])
    b = result([obligation("energy")], [service("CHARGE", modality=Modality.MAY)])
    assert a.branches[0].classification is ScheduleClass.COMPLETE_MUST
    assert b.branches[0].classification is ScheduleClass.COMPLETE_MAY
    assert not l2_precedes(a, b) and not l2_precedes(b, a)


def test_complete_versus_unknown_has_no_preference() -> None:
    a = result([obligation("energy")], [service("CHARGE")])
    b = result([obligation("energy")], [service("CHARGE", route=None)])
    assert b.branches[0].classification is ScheduleClass.UNKNOWN
    assert not l2_precedes(a, b) and not l2_precedes(b, a)


def test_complete_may_precedes_proven_no_schedule() -> None:
    a = result([obligation("energy")], [service("CHARGE", modality=Modality.MAY)])
    b = result([obligation("energy", 0)], [service("CHARGE")])
    assert l2_precedes(a, b)


def test_opportunity_horizon_expiry() -> None:
    got = result([obligation("energy", 5)], [service("CHARGE", horizon=1, route=1)])
    assert got.branches[0].classification is ScheduleClass.NONE


def test_unknown_horizon() -> None:
    assert result([obligation("energy")], [service("CHARGE", horizon=None)]).branches[0].classification is ScheduleClass.UNKNOWN


def test_unknown_route_duration() -> None:
    assert result([obligation("energy")], [service("CHARGE", route=None)]).branches[0].classification is ScheduleClass.UNKNOWN


def test_service_duration_exceeds_deadline() -> None:
    assert result([obligation("energy", 2)], [service("CHARGE", completion=2)]).branches[0].classification is ScheduleClass.NONE


def test_candidate_elapsed_time_consumes_slack() -> None:
    assert result([obligation("energy", 2)], [service("CHARGE")], elapsed=2).branches[0].classification is ScheduleClass.NONE


def test_rest_covers_fatigue_and_integrity_together() -> None:
    got = result([obligation("fatigue"), obligation("integrity")], [service("REST")])
    assert got.branches[0].classification is ScheduleClass.COMPLETE_MUST


def test_charge_covers_energy_only() -> None:
    got = result([obligation("energy"), obligation("fatigue")], [service("CHARGE")])
    assert got.branches[0].classification is ScheduleClass.NONE


def test_inspect_covers_stimulation_only() -> None:
    got = result([obligation("stimulation"), obligation("energy")], [service("INSPECT")])
    assert got.branches[0].classification is ScheduleClass.NONE


def test_multiple_service_effect_branches_are_universal() -> None:
    bad = service("CHARGE", branches=({"energy": 0.2}, {"energy": -0.1}))
    got = result([obligation("energy")], [bad])
    assert got.branches[0].classification is ScheduleClass.NONE


def test_one_current_branch_unschedulable() -> None:
    obligations = ((obligation("energy", 5),), (obligation("energy", 0),))
    got = evaluate_candidate((CandidateBranch(ROOT), CandidateBranch(ROOT)), obligations, (service("CHARGE"),))
    assert got.complete_on_every_branch is False and got.has_proven_no_schedule


def test_candidate_branch_permutation_invariance() -> None:
    branches = (CandidateBranch(ROOT, 0), CandidateBranch(ROOT, 1))
    obligations = ((obligation("energy", 5),), (obligation("energy", 5),))
    a = evaluate_candidate(branches, obligations, (service("CHARGE"),))
    b = evaluate_candidate(tuple(reversed(branches)), tuple(reversed(obligations)), (service("CHARGE"),))
    assert sorted(x.classification.value for x in a.branches) == sorted(x.classification.value for x in b.branches)


def test_service_permutation_invariance() -> None:
    obligations = [obligation("energy"), obligation("fatigue")]
    services = [service("CHARGE"), service("REST")]
    assert result(obligations, services).branches[0].classification == result(obligations, list(reversed(services))).branches[0].classification


def test_service_identity_rename_invariance() -> None:
    a = result([obligation("energy")], [service("CHARGE", identity="alpha")])
    b = result([obligation("energy")], [service("CHARGE", identity="beta")])
    assert a.branches[0].classification == b.branches[0].classification


def test_irrelevant_service_identity_cannot_create_preference() -> None:
    base = result([obligation("energy")], [service("CHARGE")])
    extra = result([obligation("energy")], [service("CHARGE"), service("INSPECT", identity="irrelevant")])
    assert not l2_precedes(base, extra) and not l2_precedes(extra, base)


def test_no_scalar_score_or_rng_surface() -> None:
    got = result([obligation("energy")], [service("CHARGE")])
    assert not hasattr(got, "score") and not hasattr(got, "reward") and not hasattr(got, "rng")


def test_depth_overflow_is_unknown() -> None:
    services = [service("CHARGE", identity=f"charge-{index}") for index in range(6)]
    assert result([obligation("energy")], services).branches[0].classification is ScheduleClass.UNKNOWN


def test_branch_overflow_is_unknown() -> None:
    overflow = service(
        "CHARGE",
        branches=tuple({"energy": 0.1 + index / 1000} for index in range(33)),
    )
    got = result([obligation("energy", 20)], [overflow])
    assert got.branches[0].classification is ScheduleClass.UNKNOWN
