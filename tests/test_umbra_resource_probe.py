import json
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.umbra_resource_probe import (ResourceRecorder, cadence_due,
    checkpoint_measurements, coverage_complete, observe_maintenance, preflight, observed_file_size)
from umbra_core.persistence import Store


def test_cadence_is_first_of_ticks_or_wall_time():
    assert not cadence_due(99, 0, 4.99, 0)
    assert cadence_due(100, 0, .01, 0)
    assert cadence_due(1, 0, 5., 0)
    assert not cadence_due(120, 100, 9.99, 5.)


@pytest.mark.parametrize("compactions,eviction,restart,ticks,expected", [
    (4, False, True, 30000, False), (5, False, True, 30000, False),
    (5, True, False, 30000, False), (5, True, True, 99, False),
    (5, True, True, 100, True)])
def test_coverage_requires_eviction_restart_and_subsequent_operation(compactions, eviction, restart, ticks, expected):
    assert coverage_complete(compactions, eviction, restart, ticks, 0) == expected


def test_sampler_separates_files_memory_and_marks_checkpoint_age(tmp_path):
    db = tmp_path / "db"
    db.write_bytes(b"123")
    Path(str(db) + "-wal").write_bytes(b"45")
    recorder = ResourceRecorder(tmp_path, db)
    recorder.sample("before_export")
    recorder.close()
    row = json.loads((tmp_path / "resources.jsonl").read_text())
    assert row["storage_bytes"] == {"database": 3, "wal": 2, "shm": 0}
    assert row["exported_evidence_bytes"] == {}
    assert row["rss_mib"] > 0
    assert row["checkpoint_measurement_age_seconds"] >= 0


def test_wall_sampler_works_while_owner_is_blocked(tmp_path):
    recorder = ResourceRecorder(tmp_path, tmp_path / "db")
    recorder.last_time -= 5
    recorder.thread.start()
    for _ in range(100):
        if (tmp_path / "resources.jsonl").stat().st_size:
            break
        threading.Event().wait(.01)
    recorder.close()
    row = json.loads((tmp_path / "resources.jsonl").read_text())
    assert row["reason"] == "wall_cadence"
    assert row["checkpoints"]["unavailable"] == "before_organism_creation"


def test_store_measurement_is_read_only_and_no_compaction_is_requested(tmp_path):
    store = Store(str(tmp_path / "db.sqlite"))
    before = store.conn.total_changes
    result = checkpoint_measurements(store)
    assert result["epochs"] == []
    assert result["checkpoint_payload_bytes"] == 0
    assert result["hot_tail_events"] == 0
    assert store.conn.total_changes == before
    store.close()


def test_observer_forwards_once_without_changing_owner_arguments(monkeypatch):
    calls, samples = [], []
    epochs = [1, 2, 3, 4]
    def compact(**kwargs):
        calls.append(kwargs)
        epochs[:] = [2, 3, 4, 5]
        return {"checkpoint_epoch": 5}
    store = SimpleNamespace(compact_authoritative_prefix=compact, reclaim_physical_storage=lambda: None)
    organism = SimpleNamespace(store=store)
    recorder = SimpleNamespace(sample=lambda reason, org: samples.append(reason))
    monkeypatch.setattr("tools.umbra_resource_probe.checkpoint_measurements", lambda s: {"epochs": list(epochs)})
    lifecycle = {"natural_compactions": 0, "eviction_observed": False}
    observe_maintenance(organism, recorder, lifecycle)
    result = store.compact_authoritative_prefix(keep_checkpoints=4, creation_tick=5000)
    assert calls == [{"keep_checkpoints": 4, "creation_tick": 5000}]
    assert result == {"checkpoint_epoch": 5}
    assert lifecycle == {"natural_compactions": 1, "eviction_observed": True}
    assert samples == ["before_compact_authoritative_prefix", "after_compact_authoritative_prefix"]


def test_wrong_protocol_hash_blocks_before_organism_or_work_creation(tmp_path):
    with pytest.raises(ValueError, match="protocol_hash_mismatch"):
        preflight(tmp_path / "must-not-exist", "fake-candidate", "wrong-hash")
    assert not (tmp_path / "must-not-exist").exists()


def test_sidecar_disappearance_is_zero_size_not_a_failed_observer(tmp_path):
    assert observed_file_size(tmp_path / "closed-wal") == 0
