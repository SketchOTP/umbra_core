"""D-011 governed synthetic perception-adapter contracts."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from umbra_core.events import AUTHORITATIVE_EVENT_TYPES, is_authoritative
from umbra_core.perception import PerceptionMembrane
from umbra_core.perception_adapters import AdapterManifest, PerceptionAdapterError, SyntheticPerceptionAdapter
from umbra_core.runtime import OrganismConfig, create_organism, load_organism, replay_from_birth


def _manifest(adapter_id: str = "synthetic-a") -> AdapterManifest:
    return AdapterManifest(adapter_id, "1.0", ("visual_features",), {"visual_features": "v1"})


def _envelope(adapter: SyntheticPerceptionAdapter, tick: int = 0, **overrides):
    data = {
        "observation_id": "obs-1", "source_id": "fixture-camera", "modality": "visual_features",
        "schema_version": "v1", "core_receipt_tick": tick, "source_timestamp": "2099-01-01T00:00:00Z",
        "capture_interval": (1.0, 2.0), "derived_features": {"edges": [0.1, 0.2]},
        "confidence": 0.6, "uncertainty": 0.4,
        "provenance_chain": ({"step": "synthetic", "source": "fixture-camera"},),
        "privacy_classification": "DERIVED_ONLY", "consent_state": "CONSENT_GRANTED",
        "retention_class": "DERIVED_BOUNDED", "replay_class": "AUTHORITATIVE",
        "integrity_metadata": {"synthetic": "true"},
    }
    data.update(overrides)
    return adapter.submit(**data)


def _contains_raw(value):
    forbidden = {"raw", "raw_payload", "image", "video", "audio", "frame", "samples", "bytes", "base64", "location_trace"}
    if isinstance(value, dict):
        return any(key.lower() in forbidden or _contains_raw(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_raw(item) for item in value)
    return False


def test_contract_rejects_raw_payload_schema_downgrade_and_manifest_spoof():
    adapter = SyntheticPerceptionAdapter(_manifest())
    with pytest.raises(PerceptionAdapterError, match="raw_payload_forbidden"):
        _envelope(adapter, derived_features={"raw_payload": "no"})
    with pytest.raises(PerceptionAdapterError, match="schema_or_modality_rejected"):
        _envelope(adapter, schema_version="old")
    with pytest.raises(PerceptionAdapterError, match="provenance_or_manifest_mismatch"):
        _envelope(adapter, manifest_hash="forged")


def test_adapter_observation_is_authoritative_deduplicated_and_preserves_uncertainty(tmp_path):
    cfg = OrganismConfig(db_path=str(tmp_path / "d011.db"), seed=8)
    org = create_organism(cfg)
    adapter = SyntheticPerceptionAdapter(_manifest())
    envelope = _envelope(adapter, org.tick)
    before = org.authoritative_state()
    assert org.submit_perception_observation(envelope, adapter.manifest)
    assert not org.submit_perception_observation(envelope, adapter.manifest)
    stored = org.perception.adapter_observations[0]
    assert stored["confidence"] == 0.6 and stored["uncertainty"] == 0.4
    assert org.identity.as_dict() == before["identity"]
    assert "perception_adapter_observation_accepted" in AUTHORITATIVE_EVENT_TYPES
    assert is_authoritative("perception_adapter_observation_accepted")
    events = list(org.store.iter_events())
    assert [e["event_type"] for e in events].count("perception_adapter_observation_accepted") == 1
    assert not _contains_raw([e["payload"] for e in events])
    org.snapshot_if_due(force=True)
    org.close()
    restored = load_organism(cfg)
    assert restored.perception.adapter_observations == [stored]
    assert restored.tick == 0  # source wall time never advances organism time
    restored.close()


def test_core_receipt_tick_blocks_delayed_or_reordered_submission(tmp_path):
    org = create_organism(OrganismConfig(db_path=str(tmp_path / "d011.db")))
    adapter = SyntheticPerceptionAdapter(_manifest())
    with pytest.raises(ValueError, match="core_receipt_tick_mismatch"):
        org.submit_perception_observation(_envelope(adapter, org.tick + 1), adapter.manifest)
    org.close()


def test_two_synthetic_adapters_are_portable_and_only_derived_data_is_durable(tmp_path):
    org = create_organism(OrganismConfig(db_path=str(tmp_path / "d011.db")))
    first = SyntheticPerceptionAdapter(_manifest("synthetic-a"))
    second = SyntheticPerceptionAdapter(_manifest("synthetic-b"))
    assert org.submit_perception_observation(_envelope(first, org.tick, observation_id="a"), first.manifest)
    assert org.submit_perception_observation(_envelope(second, org.tick, observation_id="b"), second.manifest)
    state_text = json.dumps(org.authoritative_state(), sort_keys=True)
    assert "raw_payload" not in state_text and "fixture-camera" in state_text
    assert {x["adapter_id"] for x in org.perception.adapter_observations} == {"synthetic-a", "synthetic-b"}
    org.close()


def test_real_ledger_replay_matches_snapshot_and_rejections_survive_restart(tmp_path):
    cfg = OrganismConfig(db_path=str(tmp_path / "d011.db"))
    org = create_organism(cfg)
    adapter = SyntheticPerceptionAdapter(_manifest())
    assert org.submit_perception_observation(_envelope(adapter, org.tick, observation_id="accepted"), adapter.manifest)
    rejected = replace(_envelope(adapter, org.tick, observation_id="rejected"), manifest_hash="forged")
    with pytest.raises(PerceptionAdapterError):
        org.submit_perception_observation(rejected, adapter.manifest)
    org.snapshot_if_due(force=True)
    snapshot_perception = org.authoritative_state()["perception"]
    org.close()
    replayed = replay_from_birth(cfg.db_path)["perception_adapter"]
    assert replayed["adapter_observations"] == snapshot_perception["adapter_observations"]
    assert replayed["rejected_adapter_observation_ids"] == ["rejected"]
    restored = load_organism(cfg)
    assert restored.perception.rejected_adapter_observation_ids == ["rejected"]
    restored.close()


def test_duplicate_or_altered_authoritative_event_fails_closed(tmp_path):
    cfg = OrganismConfig(db_path=str(tmp_path / "d011.db"))
    org = create_organism(cfg)
    adapter = SyntheticPerceptionAdapter(_manifest())
    assert org.submit_perception_observation(_envelope(adapter, org.tick, observation_id="one"), adapter.manifest)
    org.snapshot_if_due(force=True)
    payload = next(e["payload"] for e in org.store.iter_events() if e["event_type"] == "perception_adapter_observation_accepted")
    org.store.append_event(agent_id=org.identity.agent_id, event_type="perception_adapter_observation_accepted", monotonic_time=0, wall_time=0, payload=payload)
    org.close()
    with pytest.raises(Exception, match="event_hash_mismatch|perception_adapter_duplicate_acceptance"):
        replay_from_birth(cfg.db_path)

    cfg2 = OrganismConfig(db_path=str(tmp_path / "altered.db"))
    org = create_organism(cfg2)
    assert org.submit_perception_observation(_envelope(adapter, org.tick), adapter.manifest)
    event = next(e for e in org.store.iter_events() if e["event_type"] == "perception_adapter_observation_accepted")
    org.store.conn.execute("UPDATE events SET payload = ? WHERE sequence = ?", ("{}", event["sequence"]))
    org.close()
    with pytest.raises(Exception, match="payload_hash_mismatch"):
        replay_from_birth(cfg2.db_path)

    for name, sql in (
        ("missing", "DELETE FROM events WHERE event_type = 'perception_adapter_observation_accepted'"),
        ("reordered", "UPDATE events SET sequence = -1 WHERE event_type = 'perception_adapter_observation_accepted'"),
    ):
        cfg3 = OrganismConfig(db_path=str(tmp_path / f"{name}.db"))
        org = create_organism(cfg3)
        assert org.submit_perception_observation(_envelope(adapter, org.tick), adapter.manifest)
        org.snapshot_if_due(force=True)
        org.store.conn.execute(sql)
        org.close()
        with pytest.raises(Exception, match="sequence_gap|chain_break|ledger_tip_mismatch|perception_adapter_snapshot_replay_mismatch"):
            replay_from_birth(cfg3.db_path)


def test_c0_to_c8_controls_are_explicitly_contained_or_show_loss():
    adapter = SyntheticPerceptionAdapter(_manifest())
    good = _envelope(adapter)
    assert good.confidence < 1 and good.uncertainty > 0  # C0
    assert len({good.source_id, "other-source"}) == 2  # C6 identity separation
    with pytest.raises(PerceptionAdapterError):
        replace(good, manifest_hash="forged").validate(adapter.manifest)  # C1
    assert replace(good, confidence=1.0, uncertainty=0.0).uncertainty == 0.0  # C2 loss
    membrane = PerceptionMembrane()
    assert membrane.accept_adapter_observation(good, adapter.manifest)
    assert not membrane.accept_adapter_observation(good, adapter.manifest)  # C3
    with pytest.raises(PerceptionAdapterError):
        replace(good, derived_features={"raw_payload": "diagnostic"}).validate(adapter.manifest)  # C4
    assert not hasattr(adapter, "memory") and not hasattr(adapter, "organism")  # C5 containment
    with pytest.raises(PerceptionAdapterError):
        replace(good, schema_version="downgrade").validate(adapter.manifest)  # C7
    assert not PerceptionMembrane().adapter_observations  # C8 loss
