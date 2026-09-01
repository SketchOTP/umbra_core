"""Focused qualification for AS-003S atomic true-body replacement."""

from __future__ import annotations

from dataclasses import replace
import json

import pytest

from umbra_core.embodiment_adapters.adapter import AdapterRequest
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.habitat.state import (
    HeldByLocation,
    sample_habitat_state,
    with_object_state_hash,
    with_state_hash,
)
from umbra_core.persistence import PersistenceError
from umbra_core.runtime import (
    BodyReplacementError,
    OrganismConfig,
    create_organism,
    load_organism,
)
from umbra_core.util import sha256_hex


def _config(tmp_path, name: str, *, seed: int = 403) -> OrganismConfig:
    return OrganismConfig(
        db_path=str(tmp_path / name),
        seed=seed,
        embodiment_adapter_enabled=True,
        wall_time_fn=lambda: 100.0,
    )


def _replacement_events(org):
    return [
        event
        for event in org.store.iter_events()
        if event["event_type"] == "embodiment_body_replaced"
    ]


def test_true_replacement_is_one_coherent_identity_transaction_and_restarts(tmp_path):
    cfg = _config(tmp_path, "replace.sqlite")
    org = create_organism(cfg)
    identity_before = org.identity.as_dict()
    adapter_before = org.embodiment_adapter.state.to_state()
    schema_before = org.self_model.active.to_dict()
    binding_before = org.self_model.body_binding_id
    profile_before = org.embodiment_adapter.state.body_profile_id

    result = org.replace_physical_body(new_profile_id=profile_before)

    assert org.identity.as_dict() == identity_before
    assert result["new_body_instance_id"] != result["old_body_instance_id"]
    assert result["new_generation"] == result["old_generation"] + 1
    assert org.embodiment_adapter.state.body_instance_id == result["new_body_instance_id"]
    assert org.embodiment.body_occupancy_view().body_instance_id == result["new_body_instance_id"]
    assert org.embodiment.body_occupancy_view().attachment_generation == result["new_generation"]
    assert org.self_model.body_binding_id != binding_before
    assert org.self_model.active.body_schema_id != schema_before["body_schema_id"]
    assert org.self_model.active.version == schema_before["version"] + 1
    assert all(item.status == "unknown" for item in org.self_model.active.capability_support.values())
    assert any(
        archived.body_schema_id == schema_before["body_schema_id"] and not archived.active
        for archived in org.self_model.archive
    )
    events = _replacement_events(org)
    assert len(events) == 1
    event = events[0]
    assert event["sequence"] == result["event_sequence"]
    assert event["payload"]["old_body_instance_id"] == adapter_before["body_instance_id"]
    assert event["payload"]["new_body_instance_id"] == result["new_body_instance_id"]
    snapshot = org.store.load_snapshot(result["snapshot_id"])
    assert snapshot["sequence"] == event["sequence"]
    assert snapshot["state"]["embodiment_adapter"]["body_instance_id"] == result["new_body_instance_id"]
    assert snapshot["state"]["embodiment"]["body_instance_id"] == result["new_body_instance_id"]
    assert snapshot["state"]["self_model"]["body_binding_id"] == result["new_body_binding_id"]
    org.store.validate_chain()
    org.close()

    restored = load_organism(cfg)
    assert restored.identity.as_dict() == identity_before
    assert restored.embodiment_adapter.state.body_instance_id == result["new_body_instance_id"]
    assert restored.embodiment.body_occupancy_view().body_instance_id == result["new_body_instance_id"]
    assert restored.self_model.body_binding_id == result["new_body_binding_id"]
    assert restored.self_model.active.body_schema_id == result["new_body_schema_id"]
    assert len(_replacement_events(restored)) == 1
    restored.close()


@pytest.mark.parametrize("stage", [1, 2])
def test_precommit_crash_rolls_back_event_snapshot_and_live_owners(tmp_path, stage):
    cfg = _config(tmp_path, f"rollback-{stage}.sqlite", seed=410 + stage)
    org = create_organism(cfg)
    before = org.authoritative_state()
    before_snapshot = org.store.load_snapshot()["snapshot_id"]
    with pytest.raises(PersistenceError, match=f"crash_injection_after_stage_{stage}"):
        org.replace_physical_body(_crash_after_stage=stage)
    assert org.authoritative_state() == before
    assert _replacement_events(org) == []
    assert org.store.load_snapshot()["snapshot_id"] == before_snapshot
    org.store.validate_chain()
    org.close()


def test_commit_before_live_apply_recovers_exactly_once_from_snapshot(tmp_path):
    cfg = _config(tmp_path, "postcommit.sqlite", seed=420)
    org = create_organism(cfg)
    old_body_id = org.embodiment_adapter.state.body_instance_id
    with pytest.raises(BodyReplacementError, match="postcommit_live_apply_injected"):
        org.replace_physical_body(_fail_after_commit_before_apply=True)
    assert org.embodiment_adapter.state.body_instance_id == old_body_id
    event = _replacement_events(org)[0]
    new_body_id = event["payload"]["new_body_instance_id"]
    org.close()

    restored = load_organism(cfg)
    assert restored.embodiment_adapter.state.body_instance_id == new_body_id
    assert restored.embodiment.body_occupancy_view().body_instance_id == new_body_id
    assert restored.self_model.body_binding_id == event["payload"]["new_body_binding_id"]
    assert restored.self_model.active.body_schema_id == event["payload"]["new_body_schema_id"]
    assert len(_replacement_events(restored)) == 1
    restored.close()


def test_held_object_rejects_without_any_replacement_mutation(tmp_path):
    cfg = _config(tmp_path, "held.sqlite", seed=430)
    org = create_organism(cfg)
    body_id = org.embodiment_adapter.state.body_instance_id
    generation = org.embodiment_adapter.state.attachment_generation
    state = sample_habitat_state()
    resource = with_object_state_hash(
        replace(
            state.objects["resource:0"],
            location=HeldByLocation(
                body_instance_id=body_id,
                attachment_generation=generation,
                hold_slot=0,
            ),
        )
    )
    state = with_state_hash(replace(state, objects={**state.objects, "resource:0": resource}))
    org.embodiment.attach_habitat_engine(HabitatEngine(state))
    before = org.authoritative_state()
    before_snapshot = org.store.load_snapshot()["snapshot_id"]

    with pytest.raises(BodyReplacementError, match="old_body_holds_objects"):
        org.replace_physical_body()

    assert org.authoritative_state() == before
    assert _replacement_events(org) == []
    assert org.store.load_snapshot()["snapshot_id"] == before_snapshot
    held = org.embodiment._habitat_engine.state.objects["resource:0"].location
    assert held.body_instance_id == body_id
    assert held.attachment_generation == generation
    org.close()


@pytest.mark.parametrize(
    ("attribute", "value", "message"),
    [
        ("_pending_action", {"capability": "MOVE"}, "pending_action"),
        ("_delayed_proposal", {"capability": "MOVE"}, "delayed_proposal"),
        ("_pending_world_plan", ["MOVE"], "pending_world_plan"),
    ],
)
def test_runtime_pending_state_rejects_before_durable_mutation(
    tmp_path, attribute, value, message
):
    org = create_organism(_config(tmp_path, f"pending-{attribute}.sqlite"))
    setattr(org, attribute, value)
    with pytest.raises(BodyReplacementError, match=message):
        org.replace_physical_body()
    assert _replacement_events(org) == []
    org.close()


def test_prepared_habitat_execution_rejects_before_durable_mutation(tmp_path):
    org = create_organism(_config(tmp_path, "prepared.sqlite", seed=440))
    org.store.insert_habitat_execution_journal_prepared(
        execution_id="exec:prepared",
        request_id="req:prepared",
        canonical_payload_hash="a" * 64,
        payload_json="{}",
        transaction_id="txn:prepared",
        prepared_tick=0,
    )
    with pytest.raises(BodyReplacementError, match="prepared_habitat_execution"):
        org.replace_physical_body()
    assert _replacement_events(org) == []
    org.close()


def test_stale_old_generation_rejected_and_new_generation_admitted(tmp_path):
    org = create_organism(_config(tmp_path, "stale.sqlite", seed=450))
    old_generation = org.embodiment_adapter.state.attachment_generation
    org.replace_physical_body()
    stale = AdapterRequest(
        request_id="request:stale",
        capability="IDLE",
        params={},
        attachment_generation=old_generation,
    )
    current = replace(
        stale,
        request_id="request:current",
        attachment_generation=org.embodiment_adapter.state.attachment_generation,
    )
    stale_rejection, _, _ = org.embodiment_adapter.preflight_execution(stale)
    current_rejection, _, _ = org.embodiment_adapter.preflight_execution(current)
    assert stale_rejection["failure_code"] == "STALE_ATTACHMENT_GENERATION"
    assert current_rejection is None
    org.close()


def test_profile_swap_and_detach_reattach_remain_distinct_from_replacement(tmp_path):
    org = create_organism(_config(tmp_path, "lifecycle.sqlite", seed=460))
    adapter = org.embodiment_adapter
    body_id = adapter.state.body_instance_id
    binding_id = org.self_model.body_binding_id
    schema_id = org.self_model.active.body_schema_id
    generation = adapter.state.attachment_generation

    adapter.swap_profile(adapter.state.body_profile_id)
    assert adapter.state.body_instance_id == body_id
    assert adapter.state.attachment_generation == generation + 1
    assert org.embodiment.body_occupancy_view().attachment_generation == generation + 1
    assert org.self_model.body_binding_id == binding_id
    assert org.self_model.active.body_schema_id == schema_id

    adapter.detach("temporary")
    adapter.attach(adapter.state.body_profile_id or "ABSTRACT_SHAPE_BODY")
    assert adapter.state.body_instance_id == body_id
    assert org.self_model.body_binding_id == binding_id
    assert org.self_model.active.body_schema_id == schema_id
    assert _replacement_events(org) == []
    org.close()


def test_bounded_lifecycle_runs_before_and_after_replacement(tmp_path):
    org = create_organism(_config(tmp_path, "lifecycle-run.sqlite", seed=470))
    assert org.tick_once()["tick"] == 1
    identity = org.identity.as_dict()
    old_body_id = org.embodiment_adapter.state.body_instance_id
    result = org.replace_physical_body()
    assert result["new_body_instance_id"] != old_body_id
    assert org.tick_once()["tick"] == 2
    assert org.identity.as_dict() == identity
    assert org.metrics["total_ticks"] == 2
    org.close()


def test_ledger_newer_than_snapshot_rebinds_occupancy_without_conflict(tmp_path):
    cfg = _config(tmp_path, "ledger-newer.sqlite", seed=480)
    org = create_organism(cfg)
    body_id = org.embodiment_adapter.state.body_instance_id
    old_snapshot = org.store.load_snapshot()
    org.embodiment_adapter.swap_profile("MINIMAL_CREATURE_BODY")
    new_generation = org.embodiment_adapter.state.attachment_generation
    assert org.store.load_snapshot()["snapshot_id"] == old_snapshot["snapshot_id"]
    org.close()

    restored = load_organism(cfg)
    assert restored.embodiment_adapter.state.body_instance_id == body_id
    assert restored.embodiment_adapter.state.attachment_generation == new_generation
    assert restored.embodiment.body_occupancy_view().body_instance_id == body_id
    assert restored.embodiment.body_occupancy_view().attachment_generation == new_generation
    restored.close()


def test_same_sequence_snapshot_occupancy_conflict_fails_closed(tmp_path):
    cfg = _config(tmp_path, "occupancy-conflict.sqlite", seed=490)
    org = create_organism(cfg)
    snapshot = org.store.load_snapshot()
    corrupted = dict(snapshot["state"])
    corrupted_embodiment = dict(corrupted["embodiment"])
    corrupted_embodiment["body_instance_id"] = "body:conflicting"
    corrupted["embodiment"] = corrupted_embodiment
    state_json = json.dumps(corrupted, sort_keys=True, separators=(",", ":"), default=str)
    org.store.conn.execute(
        "UPDATE snapshots SET state_json=?, state_hash=? WHERE snapshot_id=?",
        (state_json, sha256_hex(state_json), snapshot["snapshot_id"]),
    )
    org.close()

    with pytest.raises(PersistenceError, match="snapshot_attachment_occupancy_mismatch"):
        load_organism(cfg)
