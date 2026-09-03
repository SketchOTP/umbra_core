"""Pure AS-006 weak-option loss and recovery-slack proofs."""

from __future__ import annotations

from dataclasses import replace

from tests.test_as005_modal_preventive import frame_with_route
from umbra_core.arbitration import Candidate
from umbra_core.hypothetical.action_selection import eliminate_by_continuation
from umbra_core.hypothetical.core import FrozenMap


def frame_at(*, energy: float = 0.7, fatigue: float = 0.2):
    frame = frame_with_route()
    return replace(
        frame,
        physiology_root=FrozenMap({
            "energy": energy,
            "fatigue": fatigue,
            "integrity": 0.9,
            "stimulation": 0.55,
        }),
        material_fingerprint="",
    )


def option_status(result, candidate_index: int = 0) -> str:
    return next(
        status
        for identity, status in result.classifications[candidate_index].status_by_witness
        if identity.startswith("known-option:")
    )


def test_may_option_is_evaluated_after_candidate_branch() -> None:
    result = eliminate_by_continuation(
        frame_at(energy=0.3105),
        [Candidate("IDLE", {}), Candidate("SIGNAL_PLAY", {})],
    )
    assert option_status(result, 0) == "PRESERVED"
    assert option_status(result, 1) == "DESTROYED"
    assert result.eliminated


def test_may_loss_does_not_claim_all_recovery_is_impossible() -> None:
    result = eliminate_by_continuation(frame_at(energy=0.31), [Candidate("IDLE", {})])
    row = result.classifications[0]
    assert option_status(result) == "DESTROYED"
    assert "OPTION_ENERGY_SLACK_EXHAUSTED" in row.unknown_reasons


def test_supported_outcome_branch_mixture_is_unknown() -> None:
    result = eliminate_by_continuation(
        frame_at(energy=0.31),
        [Candidate("ORIENT", {})],
    )
    assert option_status(result) == "UNKNOWN"


def test_may_option_identity_is_candidate_neutral() -> None:
    first = eliminate_by_continuation(frame_at(), [Candidate("IDLE", {"x": 1}), Candidate("MOVE", {})])
    second = eliminate_by_continuation(frame_at(), [Candidate("MOVE", {"other": 2}), Candidate("IDLE", {})])
    assert first.modal_options == second.modal_options
    assert first.modal_option_details[0]["opportunity_identity"] == "entity:resource:1"
    assert first.modal_option_details[0]["observed_demand_ticks"] == 4


def test_preventive_activation_uses_option_demand_not_fixed_depth() -> None:
    frame = frame_at(energy=0.305)
    result = eliminate_by_continuation(frame, [Candidate("IDLE", {})])
    # The route demand is four ticks and the energy boundary is reached inside
    # that demand.  A larger hypothetical recursion depth cannot activate this
    # option; the status is determined by source demand and owner slack.
    assert option_status(result) == "DESTROYED"
