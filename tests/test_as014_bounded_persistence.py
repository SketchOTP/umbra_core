"""AS-014 checkpoint-plus-tail persistence regression tests."""

from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from umbra_core.persistence import PersistenceError, Store
from umbra_core.runtime import (
    OrganismConfig,
    create_organism,
    load_organism,
    replay_from_birth,
    restore_habitat_engine_from_checkpoint,
)
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.habitat.events import habitat_state_from_checkpoint_payload
from umbra_core.habitat.state import sample_habitat_state


def _config(path: Path, *, tail: int = 32) -> OrganismConfig:
    return OrganismConfig(
        db_path=str(path),
        seed=4114,
        snapshot_every=1,
        embodiment_adapter_enabled=True,
        ledger_hot_tail_event_max=tail,
        ledger_max_events_per_tick=16,
        ledger_checkpoint_keep=2,
    )


def test_checkpoint_plus_tail_preserves_restart_and_attachment(tmp_path: Path) -> None:
    path = tmp_path / "checkpoint.sqlite"
    cfg = _config(path)
    org = create_organism(cfg)
    org.run_ticks(5)
    checkpoint = org.store.latest_checkpoint()
    assert checkpoint is not None
    assert checkpoint["compacted_sequence_start"] >= 1
    assert checkpoint["compacted_sequence_end"] > 0
    assert checkpoint["compacted_event_count"] > 0
    assert len(org.store.iter_events()) < org.store.last_sequence()
    assert len(org.store.iter_events()) <= cfg.ledger_hot_tail_event_max
    assert org.store.last_event_of_types(("embodiment_body_attached",)) is not None
    org.store.validate_chain()
    before = org.authoritative_state()
    org.close()

    restored = load_organism(cfg)
    assert restored.authoritative_state()["identity"] == before["identity"]
    assert restored.tick == before["tick"]
    assert restored.embodiment_adapter is not None
    assert restored.embodiment_adapter.state.to_state() == before["embodiment_adapter"]
    restored.store.validate_chain()
    restored.close()


def test_compacted_prefix_rejects_full_birth_replay_without_archive(tmp_path: Path) -> None:
    path = tmp_path / "birth-replay.sqlite"
    org = create_organism(_config(path))
    org.run_ticks(4)
    org.close()
    with pytest.raises(PersistenceError, match="full_birth_replay_unavailable_compacted_prefix"):
        replay_from_birth(str(path))


def test_checkpoint_commits_exact_habitat_state_when_attached(tmp_path: Path) -> None:
    path = tmp_path / "habitat-checkpoint.sqlite"
    cfg = _config(path)
    org = create_organism(cfg)
    engine = HabitatEngine(sample_habitat_state())
    org.embodiment.attach_habitat_engine(engine)
    org.run_ticks(4)
    checkpoint = org.store.latest_checkpoint()
    assert checkpoint is not None
    payload = checkpoint["habitat_checkpoint"]
    assert payload is not None
    restored = habitat_state_from_checkpoint_payload(payload)
    assert restored.habitat_id == engine.state.habitat_id
    assert restored.state_version == engine.state.state_version
    assert restored.state_hash == engine.state.state_hash
    assert checkpoint["habitat_binding"]["state_hash"] == engine.state.state_hash
    org.close()

    loaded = load_organism(cfg)
    reattached = restore_habitat_engine_from_checkpoint(loaded)
    assert reattached.state.habitat_id == engine.state.habitat_id
    assert reattached.state.state_hash == engine.state.state_hash
    loaded.authoritative_state()
    loaded.close()


@pytest.mark.parametrize("phase", ("checkpoint_prepared", "checkpoint_commit", "prefix_removal"))
def test_checkpoint_crash_injection_rolls_back_cleanly(tmp_path: Path, phase: str) -> None:
    path = tmp_path / f"{phase}.sqlite"
    store = Store(path)
    source = create_organism(_config(tmp_path / f"identity-{phase}.sqlite"))
    store.save_identity(source.identity)
    source.close()
    # A compact synthetic authority ledger is enough to prove storage atomicity.
    for sequence in range(4):
        store.append_event(
            agent_id=store.load_identity().agent_id,
            event_type="physiology_drift",
            monotonic_time=float(sequence),
            wall_time=float(sequence),
            payload={"sequence": sequence},
        )
    snapshot = store.save_snapshot(store.load_identity().agent_id, store.last_sequence(), 4.0, {"identity": store.load_identity().as_dict()})
    before = store.iter_events()
    with pytest.raises(PersistenceError, match="crash_injection"):
        store.compact_authoritative_prefix(
            agent_id=store.load_identity().agent_id,
            snapshot_id=snapshot,
            creation_tick=4,
            creation_wall_time=4.0,
            habitat_binding={},
            habitat_checkpoint=None,
            body_attachment={},
            crash_after=phase,
        )
    assert store.latest_checkpoint() is None
    assert store.iter_events() == before
    store.validate_chain()
    store.close()


def test_physical_reclamation_preserves_checkpoint_chain(tmp_path: Path) -> None:
    path = tmp_path / "reclaim.sqlite"
    store = Store(path)
    source = create_organism(_config(tmp_path / "identity.sqlite"))
    store.save_identity(source.identity)
    source.close()
    for index in range(128):
        store.append_event(
            agent_id=store.load_identity().agent_id,
            event_type="orchestration_tick_committed",
            monotonic_time=float(index),
            wall_time=float(index),
            payload={"payload": "x" * 4096, "index": index},
        )
    snapshot = store.save_snapshot(store.load_identity().agent_id, store.last_sequence(), 128.0, {"identity": store.load_identity().as_dict()})
    store.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    before = path.stat().st_size
    store.compact_authoritative_prefix(
        agent_id=store.load_identity().agent_id,
        snapshot_id=snapshot,
        creation_tick=128,
        creation_wall_time=128.0,
        habitat_binding={},
        habitat_checkpoint=None,
        body_attachment={},
    )
    store.reclaim_physical_storage()
    assert path.stat().st_size <= before
    store.validate_chain()
    store.close()


def test_post_checkpoint_event_keeps_absolute_sequence_and_checkpoint_predecessor(tmp_path: Path) -> None:
    path = tmp_path / "tail.sqlite"
    org = create_organism(_config(path))
    org.run_ticks(4)
    checkpoint = org.store.latest_checkpoint()
    assert checkpoint is not None
    prior_sequence = org.store.last_sequence()
    prior_hash = org.store.last_event_hash()
    event = org.store.append_event(
        agent_id=org.identity.agent_id,
        event_type="physiology_drift",
        monotonic_time=org.monotonic_time,
        wall_time=0.0,
        payload={"post_checkpoint": True},
    )
    assert event["sequence"] == prior_sequence + 1
    assert event["sequence"] > checkpoint["compacted_sequence_end"]
    assert event["previous_event_hash"] == prior_hash
    org.store.validate_chain()
    org.close()


def test_reclamation_crash_boundary_is_always_a_valid_checkpoint_state(tmp_path: Path) -> None:
    path = tmp_path / "reclaim-crash.sqlite"
    org = create_organism(_config(path))
    org.run_ticks(4)
    with pytest.raises(PersistenceError, match="crash_injection_after_vacuum"):
        org.store.reclaim_physical_storage(crash_after="after_vacuum")
    org.store.validate_chain()
    org.close()


def test_active_event_provenance_survives_successive_prefix_compactions(tmp_path: Path) -> None:
    """An event id still named by live material state must not dangle."""
    path = tmp_path / "active-provenance.sqlite"
    store = Store(path)
    source = create_organism(_config(tmp_path / "identity-active-provenance.sqlite"))
    store.save_identity(source.identity)
    source.close()
    agent_id = store.load_identity().agent_id
    source_event = store.append_event(
        agent_id=agent_id,
        event_type="outcome_verified",
        monotonic_time=1.0,
        wall_time=1.0,
        payload={"outcome": "retained"},
    )
    snapshot = store.save_snapshot(
        agent_id,
        store.last_sequence(),
        1.0,
        {"memory": {"source_event_ids": [source_event["event_id"]]}},
    )
    store.compact_authoritative_prefix(
        agent_id=agent_id,
        snapshot_id=snapshot,
        creation_tick=1,
        creation_wall_time=1.0,
        habitat_binding={},
        habitat_checkpoint=None,
        body_attachment={},
    )
    store.append_event(
        agent_id=agent_id,
        event_type="physiology_drift",
        monotonic_time=2.0,
        wall_time=2.0,
        payload={"tick": 2},
    )
    successor_snapshot = store.save_snapshot(
        agent_id,
        store.last_sequence(),
        2.0,
        {"memory": {"source_event_ids": [source_event["event_id"]]}},
    )
    store.compact_authoritative_prefix(
        agent_id=agent_id,
        snapshot_id=successor_snapshot,
        creation_tick=2,
        creation_wall_time=2.0,
        habitat_binding={},
        habitat_checkpoint=None,
        body_attachment={},
    )
    retained = {
        item["event"]["event_id"]
        for item in store.checkpoint_provenance()
        if item["provenance_key"].startswith("active_event:")
    }
    assert source_event["event_id"] in retained
    store.validate_chain()
    store.close()


def test_checkpoint_maintenance_does_not_change_logical_organism_state(tmp_path: Path) -> None:
    root = tmp_path / "root.sqlite"
    source_cfg = _config(root, tail=100_000)
    source = create_organism(source_cfg)
    source.snapshot_if_due(force=True)
    source.close()
    no_maintenance = tmp_path / "no-maintenance.sqlite"
    maintenance = tmp_path / "maintenance.sqlite"
    shutil.copy2(root, no_maintenance)
    shutil.copy2(root, maintenance)

    common = {"seed": 4114, "snapshot_every": 1, "embodiment_adapter_enabled": True, "wall_time_fn": lambda: 0.0}
    left = load_organism(OrganismConfig(db_path=str(no_maintenance), ledger_hot_tail_event_max=100_000, **common))
    right = load_organism(OrganismConfig(db_path=str(maintenance), ledger_hot_tail_event_max=32, ledger_max_events_per_tick=16, **common))
    left_actions = [left.tick_once().get("selected_action") for _ in range(5)]
    right_actions = [right.tick_once().get("selected_action") for _ in range(5)]
    assert left_actions == right_actions
    assert left.rng.export_state() == right.rng.export_state()
    assert left.phys.to_state() == right.phys.to_state()
    assert left.embodiment.to_state() == right.embodiment.to_state()
    assert left.arbitrator.state.to_state() == right.arbitrator.state.to_state()
    for name in ("world_model", "memory", "social", "individuality"):
        left_owner, right_owner = getattr(left, name), getattr(right, name)
        assert (left_owner is None) == (right_owner is None)
        if left_owner is not None:
            assert left_owner.accepted_state() == right_owner.accepted_state()
    assert left.store.latest_checkpoint() is None
    assert right.store.latest_checkpoint() is not None
    left.close()
    right.close()
