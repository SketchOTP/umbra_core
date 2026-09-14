from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from experiments.as014.qualification import REGIMES
from experiments.as018.development import execute
from experiments.as018.full_config import config, fingerprint
from experiments.d012.readonly_validation import validate_read_only
from umbra_core.runtime import create_organism


ROOT = Path(__file__).resolve().parents[1]


def test_registered_development_manifest_is_fresh_and_complete() -> None:
    path = ROOT / "experiments/as018/AS018_DEVELOPMENT_SEED_MANIFEST_V1.json"
    manifest = json.loads(path.read_text())
    seeds = [seed for regime in REGIMES for seed in manifest["development_regimes"][regime]]
    assert manifest["schema"] == "AS018_DEVELOPMENT_SEED_MANIFEST_V1"
    assert all(len(manifest["development_regimes"][regime]) == 8 for regime in REGIMES)
    assert len(seeds) == len(set(seeds)) == 32
    assert manifest["ticks_per_organism"] == 7200
    assert manifest["retries"] == manifest["reseeds"] == manifest["substitutions"] == 0


def test_as018_configuration_explicitly_enables_only_the_rre_switch(tmp_path: Path) -> None:
    value = config(81818003, tmp_path / "config.sqlite", "R0")
    assert value.recovery_reachability_enabled is True
    assert value.viability_kernel_enabled is True
    assert fingerprint(value)["as018"]["recovery_reachability_enabled"] is True


def test_challenge_rejects_wrong_shape_before_creating_work(tmp_path: Path) -> None:
    manifest = {
        "schema": "AS018_DEVELOPMENT_SEED_MANIFEST_V1",
        "directive": "UMBRA-AS-018",
        "development_regimes": {regime: [1] for regime in REGIMES},
    }
    try:
        execute(manifest, tmp_path / "work")
    except RuntimeError as exc:
        assert str(exc) == "AS018_DEVELOPMENT_MANIFEST_CONTRACT_INVALID"
    else:
        raise AssertionError("invalid manifest was accepted")
    assert not (tmp_path / "work").exists()


def test_read_only_validation_accepts_checkpoint_plus_absolute_tail(tmp_path: Path) -> None:
    database = tmp_path / "checkpoint-tail.sqlite"
    value = config(
        88009999,
        database,
        "R0",
        ledger_overrides={
            "ledger_hot_tail_event_max": 32,
            "ledger_max_events_per_tick": 16,
        },
    )
    value.snapshot_every = 1
    value.ledger_checkpoint_keep = 2
    organism = create_organism(value)
    organism.run_ticks(4)
    organism.close()

    result = validate_read_only(database)

    assert result["chain_status"] == "ok"
    assert result["max_event_sequence"] == result["event_count"]
    with sqlite3.connect(database) as connection:
        checkpoint_end = connection.execute(
            "SELECT compacted_sequence_end FROM ledger_checkpoints"
        ).fetchone()[0]
        tail_start = connection.execute("SELECT MIN(sequence) FROM events").fetchone()[0]
    assert tail_start == checkpoint_end + 1
