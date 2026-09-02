"""Synthetic storage-contract tests only; no organism import or construction."""

from __future__ import annotations

import hashlib
import json
import sqlite3

import pytest

from experiments.as003pr5a.protocol import ProtocolMetadataError, read_snapshot_metadata


def _database(tmp_path, *, latest="snapshot", referenced="snapshot", ledger='{"event_hash":"genesis","sequence":0}', bad_hash=False):
    path = tmp_path / "metadata.sqlite"
    state = json.dumps({"tick": 0}, sort_keys=True, separators=(",", ":"))
    digest = "0" * 64 if bad_hash else hashlib.sha256(state.encode()).hexdigest()
    with sqlite3.connect(path) as connection:
        connection.executescript(
            "CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);"
            "CREATE TABLE snapshots(snapshot_id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, sequence INTEGER NOT NULL, monotonic_time REAL NOT NULL, state_json TEXT NOT NULL, state_hash TEXT NOT NULL);"
        )
        if latest is not None:
            connection.execute("INSERT INTO meta VALUES ('latest_snapshot', ?)", (latest,))
        connection.execute("INSERT INTO meta VALUES ('ledger_tip', ?)", (ledger,))
        if referenced is not None:
            connection.execute("INSERT INTO snapshots VALUES (?, 'agent', 5, 0.0, ?, ?)", (referenced, state, digest))
    return path


def test_raw_text_snapshot_id(tmp_path):
    value = read_snapshot_metadata(sqlite3.connect(_database(tmp_path)))
    assert value["latest_snapshot_id"] == "snapshot"


def test_missing_latest_snapshot(tmp_path):
    value = read_snapshot_metadata(sqlite3.connect(_database(tmp_path, latest=None, referenced=None)))
    assert value["latest_snapshot"] is None


def test_missing_referenced_snapshot(tmp_path):
    with pytest.raises(ProtocolMetadataError, match="latest_snapshot_reference_missing"):
        read_snapshot_metadata(sqlite3.connect(_database(tmp_path, latest="missing", referenced=None)))


def test_uuid_like_raw_text_snapshot_id(tmp_path):
    identifier = "a580866c-56e0-4fc0-94a5-8bfe70256e22"
    value = read_snapshot_metadata(sqlite3.connect(_database(tmp_path, latest=identifier, referenced=identifier)))
    assert value["latest_snapshot_id"] == identifier


def test_ledger_tip_remains_json(tmp_path):
    value = read_snapshot_metadata(sqlite3.connect(_database(tmp_path, ledger='{"event_hash":"abc","sequence":5}')))
    assert value["ledger_tip"] == {"event_hash": "abc", "sequence": 5}


def test_snapshot_sequence_and_hash(tmp_path):
    value = read_snapshot_metadata(sqlite3.connect(_database(tmp_path)))
    assert value["latest_snapshot"]["sequence"] == 5


def test_corrupted_snapshot_hash_fails(tmp_path):
    with pytest.raises(ProtocolMetadataError, match="snapshot_hash_mismatch"):
        read_snapshot_metadata(sqlite3.connect(_database(tmp_path, bad_hash=True)))


def test_malformed_ledger_tip_fails(tmp_path):
    with pytest.raises(ProtocolMetadataError, match="malformed_ledger_tip_json"):
        read_snapshot_metadata(sqlite3.connect(_database(tmp_path, ledger="not-json")))
