from __future__ import annotations

from umbra_core.arbitration import Arbitrator, Candidate
from umbra_core.physiology import Physiology, verified_outcome_effect_branches
from umbra_core.recoverability import (
    RecoverabilityStatus,
    enumerate_regulatory_recovery_routes,
    prospective_recoverability_transition,
)
from umbra_core.recoverability.contracts import candidate_is_admissible
from umbra_core.self_model.engine import SupportSemantics


class ZeroNoise:
    def gauss(self, mean, sigma):
        return 0.0


def _interval(semantics=SupportSemantics.VERIFIED_OBSERVED_SUPPORT.value):
    return {
        "minimum": 1.0,
        "maximum": 1.0,
        "semantics": semantics,
        "evidence_count": 4,
        "provenance": ["verified-outcome:test"],
    }


def _support(semantics=SupportSemantics.VERIFIED_OBSERVED_SUPPORT.value):
    return {
        capability: {
            "capability": capability,
            "body_schema_id": "body-1",
            "progress": _interval(semantics),
            "completion": {
                **_interval(semantics),
                "minimum": 0.0,
                "maximum": 0.0,
            },
        }
        for capability in ("MOVE", "APPROACH", "RETREAT")
    }


def _resource(*, semantics=SupportSemantics.VERIFIED_OBSERVED_SUPPORT.value):
    return {
        "kind": "resource",
        "fact_kind": "REMEMBERED_ESTIMATE",
        "source": "world_model_memory",
        "relative_direction": 3.141592653589793,
        "estimated_distance": 40.0,
        "distance_support_upper_bound": 40.0,
        "support_center_dx": 40.0,
        "support_center_dy": 0.0,
        "support_radius": 0.0,
        "support_provenance": "sensor:bounded_body_region",
        "support_source_kind": "CURRENT_OBSERVATION",
        "support_semantics": semantics,
        "support_body_schema_id": "body-1",
    }


def _context(semantics=SupportSemantics.VERIFIED_OBSERVED_SUPPORT.value):
    return {
        "body_schema_id": "body-1",
        "capability_support": _support(semantics),
        "body_energy_cost_scale": 1.0,
        "pending_commitment": False,
    }


def _moving_away(source="base"):
    return Candidate(
        "MOVE",
        {
            "heading_delta": 3.141592653589793,
            "step": 1.0,
            "toward": "resource",
            "source": source,
        },
    )


def test_production_transition_constrains_only_supported_option_destruction():
    result = prospective_recoverability_transition(
        organism_tick=1,
        body_schema_id="body-1",
        physiology=Physiology(energy=0.301).to_state(),
        attended_dimensions=["energy"],
        observations=[_resource()],
        candidate=_moving_away(),
        authority_effect_branches=verified_outcome_effect_branches("MOVE"),
        capability_support=_support(),
    )
    row = result["transitions"][0]
    assert row["current_status"] == RecoverabilityStatus.SUPPORTED_MARGIN_POSITIVE.value
    assert row["projected_status"] == RecoverabilityStatus.SUPPORTED_MARGIN_EXHAUSTED.value
    assert result["constrained"] is True
    assert result["action_authority"] is False
    assert result["candidate_created"] is False
    assert result["rollout_required"] is False


def test_current_authority_preserves_supported_regulatory_alternative():
    move = _moving_away()
    charge = Candidate("CHARGE", {"toward": "resource", "source": "base"})
    effects = {
        "MOVE": (verified_outcome_effect_branches("MOVE")[0],),
        "CHARGE": (verified_outcome_effect_branches("CHARGE")[0],),
    }
    routes = enumerate_regulatory_recovery_routes(
        physiology=Physiology(energy=0.301).as_dict(),
        active_needs=["energy"],
        candidates=[move, charge],
        observations=[_resource()],
        authority_effect_branches_for=lambda candidate: effects[candidate.capability],
        current_executability_for=lambda _: "EXECUTABLE",
    )
    assert {(route.need, route.endpoint_capability) for route in routes} == {
        ("energy", "CHARGE"),
    }


def test_unknown_support_is_neutral_in_integrated_filter():
    candidate = _moving_away()
    assert candidate_is_admissible(
        candidate,
        physiology=Physiology(energy=0.301),
        observations=[_resource(semantics=SupportSemantics.UNKNOWN.value)],
        arbitration_state=Arbitrator().state,
        effect_branches=verified_outcome_effect_branches(candidate.capability),
    )


def test_empty_filtered_pool_uses_existing_no_safe_action_without_fallback():
    arb = Arbitrator()
    arb.generate_candidates = lambda phys, observations, tick: [_moving_away()]
    arb._introduces_critical_boundary = lambda *args, **kwargs: False
    chosen = arb.select(
        Physiology(energy=0.301),
        [_resource()],
        1,
        ZeroNoise(),
    )
    assert chosen.capability == "MOVE"


def test_active_recovery_does_not_consult_prospective_filter():
    arb = Arbitrator()
    chosen = arb.select(
        Physiology(energy=0.29),
        [_resource()],
        1,
        ZeroNoise(),
    )
    assert chosen.capability in {"APPROACH", "CHARGE", "SIGNAL_ASSISTANCE"}


def test_source_provenance_does_not_change_constraint():
    state = Physiology(energy=0.301)
    observations = [_resource()]
    first = candidate_is_admissible(
        _moving_away("development"),
        physiology=state,
        observations=observations,
        arbitration_state=Arbitrator().state,
        effect_branches=verified_outcome_effect_branches("MOVE"),
    )
    second = candidate_is_admissible(
        _moving_away("memory"),
        physiology=state,
        observations=observations,
        arbitration_state=Arbitrator().state,
        effect_branches=verified_outcome_effect_branches("MOVE"),
    )
    assert first == second
