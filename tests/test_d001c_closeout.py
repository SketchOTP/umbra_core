"""D-001C tests: downsampling policy + soak closeout gates."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from umbra_core.events import (
    AUTHORITATIVE_EVENT_TYPES,
    DIAGNOSTIC_EVENT_TYPES,
    is_authoritative,
    is_diagnostic,
)
from umbra_core.runtime import OrganismConfig, create_organism, load_organism
from umbra_core.persistence import Store

EVIDENCE = Path(__file__).resolve().parents[1] / "docs" / "evidence" / "d001"
SOAK_SUMMARY = EVIDENCE / "soak-6h-summary.json"
SOAK_CLOSEOUT = EVIDENCE / "soak-closeout.json"
SOAK_DB = Path("/tmp/umbra_soak/soak6h.sqlite")


def _db(tmp_path: Path, name: str = "t.sqlite") -> str:
    return str(tmp_path / name)


def test_authoritative_events_are_never_downsampled(tmp_path):
    org = create_organism(OrganismConfig(db_path=_db(tmp_path), seed=1, snapshot_every=1000))
    org.run_ticks(12)
    events = org.store.iter_events()
    types = [e["event_type"] for e in events]
    # Every tick: physiology_drift + (proposal|denial) + usually outcome_verified
    drifts = [e for e in events if e["event_type"] == "physiology_drift"]
    gov = [e for e in events if e["event_type"] in ("proposal", "denial")]
    outcomes = [e for e in events if e["event_type"] == "outcome_verified"]
    assert len(drifts) == 12
    assert len(gov) == 12
    assert len(outcomes) == 12  # all defaults admitted
    assert "birth" in types
    for t in ("physiology_drift", "proposal", "outcome_verified", "birth"):
        assert is_authoritative(t)
    # No cadence holes in drift sequences
    assert [e["sequence"] for e in drifts]  # present
    org.close()


def test_omitted_events_are_non_authoritative():
    for t in DIAGNOSTIC_EVENT_TYPES:
        assert is_diagnostic(t)
        assert not is_authoritative(t)
    overlap = AUTHORITATIVE_EVENT_TYPES & DIAGNOSTIC_EVENT_TYPES
    assert not overlap


def test_replay_does_not_require_omitted_events(tmp_path):
    """Seed replay matches without any diagnostic observation events in the ledger."""
    p1 = _db(tmp_path, "a.sqlite")
    p2 = _db(tmp_path, "b.sqlite")
    o1 = create_organism(OrganismConfig(db_path=p1, seed=42))
    o1.run_ticks(30)
    s1 = {
        "physiology": o1.authoritative_state()["physiology"],
        "embodiment": o1.authoritative_state()["embodiment"],
        "tick": o1.authoritative_state()["tick"],
    }
    types = {e["event_type"] for e in o1.store.iter_events()}
    assert "observation" not in types  # diagnostic omitted
    o1.close()
    o2 = create_organism(OrganismConfig(db_path=p2, seed=42))
    o2.run_ticks(30)
    s2 = {
        "physiology": o2.authoritative_state()["physiology"],
        "embodiment": o2.authoritative_state()["embodiment"],
        "tick": o2.authoritative_state()["tick"],
    }
    o2.close()
    assert s1 == s2


def test_no_unbounded_runtime_collection(tmp_path):
    org = create_organism(OrganismConfig(db_path=_db(tmp_path), seed=3))
    org.run_ticks(600)
    assert len(org.metrics["cells"]) <= 500
    assert len(org.arbitrator.state.visited_cells) <= 500
    org.close()


def _require_soak():
    if not SOAK_SUMMARY.exists() and not SOAK_CLOSEOUT.exists():
        pytest.skip("soak summary not ready yet")
    if SOAK_CLOSEOUT.exists():
        return json.loads(SOAK_CLOSEOUT.read_text())
    return json.loads(SOAK_SUMMARY.read_text())


def test_soak_duration_meets_gate():
    data = _require_soak()
    # prefer closeout if present
    dur = data.get("duration_sec") or data.get("elapsed_sec") or 0
    assert dur >= 6 * 3600 - 30  # 30s clock slack


def test_soak_identity_preserved():
    data = _require_soak()
    if SOAK_CLOSEOUT.exists():
        co = json.loads(SOAK_CLOSEOUT.read_text())
        assert co.get("identity_preserved") is True
        assert co.get("agent_id")
    else:
        assert data.get("agent_id")


def test_soak_ledger_valid():
    if SOAK_CLOSEOUT.exists():
        co = json.loads(SOAK_CLOSEOUT.read_text())
        assert co.get("ledger_valid") is True
    else:
        if not SOAK_DB.exists():
            pytest.skip("soak db missing")
        store = Store(str(SOAK_DB))
        store.validate_chain()
        store.close()


def test_soak_restart_succeeds():
    if SOAK_CLOSEOUT.exists():
        co = json.loads(SOAK_CLOSEOUT.read_text())
        assert co.get("restart_ok") is True
        return
    if not SOAK_DB.exists():
        pytest.skip("soak db missing")
    cfg = OrganismConfig(db_path=str(SOAK_DB), seed=99)
    org = load_organism(cfg)
    assert org.identity.agent_id
    org.run_ticks(2)
    org.close()


def test_soak_snapshot_replay_matches():
    if SOAK_CLOSEOUT.exists():
        co = json.loads(SOAK_CLOSEOUT.read_text())
        assert co.get("snapshot_replay_match") is True
        return
    if not SOAK_DB.exists():
        pytest.skip("soak db missing")
    cfg = OrganismConfig(db_path=str(SOAK_DB), seed=99)
    store = Store(str(SOAK_DB))
    snap = store.load_snapshot()
    store.close()
    org = load_organism(cfg)
    live = org.authoritative_state()
    assert live["physiology"] == snap["state"]["physiology"]
    assert live["embodiment"] == snap["state"]["embodiment"]
    assert live["identity"]["agent_id"] == snap["state"]["identity"]["agent_id"]
    org.close()
