"""D-013AN verified capability progress/duration support qualification."""

from __future__ import annotations

from pathlib import Path

from umbra_core.runtime import OrganismConfig, create_organism, load_organism
from umbra_core.self_model import SelfModel, SupportSemantics
from umbra_core.util import canon_json, sha256_hex


def _verified(
    sm: SelfModel,
    *,
    capability: str = "MOVE",
    before: tuple[float, float] = (0.0, 0.0),
    after: tuple[float, float] = (1.0, 0.0),
    applied_step: float = 1.0,
    heading: float = 0.0,
    success: bool = True,
    reason: str = "ok",
    issue_tick: int = 3,
    completion_tick: int = 3,
    provenance: str = "outcome-1",
) -> dict:
    body_before = {"x": before[0], "y": before[1], "heading": 0.0}
    sm.note_body_before(body_before)
    sm.predict(
        capability,
        {"step": applied_step, "heading": heading},
        issue_tick,
        body_before,
    )
    return sm.observe_outcome(
        tick=completion_tick,
        capability=capability,
        verified_outcome={
            "capability": capability,
            "success": success,
            "reason": reason,
            "effects": {},
            "verified": True,
        },
        body_after={"x": after[0], "y": after[1], "heading": heading},
        observation_summary=None,
        action_issued=True,
        now=float(completion_tick),
        applied_params={"step": applied_step, "heading": heading},
        issue_tick=issue_tick,
        sample_body_schema_id=sm.active.body_schema_id,
        provenance_ref=provenance,
    )


def test_verified_success_updates_labeled_progress_and_duration_support() -> None:
    sm = SelfModel.create("agent", seed=1)
    result = _verified(sm, after=(0.8, 0.0), applied_step=0.8)
    support = sm.capability_support("MOVE")

    assert result["capability_support_updated"] is True
    assert support["progress"] == {
        "minimum": 0.8,
        "maximum": 0.8,
        "semantics": SupportSemantics.VERIFIED_OBSERVED_SUPPORT.value,
        "evidence_count": 1,
        "provenance": ["outcome-1"],
    }
    assert support["completion"]["minimum"] == 0.0
    assert support["completion"]["maximum"] == 0.0
    assert support["applied_step"]["minimum"] == 0.8
    assert "requested_step" not in support
    assert support["status"] == "supported"


def test_sideways_or_reverse_displacement_is_not_positive_intended_progress() -> None:
    sideways = SelfModel.create("sideways", seed=2)
    _verified(sideways, after=(0.0, 1.0))
    assert abs(sideways.capability_support("MOVE")["progress"]["maximum"]) < 1e-12

    reverse = SelfModel.create("reverse", seed=3)
    _verified(reverse, after=(-0.5, 0.0))
    assert reverse.capability_support("MOVE")["progress"]["maximum"] == -0.5


def test_failure_is_branch_separate_and_does_not_inflate_success_support() -> None:
    sm = SelfModel.create("agent", seed=4)
    _verified(sm, after=(0.3, 0.0), success=False, reason="movement_slip")
    support = sm.capability_support("MOVE")

    assert support["progress"]["semantics"] == SupportSemantics.UNKNOWN.value
    assert support["progress"]["evidence_count"] == 0
    assert support["outcome_support"]["verified_success_count"] == 0
    assert support["outcome_support"]["observed_failure_modes"]["MOVEMENT_SLIP"] == 1


def test_unverified_external_and_denied_changes_do_not_update_support() -> None:
    sm = SelfModel.create("agent", seed=5)
    schema_id = sm.active.body_schema_id
    sm.note_body_before({"x": 0.0, "y": 0.0, "heading": 0.0})
    result = sm.observe_outcome(
        tick=1,
        capability="MOVE",
        verified_outcome=None,
        body_after={"x": 1.0, "y": 0.0, "heading": 0.0},
        observation_summary=None,
        action_issued=False,
        now=1.0,
        applied_params={"step": 1.0, "heading": 0.0},
        issue_tick=1,
        sample_body_schema_id=schema_id,
        provenance_ref="not-verified",
    )
    assert result["capability_support_updated"] is False
    assert sm.capability_support("MOVE")["status"] == "unknown"


def test_delayed_completion_records_committed_tick_lag() -> None:
    sm = SelfModel.create("agent", seed=6)
    _verified(sm, issue_tick=4, completion_tick=7)
    completion = sm.capability_support("MOVE")["completion"]
    assert completion["minimum"] == 3.0
    assert completion["maximum"] == 3.0


def test_runtime_delayed_completion_uses_authoritative_issue_tick(tmp_path: Path) -> None:
    org = create_organism(
        OrganismConfig(
            db_path=str(tmp_path / "delay.sqlite"),
            seed=12,
            intervention="I3",
            drift_enabled=False,
        )
    )
    org.run_ticks(80)
    completions = [
        org.self_model.capability_support(capability)["completion"]
        for capability in ("MOVE", "APPROACH", "RETREAT")
    ]
    assert any(
        support.get("maximum") is not None and support["maximum"] >= 1.0
        for support in completions
    )
    org.close()


def test_runtime_adapter_support_records_clamped_applied_step(tmp_path: Path) -> None:
    org = create_organism(
        OrganismConfig(
            db_path=str(tmp_path / "adapter.sqlite"),
            seed=9,
            drift_enabled=False,
            embodiment_adapter_enabled=True,
        )
    )
    org.run_ticks(80)
    observed = [
        org.self_model.capability_support(capability)["applied_step"]
        for capability in ("MOVE", "APPROACH", "RETREAT")
        if org.self_model.capability_support(capability)["status"] == "supported"
    ]
    assert observed
    assert all(support["maximum"] <= 1.0 for support in observed)
    org.close()


def test_support_is_fixed_size_and_provenance_is_bounded() -> None:
    sm = SelfModel.create("agent", seed=7)
    for index in range(40):
        _verified(
            sm,
            issue_tick=index,
            completion_tick=index,
            provenance=f"outcome-{index}",
        )
    support = sm.capability_support("MOVE")
    assert support["progress"]["evidence_count"] == 40
    assert len(support["progress"]["provenance"]) == 16
    assert len(sm.active.capability_support) == 3
    assert set(support["outcome_support"]["observed_failure_modes"]) == {
        "MOVEMENT_SLIP",
        "ROUTE_BLOCKED",
        "ADAPTER_REJECTED",
        "OTHER_VERIFIED_FAILURE",
    }


def test_body_change_invalidates_empirical_support() -> None:
    sm = SelfModel.create("agent", seed=8)
    _verified(sm)
    prior_id = sm.active.body_schema_id
    sm.replace_body(reduced=True, now=10.0)

    assert sm.archive[-1].body_schema_id == prior_id
    assert sm.archive[-1].capability_support["MOVE"].status == "supported"
    assert sm.capability_support("MOVE")["status"] == "unknown"
    assert sm.capability_support("MOVE")["body_schema_id"] == sm.active.body_schema_id


def test_restart_round_trip_preserves_support_and_old_states_migrate_unknown(tmp_path: Path) -> None:
    db_path = str(tmp_path / "support.sqlite")
    org = create_organism(OrganismConfig(db_path=db_path, seed=9, drift_enabled=False))
    org.run_ticks(80)
    support_before = org.self_model.capability_support("MOVE")
    assert (
        support_before["progress"]["semantics"]
        == SupportSemantics.VERIFIED_OBSERVED_SUPPORT.value
    )
    org.snapshot_if_due(force=True)
    org.close()

    restored = load_organism(OrganismConfig(db_path=db_path, seed=9, drift_enabled=False))
    assert restored.self_model.capability_support("MOVE") == support_before
    state = restored.self_model.to_state()
    state["active"].pop("capability_support")
    state["state_hash"] = sha256_hex(
        canon_json(
            {
                "active": state["active"],
                "archive_ids": [item["body_schema_id"] for item in state["archive"]],
                "binding": state["body_binding_id"],
                "agent_id": state["agent_id"],
            }
        )
    )
    migrated = SelfModel.from_state(state)
    assert migrated.capability_support("MOVE")["status"] == "unknown"
    restored.close()


def test_birth_replay_support_provenance_is_deterministic(tmp_path: Path) -> None:
    first = create_organism(OrganismConfig(db_path=str(tmp_path / "first.db"), seed=43))
    second = create_organism(OrganismConfig(db_path=str(tmp_path / "second.db"), seed=43))
    try:
        first.run_ticks(80)
        second.run_ticks(80)
        assert first.self_model.state_hash() == second.self_model.state_hash()
        assert (
            first.self_model.active.capability_support
            == second.self_model.active.capability_support
        )
    finally:
        first.close()
        second.close()


def test_non_motion_capabilities_are_explicitly_not_applicable() -> None:
    sm = SelfModel.create("agent", seed=10)
    for capability in ("ORIENT", "REST", "CHARGE"):
        support = sm.capability_support(capability)
        assert support["progress"]["semantics"] == SupportSemantics.NOT_APPLICABLE.value
        assert support["completion"]["semantics"] == SupportSemantics.NOT_APPLICABLE.value
