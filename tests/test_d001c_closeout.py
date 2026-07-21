"""D-001C tests: retention-v1 policy + Run B soak closeout gates.

Soak-dependent tests require Run B artifacts only. Run A evidence must not
satisfy or offset these gates.
"""

from __future__ import annotations

import json
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
# Qualifying soak = Run B only (retention v1).
SOAK_SUMMARY = EVIDENCE / "soak-run-b-summary.json"
SOAK_CLOSEOUT = EVIDENCE / "soak-run-b-closeout.json"
SOAK_CLOSEOUT_ALIAS = EVIDENCE / "soak-closeout.json"
SOAK_DB = Path("/home/sketch/Projects/UMBRA-CORE/.soak/run_b.sqlite")


def _db(tmp_path: Path, name: str = "t.sqlite") -> str:
    return str(tmp_path / name)


def _closeout_path() -> Path | None:
    if SOAK_CLOSEOUT.exists():
        return SOAK_CLOSEOUT
    if SOAK_CLOSEOUT_ALIAS.exists():
        co = json.loads(SOAK_CLOSEOUT_ALIAS.read_text())
        if co.get("run_id") == "B":
            return SOAK_CLOSEOUT_ALIAS
    return None


def test_authoritative_events_are_never_downsampled(tmp_path):
    org = create_organism(OrganismConfig(db_path=_db(tmp_path), seed=1, snapshot_every=1000))
    org.run_ticks(12)
    events = org.store.iter_events()
    types = [e["event_type"] for e in events]
    drifts = [e for e in events if e["event_type"] == "physiology_drift"]
    gov = [e for e in events if e["event_type"] in ("proposal", "denial")]
    outcomes = [e for e in events if e["event_type"] == "outcome_verified"]
    assert len(drifts) == 12
    assert len(gov) == 12
    assert len(outcomes) == 12
    assert "birth" in types
    for t in ("physiology_drift", "proposal", "outcome_verified", "birth"):
        assert is_authoritative(t)
    org.close()


def test_omitted_events_are_non_authoritative():
    for t in DIAGNOSTIC_EVENT_TYPES:
        assert is_diagnostic(t)
        assert not is_authoritative(t)
    assert not (AUTHORITATIVE_EVENT_TYPES & DIAGNOSTIC_EVENT_TYPES)


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
    assert "observation" not in types
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


def _require_run_b_closeout():
    path = _closeout_path()
    if path is None:
        if not SOAK_SUMMARY.exists():
            pytest.skip("Run B soak not finished")
        pytest.skip("Run B closeout not generated yet")
    co = json.loads(path.read_text())
    assert co.get("run_id") == "B"
    assert co.get("run_a_not_used_for_offset") is True
    return co


def test_soak_duration_meets_gate():
    co = _require_run_b_closeout()
    assert co["duration_sec"] >= 6 * 3600 - 30
    assert co["gates"]["1_duration_ge_6h"] is True
    assert co["gates"]["1_no_crash"] is True


def test_soak_gate9_performance():
    co = _require_run_b_closeout()
    assert co["gates"]["2_cpu_mean_le_5pct"] is True
    assert co["gates"]["3_rss_p95_le_200"] is True
    assert co["gates"]["4_rss_slope_le_1"] is True


def test_soak_authoritative_cadence():
    co = _require_run_b_closeout()
    assert co["gates"]["5_authoritative_cadence"] is True
    assert abs(co["cadence"]["drift_per_tick"] - 1.0) < 0.02
    assert abs(co["cadence"]["gov_per_tick"] - 1.0) < 0.02


def test_soak_identity_preserved():
    co = _require_run_b_closeout()
    assert co.get("identity_preserved") is True
    assert co.get("agent_id")
    assert co["gates"]["7_identity_after_restart"] is True


def test_soak_ledger_valid():
    co = _require_run_b_closeout()
    assert co.get("ledger_valid") is True
    assert co["gates"]["6_ledger_valid"] is True
    if SOAK_DB.exists():
        store = Store(str(SOAK_DB))
        store.validate_chain()
        store.close()


def test_soak_restart_succeeds():
    co = _require_run_b_closeout()
    assert co.get("restart_ok") is True
    if not SOAK_DB.exists():
        pytest.fail("Run B DB required for restart check")
    org = load_organism(OrganismConfig(db_path=str(SOAK_DB), seed=99))
    assert org.identity.agent_id == co["agent_id"]
    org.run_ticks(2)
    org.close()


def test_soak_snapshot_replay_matches():
    co = _require_run_b_closeout()
    assert co.get("snapshot_replay_match") is True
    assert co["gates"]["8_snapshot_replay_match"] is True
    if not SOAK_DB.exists():
        pytest.fail("Run B DB required for snapshot check")
    store = Store(str(SOAK_DB))
    snap = store.load_snapshot()
    store.close()
    org = load_organism(OrganismConfig(db_path=str(SOAK_DB), seed=99))
    live = org.authoritative_state()
    assert live["physiology"] == snap["state"]["physiology"]
    assert live["embodiment"] == snap["state"]["embodiment"]
    assert live["identity"]["agent_id"] == snap["state"]["identity"]["agent_id"]
    org.close()


def test_soak_database_growth_bounded():
    co = _require_run_b_closeout()
    assert co["gates"]["9_database_growth_recorded_and_bounded"] is True
    assert co["database_bytes"] > 0
    assert co["database_bytes"] <= co["database_bytes_ceiling"]
