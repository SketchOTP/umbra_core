from __future__ import annotations

from umbra_core.arbitration import Arbitrator, Candidate
from umbra_core.physiology import Physiology, verified_outcome_effect_branches
from umbra_core.recoverability import (
    RecoverabilityStatus,
    prospective_recoverability_transition,
)
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


def test_filter_preserves_supported_alternative_and_existing_scoring_authority():
    arb = Arbitrator()
    move = _moving_away()
    charge = Candidate("CHARGE", {"toward": "resource", "source": "base"})
    arb.generate_candidates = lambda phys, observations, tick: [move, charge]

    def score(candidate, phys, observations, tick):
        candidate.total = 10.0 if candidate.capability == "MOVE" else 1.0
        candidate.scores = {}
        return candidate

    arb.score_candidate = score
    arb._introduces_critical_boundary = lambda *args, **kwargs: False
    events = []
    chosen = arb.select(
        Physiology(energy=0.301),
        [_resource()],
        1,
        ZeroNoise(),
        prospective_recoverability_context=_context(),
        prospective_recoverability_observer=events.append,
    )
    assert chosen.capability == "CHARGE"
    assert any(
        event["candidate"]["capability"] == "MOVE" and event["constrained"]
        for event in events
    )
    assert any(
        event["candidate"]["capability"] == "CHARGE" and not event["constrained"]
        for event in events
    )


def test_unknown_support_is_neutral_in_integrated_filter():
    candidates, events = Arbitrator._prospective_recoverability_filter(
        candidates=[_moving_away()],
        phys=Physiology(energy=0.301),
        observations=[_resource()],
        tick=1,
        attended_dimensions=frozenset({"energy"}),
        context=_context(SupportSemantics.UNKNOWN.value),
        effect_branches=lambda candidate: verified_outcome_effect_branches(
            candidate.capability
        ),
    )
    assert len(candidates) == 1
    assert events[0]["constrained"] is False
    assert "UNKNOWN" in events[0]["transitions"][0]["projected_status"]


def test_empty_filtered_pool_uses_existing_no_safe_action_without_fallback():
    arb = Arbitrator()
    arb.generate_candidates = lambda phys, observations, tick: [_moving_away()]
    arb._introduces_critical_boundary = lambda *args, **kwargs: False
    chosen = arb.select(
        Physiology(energy=0.301),
        [_resource()],
        1,
        ZeroNoise(),
        prospective_recoverability_context=_context(),
    )
    assert chosen.capability == "IDLE"
    assert chosen.params == {
        "source": "no_safe_action",
        "reason": "no_verified_branch_safe",
    }


def test_active_recovery_does_not_consult_prospective_filter():
    arb = Arbitrator()
    events = []
    chosen = arb.select(
        Physiology(energy=0.29),
        [_resource()],
        1,
        ZeroNoise(),
        prospective_recoverability_context=_context(),
        prospective_recoverability_observer=events.append,
    )
    assert chosen.capability in {"APPROACH", "CHARGE", "SIGNAL_ASSISTANCE"}
    assert events == []


def test_source_provenance_does_not_change_constraint():
    first, first_events = Arbitrator._prospective_recoverability_filter(
        candidates=[_moving_away("development")],
        phys=Physiology(energy=0.301),
        observations=[_resource()],
        tick=1,
        attended_dimensions=frozenset({"energy"}),
        context=_context(),
        effect_branches=lambda candidate: verified_outcome_effect_branches(
            candidate.capability
        ),
    )
    second, second_events = Arbitrator._prospective_recoverability_filter(
        candidates=[_moving_away("memory")],
        phys=Physiology(energy=0.301),
        observations=[_resource()],
        tick=1,
        attended_dimensions=frozenset({"energy"}),
        context=_context(),
        effect_branches=lambda candidate: verified_outcome_effect_branches(
            candidate.capability
        ),
    )
    assert first == second == []
    assert first_events == second_events
